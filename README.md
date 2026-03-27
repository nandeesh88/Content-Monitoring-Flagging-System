# Content Monitoring & Flagging System

A Django REST Framework service that monitors incoming content, scores keyword relevance, and creates reviewable flags with suppression logic to prevent noisy re-flagging.

## Content Source

This project uses **both** of the following sources:

- **Mock JSON dataset** - used as the default source. Contains 6 hand-crafted articles
  that are guaranteed to match the example keywords (python, django, automation, data pipeline).
  Always runs even if the internet is unavailable.

- **HackerNews public API** - used as a real live source. Fetches the top 10 stories
  from https://hacker-news.firebaseio.com. No API key required. If HackerNews is
  unreachable, the scan still completes using the mock dataset.

Both sources are combined and scanned together on every `POST /api/scan/` call.

## Tech Stack

- Python
- Django
- Django REST Framework
- SQLite
- Requests

## Features

- Keyword management API
- Scanning pipeline across multiple content sources
- Relevance scoring based on keyword match quality
- Flag review workflow (`pending`, `relevant`, `irrelevant`)
- Suppression logic for irrelevant flags until content changes

## Setup

### 1. Clone and enter project

```bash
git clone <repo-url>
cd content-monitor
```

### 2. Create and activate virtual environment

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install django djangorestframework requests
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Run development server

```bash
python manage.py runserver
```

Server URL:

- http://127.0.0.1:8000/

## Content Sources

Two sources are used during scanning:

1. Mock JSON dataset
- Default source
- Always runs
- Contains 6 local articles

2. HackerNews public API
- No API key required
- Fetches top 10 stories live

## API Endpoints

Base prefix: `/api/`

- `POST /api/keywords/` — Create a keyword
- `GET /api/keywords/list/` — List all keywords
- `POST /api/scan/` — Trigger a scan
- `GET /api/flags/` — List all flags
- `PATCH /api/flags/<id>/` — Update flag status

Supported filters for listing flags:

- `GET /api/flags/?status=pending`
- `GET /api/flags/?keyword=python`

## Curl Examples (All 5 Endpoints)

### 1) Create keyword

```bash
curl -X POST "http://127.0.0.1:8000/api/keywords/" \
  -H "Content-Type: application/json" \
  -d '{"name":"python"}'
```

### 2) List keywords

```bash
curl -X GET "http://127.0.0.1:8000/api/keywords/list/"
```

### 3) Trigger scan

```bash
curl -X POST "http://127.0.0.1:8000/api/scan/"
```

### 4) List flags (with optional filters)

```bash
curl -X GET "http://127.0.0.1:8000/api/flags/"
```

```bash
curl -X GET "http://127.0.0.1:8000/api/flags/?status=pending"
```

```bash
curl -X GET "http://127.0.0.1:8000/api/flags/?keyword=python"
```

### 5) Update flag status

```bash
curl -X PATCH "http://127.0.0.1:8000/api/flags/1/" \
  -H "Content-Type: application/json" \
  -d '{"status":"irrelevant"}'
```

## Scoring Logic

- Exact keyword match in title -> 100
- Partial keyword match in title -> 70
- Keyword appears only in body -> 40
- No match -> 0

## Suppression Logic

If a flag is marked `irrelevant`, it is suppressed on future scans until the related content item changes.

How it works:

- At suppression time, `suppressed_until_update` is set to the content item's current `last_updated`.
- On each scan, if `content_item.last_updated > suppressed_until_update`, the content is treated as changed.
- The flag is then resurfaced by resetting status to `pending`.

This prevents repetitive review of unchanged content while still resurfacing genuinely updated items.

## Assumptions and Trade-offs

- `title + source` is used as a practical unique key for `ContentItem` to avoid duplicates.
- HackerNews stories use `url` or `text` as body because many stories do not provide full body content.
- SQLite is used for simplicity and local development speed.
- Authentication is intentionally excluded to keep scope focused on core monitoring logic.
- `unique_together` on `Flag` prevents duplicate flags for the same keyword/content pair.

## Project Structure

```text
content-monitor/
  db.sqlite3
  manage.py
  README.md
  content_monitor/
    __init__.py
    asgi.py
    settings.py
    urls.py
    wsgi.py
  monitor/
    __init__.py
    admin.py
    apps.py
    models.py
    serializers.py
    tests.py
    urls.py
    views.py
    migrations/
      __init__.py
      0001_initial.py
    services/
      __init__.py
      scanner.py
      sources.py
```

## Notes

- Use the project virtual environment for local commands.
- If HackerNews is temporarily unavailable, the scan still runs using the mock dataset.

## Sample API Responses

### POST /api/keywords/

```json
{
  "id": 1,
  "name": "python",
  "created_at": "2026-03-27T11:02:34.130245Z"
}
```

### POST /api/scan/

```json
{
  "message": "Scan completed successfully.",
  "flags_created": 7,
  "flags_skipped": 0,
  "flags_resurfaced": 0,
  "total_content_items": 6,
  "total_keywords": 4
}
```

### GET /api/flags/

```json
[
  {
    "id": 1,
    "keyword": 1,
    "keyword_name": "python",
    "content_item": 1,
    "content_title": "Learn Django Fast",
    "content_source": "mock",
    "score": 40,
    "status": "pending",
    "reviewed_at": null,
    "created_at": "2026-03-27T11:03:00.889907Z"
  }
]
```

### PATCH /api/flags/1/

```json
{
  "id": 1,
  "keyword": 1,
  "keyword_name": "python",
  "content_item": 1,
  "content_title": "Learn Django Fast",
  "content_source": "mock",
  "score": 40,
  "status": "irrelevant",
  "reviewed_at": "2026-03-27T11:03:54.607285Z",
  "created_at": "2026-03-27T11:03:00.889907Z"
}
```
