from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ContentItem, Flag, Keyword
from .services.scanner import compute_score, run_scan


class KeywordCreationTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_create_keyword_and_duplicate(self):
		"""
		Test 1 - Keyword creation
		- POST /api/keywords/ with {'name': 'python'} returns 201
		- Creating duplicate keyword returns 400
		"""
		response = self.client.post('/api/keywords/', {'name': 'python'}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data['name'], 'python')
		self.assertIn('id', response.data)

		duplicate = self.client.post('/api/keywords/', {'name': 'python'}, format='json')
		self.assertEqual(duplicate.status_code, 400)


class ScoringLogicTests(TestCase):
	def test_compute_score_cases(self):
		"""
		Test 2 - Scoring logic
		"""
		self.assertEqual(compute_score('python', 'Python Guide', 'some body'), 100)
		self.assertEqual(compute_score('python', 'Learn pythonic code', 'some body'), 70)
		self.assertEqual(compute_score('python', 'Cooking Tips', 'python is mentioned in body'), 40)
		self.assertEqual(compute_score('python', 'Cooking Tips', 'no match here'), 0)


class FlagReviewWorkflowTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.keyword = Keyword.objects.create(name='python')
		self.content_item = ContentItem.objects.create(
			title='Python Guide',
			body='A simple guide.',
			source='mock',
			last_updated=timezone.now(),
		)
		self.flag = Flag.objects.create(
			keyword=self.keyword,
			content_item=self.content_item,
			score=100,
			status='pending',
		)

	def test_patch_relevant_then_irrelevant(self):
		"""
		Test 3 - Flag review workflow
		- PATCH relevant updates status
		- PATCH irrelevant sets reviewed_at and suppressed_until_update
		"""
		relevant_response = self.client.patch(
			f'/api/flags/{self.flag.id}/',
			{'status': 'relevant'},
			format='json',
		)
		self.assertEqual(relevant_response.status_code, 200)
		self.flag.refresh_from_db()
		self.assertEqual(self.flag.status, 'relevant')

		irrelevant_response = self.client.patch(
			f'/api/flags/{self.flag.id}/',
			{'status': 'irrelevant'},
			format='json',
		)
		self.assertEqual(irrelevant_response.status_code, 200)
		self.flag.refresh_from_db()
		self.assertEqual(self.flag.status, 'irrelevant')
		self.assertIsNotNone(self.flag.reviewed_at)
		self.assertIsNotNone(self.flag.suppressed_until_update)
		self.assertEqual(self.flag.suppressed_until_update, self.content_item.last_updated)


class SuppressionLogicTests(TestCase):
	def setUp(self):
		self.keyword = Keyword.objects.create(name='python')
		self.base_last_updated = timezone.now().replace(microsecond=0)
		self.content_item = ContentItem.objects.create(
			title='Python Guide',
			body='Some body text.',
			source='mock',
			last_updated=self.base_last_updated,
		)
		self.flag = Flag.objects.create(
			keyword=self.keyword,
			content_item=self.content_item,
			score=100,
			status='irrelevant',
			reviewed_at=timezone.now(),
			suppressed_until_update=self.base_last_updated,
		)

	def test_irrelevant_flag_suppressed_until_content_changes(self):
		"""
		Test 4 - Suppression logic
		- First scan with unchanged last_updated keeps flag irrelevant
		- Second scan with future last_updated resurfaces flag to pending
		"""
		with patch(
			'monitor.services.scanner.get_all_content',
			return_value=[
				{
					'title': 'Python Guide',
					'body': 'Some body text.',
					'source': 'mock',
					'last_updated': self.base_last_updated.isoformat(),
				}
			],
		):
			first_result = run_scan()

		self.flag.refresh_from_db()
		self.assertEqual(self.flag.status, 'irrelevant')
		self.assertEqual(first_result['flags_resurfaced'], 0)

		future_last_updated = self.base_last_updated + timedelta(days=1)
		with patch(
			'monitor.services.scanner.get_all_content',
			return_value=[
				{
					'title': 'Python Guide',
					'body': 'Some body text.',
					'source': 'mock',
					'last_updated': future_last_updated.isoformat(),
				}
			],
		):
			second_result = run_scan()

		self.flag.refresh_from_db()
		self.assertEqual(self.flag.status, 'pending')
		self.assertIsNone(self.flag.suppressed_until_update)
		self.assertEqual(second_result['flags_resurfaced'], 1)
