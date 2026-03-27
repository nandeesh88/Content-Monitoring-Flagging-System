from datetime import datetime, timezone

import requests


def get_mock_content():
    """Return a local mock dataset as the default content source."""
    return [
        {
            'title': 'Learn Django Fast',
            'body': 'Django is a powerful Python web framework used for building scalable applications.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
        {
            'title': 'Python Automation Scripts',
            'body': 'Automate repetitive tasks using Python scripts and libraries like os and subprocess.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
        {
            'title': 'Building a Data Pipeline',
            'body': 'A data pipeline moves and transforms data between systems efficiently.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
        {
            'title': 'Cooking Tips for Beginners',
            'body': 'Best recipes and kitchen hacks for people who are just starting to cook.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
        {
            'title': 'Django REST Framework Guide',
            'body': 'DRF makes it easy to build Web APIs on top of Django with serializers and viewsets.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
        {
            'title': 'Automation in DevOps',
            'body': 'Modern DevOps relies heavily on automation tools like Ansible, Terraform, and Jenkins.',
            'source': 'mock',
            'last_updated': '2026-03-20T10:00:00Z',
        },
    ]


def get_hackernews_content(limit=10):
    """Fetch top stories from HackerNews public API. No API key required."""
    try:
        response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=5)
        story_ids = response.json()[:limit]

        stories = []
        for story_id in story_ids:
            story_response = requests.get(
                f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                timeout=5,
            )
            story = story_response.json()

            if not story or story.get('type') != 'story':
                continue

            timestamp = datetime.fromtimestamp(story.get('time', 0), tz=timezone.utc).isoformat()

            stories.append(
                {
                    'title': story.get('title', ''),
                    'body': story.get('text') or story.get('url') or '',
                    'source': 'hackernews',
                    'last_updated': timestamp,
                }
            )

        return stories
    except Exception as exc:
        print(f'[HackerNews] Failed to fetch: {exc}')
        return []


def get_all_content():
    """Combine mock and HackerNews content into one list."""
    return get_mock_content() + get_hackernews_content(limit=10)