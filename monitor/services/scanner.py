from django.utils import timezone
from django.utils.dateparse import parse_datetime

from monitor.models import Keyword, ContentItem, Flag
from .sources import get_all_content


def compute_score(keyword_name: str, title: str, body: str) -> int:
    """
    Scoring rules:
      - Exact keyword match in title   -> 100
      - Partial keyword match in title -> 70
      - Keyword only in body           -> 40
      - No match                       -> 0
    """
    keyword_lower = keyword_name.lower()
    title_lower = title.lower()
    body_lower = body.lower()

    title_words = title_lower.split()

    if keyword_lower in title_words:
        return 100
    if keyword_lower in title_lower:
        return 70
    if keyword_lower in body_lower:
        return 40
    return 0


def run_scan():
    """
    Main scan logic:
    1. Fetch all content (mock + HackerNews)
    2. Upsert ContentItems into DB
    3. For each keyword x content pair, compute score
    4. Apply suppression logic before creating/updating flags
    5. Return summary of results
    """
    content_list = get_all_content()
    keywords = Keyword.objects.all()

    if not keywords.exists():
        return {'error': 'No keywords found. Please add keywords first.'}

    created_count = 0
    skipped_count = 0
    resurfaced_count = 0

    for item_data in content_list:
        last_updated = parse_datetime(item_data.get('last_updated', ''))
        if last_updated is None:
            last_updated = timezone.now()

        content_item, _ = ContentItem.objects.update_or_create(
            title=item_data.get('title', ''),
            source=item_data.get('source', ''),
            defaults={
                'body': item_data.get('body', ''),
                'last_updated': last_updated,
            },
        )

        for keyword in keywords:
            score = compute_score(keyword.name, content_item.title, content_item.body)
            if score == 0:
                continue

            existing_flag = Flag.objects.filter(keyword=keyword, content_item=content_item).first()

            if existing_flag:
                if existing_flag.status == 'irrelevant':
                    content_changed = (
                        existing_flag.suppressed_until_update is None
                        or content_item.last_updated > existing_flag.suppressed_until_update
                    )
                    if content_changed:
                        existing_flag.status = 'pending'
                        existing_flag.score = score
                        existing_flag.suppressed_until_update = None
                        existing_flag.reviewed_at = None
                        existing_flag.save()
                        resurfaced_count += 1
                    else:
                        skipped_count += 1
                else:
                    existing_flag.score = score
                    existing_flag.save()
                    skipped_count += 1
            else:
                Flag.objects.create(
                    keyword=keyword,
                    content_item=content_item,
                    score=score,
                    status='pending',
                )
                created_count += 1

    return {
        'message': 'Scan completed successfully.',
        'flags_created': created_count,
        'flags_skipped': skipped_count,
        'flags_resurfaced': resurfaced_count,
        'total_content_items': len(content_list),
        'total_keywords': keywords.count(),
    }