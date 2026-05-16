# PDF Backfill Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `past/extract.py` — a Python script that OCRs image-based Railsplitter newspaper PDFs and backfills extracted articles directly into `content.json`.

**Architecture:** pdf2image converts each PDF page to a 300 DPI PIL image; pytesseract's `image_to_data()` returns per-word bounding boxes that are clustered into text blocks by pytesseract's own block grouping; blocks are classified by relative font size into roles (section_banner, headline, dek, byline, body) and then grouped into article records; articles are built into content.json shape and merged idempotently.

**Tech Stack:** Python 3.11+, pdf2image, pytesseract (wraps tesseract binary), Pillow, pytest. System deps: poppler + tesseract via Homebrew.

---

## File Structure

```
past/
  extract.py          # All pipeline logic + CLI — single file
  requirements.txt    # Runtime + test deps
  tests/
    __init__.py
    test_extract.py   # All unit tests

.gitignore            # Add past/.venv/ entry
```

`content.json` is at the project root, resolved via `Path(__file__).parent.parent / 'content.json'` so the script works regardless of working directory.

---

### Task 1: Scaffold — venv, requirements, gitignore, test skeleton

**Files:**
- Create: `past/requirements.txt`
- Create: `past/tests/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `past/requirements.txt`**

```
pdf2image>=1.17.0
pytesseract>=0.3.10
Pillow>=10.0.0
pytest>=7.0.0
```

- [ ] **Step 2: Add `past/.venv/` to `.gitignore`**

Append to the end of `.gitignore`:

```
# Python venv
past/.venv/
```

- [ ] **Step 3: Create the venv and install deps**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter/past
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Verify system deps are present**

```bash
which pdftoppm && which tesseract
```

Expected: two paths printed. If either is missing, install it:
```bash
brew install poppler tesseract
```

- [ ] **Step 5: Create test directory**

```bash
mkdir -p /Users/ryan/Documents/Projects/Railsplitter/past/tests
touch /Users/ryan/Documents/Projects/Railsplitter/past/tests/__init__.py
```

- [ ] **Step 6: Commit scaffold**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/requirements.txt past/tests/__init__.py .gitignore
git commit -m "feat: scaffold PDF backfill script venv and test dir"
```

---

### Task 2: Utility functions — slugify, parse_byline, detect_section

**Files:**
- Create: `past/extract.py` (initial version — utils only)
- Create/Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write the failing tests**

Create `past/tests/test_extract.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extract import slugify, parse_byline, detect_section, is_known_section

# slugify

def test_slugify_basic():
    assert slugify("One Billion Reasons to Fill Out a Bracket") == "one-billion-reasons-to-fill-out-a-bracket"

def test_slugify_special_chars():
    assert slugify("Tiger's Win: 9–1!") == "tigers-win-9-1"

def test_slugify_truncates_at_60():
    long = "A Very Long Headline That Goes Well Beyond The Sixty Character Limit Here"
    result = slugify(long)
    assert len(result) <= 60

def test_slugify_strips_trailing_hyphens():
    result = slugify("Hello World!!!")
    assert not result.endswith('-')

def test_slugify_collapses_multiple_hyphens():
    assert '--' not in slugify("Hello  --  World")

# parse_byline

def test_parse_byline_strips_by():
    assert parse_byline("By Ryan Lu") == "Ryan Lu"

def test_parse_byline_strips_uppercase_by():
    assert parse_byline("BY RYAN LU") == "RYAN LU"

def test_parse_byline_strips_written_by():
    assert parse_byline("Written By Jane Doe") == "Jane Doe"

def test_parse_byline_no_prefix():
    assert parse_byline("Ryan Lu") == "Ryan Lu"

def test_parse_byline_strips_whitespace():
    assert parse_byline("  By  Ryan Lu  ") == "Ryan Lu"

# detect_section / is_known_section

def test_detect_section_sports():
    assert detect_section("SPORTS") == "sports"

def test_detect_section_opinion():
    assert detect_section("OPINION") == "opinion"

def test_detect_section_news_variants():
    assert detect_section("NEWS") == "news"
    assert detect_section("LINCOLN NEWS") == "news"

def test_detect_section_case_insensitive():
    assert detect_section("Sports") == "sports"

def test_detect_section_unknown_defaults_to_news():
    assert detect_section("ADVERTISEMENTS") == "news"

def test_is_known_section_true():
    assert is_known_section("SPORTS") is True

def test_is_known_section_false():
    assert is_known_section("ADVERTISEMENTS") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter/past
source .venv/bin/activate
pytest tests/test_extract.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'slugify' from 'extract'` (or ModuleNotFoundError since extract.py doesn't exist yet).

- [ ] **Step 3: Create `past/extract.py` with utility functions**

```python
import re
import sys
import json
import shutil
import argparse
from pathlib import Path

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

CONTENT_JSON = Path(__file__).parent.parent / 'content.json'

SECTION_MAP = {
    'NEWS': 'news',
    'LINCOLN NEWS': 'news',
    'FEATURES': 'features',
    'FEATURE': 'features',
    'OPINION': 'opinion',
    'OPINIONS': 'opinion',
    'SPORTS': 'sports',
    'SPORT': 'sports',
    'REVIEWS': 'reviews',
    'REVIEW': 'reviews',
}


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"['’]", '', text)          # drop apostrophes
    text = re.sub(r'[^a-z0-9]+', '-', text)        # non-alphanum → hyphen
    text = text.strip('-')
    text = re.sub(r'-+', '-', text)                 # collapse runs
    if len(text) > max_len:
        text = text[:max_len].rstrip('-')
    return text


def parse_byline(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^(?:Written\s+By|BY|By)\s+', '', text, flags=re.IGNORECASE)
    return text.strip()


def detect_section(text: str) -> str:
    return SECTION_MAP.get(text.strip().upper(), 'news')


def is_known_section(text: str) -> bool:
    return text.strip().upper() in SECTION_MAP
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "slugify or byline or section"
```

Expected: all matching tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add slugify, parse_byline, detect_section utilities"
```

---

### Task 3: parse_issue_info

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
from extract import parse_issue_info

def test_parse_issue_info_standard():
    result = parse_issue_info("Issue 3, December 2025")
    assert result == {
        'number': '3', 'date': 'December 2025',
        'id': 'issue-3', 'title': 'Issue 3',
    }

def test_parse_issue_info_pipe_separator():
    result = parse_issue_info("Issue 6 | April 2026")
    assert result is not None
    assert result['number'] == '6'
    assert result['date'] == 'April 2026'

def test_parse_issue_info_embedded_in_longer_text():
    text = "THE RAILSPLITTER | Issue 5, March 2026 | Lincoln High School"
    result = parse_issue_info(text)
    assert result is not None
    assert result['number'] == '5'

def test_parse_issue_info_no_match_returns_none():
    assert parse_issue_info("The Railsplitter Student Newspaper") is None

def test_parse_issue_info_id_format():
    result = parse_issue_info("Issue 12, May 2025")
    assert result['id'] == 'issue-12'
    assert result['title'] == 'Issue 12'
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "issue_info"
```

Expected: ImportError or AttributeError — `parse_issue_info` not defined.

- [ ] **Step 3: Implement `parse_issue_info` in `past/extract.py`**

Add after `is_known_section`:

```python
_ISSUE_RE = re.compile(
    r'[Ii]ssue\s+(\d+)\s*[,|]\s*([A-Za-z]+\s+\d{4})',
    re.IGNORECASE,
)


def parse_issue_info(text: str) -> dict | None:
    """Parse issue number and date from masthead text.
    Returns {'number', 'date', 'id', 'title'} or None.
    """
    m = _ISSUE_RE.search(text)
    if not m:
        return None
    number = m.group(1)
    date_str = m.group(2).strip()
    return {
        'number': number,
        'date': date_str,
        'id': f'issue-{number}',
        'title': f'Issue {number}',
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "issue_info"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add parse_issue_info for masthead parsing"
```

---

### Task 4: cluster_into_blocks

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
from extract import cluster_into_blocks

def _make_ocr(words):
    """words: list of (text, block_num, left, top, width, height, conf)"""
    data = {k: [] for k in ('level','block_num','par_num','line_num',
                             'word_num','left','top','width','height','conf','text','page_num')}
    for text, block_num, left, top, width, height, conf in words:
        data['level'].append(5)
        data['block_num'].append(block_num)
        data['par_num'].append(1)
        data['line_num'].append(1)
        data['word_num'].append(1)
        data['left'].append(left)
        data['top'].append(top)
        data['width'].append(width)
        data['height'].append(height)
        data['conf'].append(conf)
        data['text'].append(text)
        data['page_num'].append(1)
    return data

def test_cluster_groups_by_block_num():
    data = _make_ocr([
        ('Hello', 1, 10, 10, 50, 20, 90),
        ('World', 1, 70, 10, 50, 20, 85),
        ('Other', 2, 10, 100, 50, 20, 80),
    ])
    blocks = cluster_into_blocks(data)
    assert len(blocks) == 2
    assert 'Hello World' in blocks[0]['text']
    assert 'Other' in blocks[1]['text']

def test_cluster_skips_empty_text():
    data = _make_ocr([
        ('', 1, 10, 10, 50, 20, 90),
        ('Hello', 1, 70, 10, 50, 20, 85),
    ])
    blocks = cluster_into_blocks(data)
    assert len(blocks) == 1

def test_cluster_skips_negative_confidence():
    data = _make_ocr([
        ('Ghost', 1, 10, 10, 50, 20, -1),
        ('Real', 1, 70, 10, 50, 20, 80),
    ])
    blocks = cluster_into_blocks(data)
    assert 'Ghost' not in blocks[0]['text']

def test_cluster_computes_avg_word_height():
    data = _make_ocr([
        ('Big', 1, 10, 10, 50, 60, 90),
        ('text', 1, 70, 10, 50, 40, 90),
    ])
    blocks = cluster_into_blocks(data)
    assert blocks[0]['avg_word_height'] == 50.0

def test_cluster_sorted_by_top():
    data = _make_ocr([
        ('Lower', 2, 10, 200, 50, 20, 90),
        ('Upper', 1, 10, 10, 50, 20, 90),
    ])
    blocks = cluster_into_blocks(data)
    assert blocks[0]['text'] == 'Upper'
    assert blocks[1]['text'] == 'Lower'

def test_cluster_empty_data_returns_empty():
    data = _make_ocr([])
    assert cluster_into_blocks(data) == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "cluster"
```

Expected: ImportError — `cluster_into_blocks` not defined.

- [ ] **Step 3: Implement `cluster_into_blocks` in `past/extract.py`**

Add after `parse_issue_info`:

```python
def cluster_into_blocks(ocr_data: dict) -> list[dict]:
    """Groups pytesseract word-level data into text blocks using block_num.
    Returns list of block dicts sorted by top coordinate.
    """
    raw: dict[int, dict] = {}
    for i, level in enumerate(ocr_data['level']):
        if level != 5:
            continue
        text = ocr_data['text'][i].strip()
        if not text:
            continue
        conf = int(ocr_data['conf'][i])
        if conf < 0:
            continue
        bn = ocr_data['block_num'][i]
        left = ocr_data['left'][i]
        top = ocr_data['top'][i]
        w = ocr_data['width'][i]
        h = ocr_data['height'][i]
        if bn not in raw:
            raw[bn] = {
                'texts': [], 'confs': [], 'word_heights': [],
                'left': left, 'top': top, 'right': left + w, 'bottom': top + h,
            }
        b = raw[bn]
        b['texts'].append(text)
        b['confs'].append(conf)
        b['word_heights'].append(h)
        b['left'] = min(b['left'], left)
        b['top'] = min(b['top'], top)
        b['right'] = max(b['right'], left + w)
        b['bottom'] = max(b['bottom'], top + h)

    result = []
    for bn, b in sorted(raw.items()):
        wh = b['word_heights']
        confs = b['confs']
        result.append({
            'block_num': bn,
            'text': ' '.join(b['texts']),
            'avg_word_height': sum(wh) / len(wh),
            'avg_conf': sum(confs) / len(confs),
            'left': b['left'],
            'top': b['top'],
            'width': b['right'] - b['left'],
            'height': b['bottom'] - b['top'],
        })

    return sorted(result, key=lambda b: b['top'])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "cluster"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add cluster_into_blocks for OCR block grouping"
```

---

### Task 5: classify_blocks and segment_articles

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
from extract import classify_blocks, segment_articles

def _block(text, avg_word_height, top, avg_conf=85, left=10):
    return {
        'block_num': 1,
        'text': text,
        'avg_word_height': avg_word_height,
        'avg_conf': avg_conf,
        'left': left,
        'top': top,
        'width': 200,
        'height': 30,
    }

PAGE_HEIGHT = 3300  # 11 inches at 300 DPI

# classify_blocks

def test_classify_headline_large_font():
    blocks = [
        _block('SPORTS', 80, 30),          # tallest at top → section_banner
        _block('Tiger Baseball Wins', 75, 200),  # headline
        _block('Body text here', 20, 400), # body
    ]
    classified = classify_blocks(blocks, PAGE_HEIGHT)
    roles = {b['text']: b['role'] for b in classified}
    assert roles['SPORTS'] == 'section_banner'
    assert roles['Tiger Baseball Wins'] == 'headline'
    assert roles['Body text here'] == 'body'

def test_classify_dek_medium_font():
    blocks = [
        _block('Big Headline', 70, 200),
        _block('A sub-headline description here', 30, 280),
        _block('Body text body text', 18, 400),
    ]
    classified = classify_blocks(blocks, PAGE_HEIGHT)
    roles = {b['text']: b['role'] for b in classified}
    assert roles['A sub-headline description here'] == 'dek'

def test_classify_byline_by_prefix():
    blocks = [
        _block('Big Headline', 70, 200),
        _block('By Jane Doe', 20, 310),
        _block('Body text here', 18, 400),
    ]
    classified = classify_blocks(blocks, PAGE_HEIGHT)
    roles = {b['text']: b['role'] for b in classified}
    assert roles['By Jane Doe'] == 'byline'

def test_classify_empty_returns_empty():
    assert classify_blocks([], PAGE_HEIGHT) == []

# segment_articles

def test_segment_groups_by_headline():
    classified = [
        {'text': 'SPORTS', 'role': 'section_banner', 'avg_conf': 90, 'top': 10},
        {'text': 'Tiger Baseball', 'role': 'headline', 'avg_conf': 88, 'top': 100},
        {'text': 'By Ryan Lu', 'role': 'byline', 'avg_conf': 85, 'top': 200},
        {'text': 'Body text one.', 'role': 'body', 'avg_conf': 82, 'top': 300},
        {'text': 'Volleyball Recap', 'role': 'headline', 'avg_conf': 87, 'top': 400},
        {'text': 'Body text two.', 'role': 'body', 'avg_conf': 81, 'top': 500},
    ]
    articles = segment_articles(classified)
    assert len(articles) == 2
    assert articles[0]['headline'] == 'Tiger Baseball'
    assert articles[0]['section'] == 'sports'
    assert articles[0]['byline'] == 'Ryan Lu'
    assert 'Body text one.' in articles[0]['body_texts']
    assert articles[1]['headline'] == 'Volleyball Recap'

def test_segment_propagates_section_banner():
    classified = [
        {'text': 'OPINION', 'role': 'section_banner', 'avg_conf': 90, 'top': 10},
        {'text': 'My Hot Take', 'role': 'headline', 'avg_conf': 88, 'top': 100},
        {'text': 'Body.', 'role': 'body', 'avg_conf': 80, 'top': 200},
    ]
    articles = segment_articles(classified)
    assert articles[0]['section'] == 'opinion'

def test_segment_empty_returns_empty():
    assert segment_articles([]) == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "classify or segment"
```

Expected: ImportError — functions not defined.

- [ ] **Step 3: Implement `classify_blocks` in `past/extract.py`**

Add after `cluster_into_blocks`:

```python
_BYLINE_PREFIXES = ('BY ', 'BY\n', 'WRITTEN BY')


def classify_blocks(blocks: list[dict], page_height: int) -> list[dict]:
    """Adds a 'role' key to each block.
    Roles: section_banner, headline, dek, byline, body.
    """
    if not blocks:
        return []

    max_h = max(b['avg_word_height'] for b in blocks)

    classified = []
    for b in blocks:
        block = dict(b)
        rel_h = b['avg_word_height'] / max_h if max_h > 0 else 0
        top_frac = b['top'] / page_height if page_height > 0 else 0
        words = b['text'].split()
        upper = b['text'].upper()

        if rel_h > 0.55 and top_frac < 0.12:
            block['role'] = 'section_banner'
        elif rel_h > 0.55:
            block['role'] = 'headline'
        elif any(upper.startswith(p) for p in _BYLINE_PREFIXES) and len(words) <= 8:
            block['role'] = 'byline'
        elif rel_h > 0.28 and len(words) <= 30:
            block['role'] = 'dek'
        else:
            block['role'] = 'body'

        classified.append(block)

    return classified
```

- [ ] **Step 4: Implement `segment_articles` in `past/extract.py`**

Add after `classify_blocks`:

```python
def segment_articles(classified_blocks: list[dict]) -> list[dict]:
    """Groups classified blocks into raw article dicts."""
    articles: list[dict] = []
    current: dict | None = None
    current_section = 'news'

    for block in classified_blocks:
        role = block['role']

        if role == 'section_banner':
            if not is_known_section(block['text']):
                print(f'  Unknown section "{block["text"]}" — defaulting to news')
            current_section = detect_section(block['text'])
        elif role == 'headline':
            if current is not None:
                articles.append(current)
            current = {
                'headline': block['text'],
                'headline_conf': block['avg_conf'],
                'dek': '',
                'dek_conf': 0.0,
                'byline': '',
                'body_texts': [],
                'body_confs': [],
                'section': current_section,
            }
        elif role == 'dek' and current is not None and not current['dek']:
            current['dek'] = block['text']
            current['dek_conf'] = block['avg_conf']
        elif role == 'byline' and current is not None and not current['byline']:
            current['byline'] = parse_byline(block['text'])
        elif role == 'body' and current is not None:
            current['body_texts'].append(block['text'])
            current['body_confs'].append(block['avg_conf'])

    if current is not None:
        articles.append(current)

    return articles
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "classify or segment"
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add classify_blocks and segment_articles"
```

---

### Task 6: build_article

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
from extract import build_article

def _raw_article(**overrides):
    base = {
        'headline': 'Tiger Baseball Wins Big',
        'headline_conf': 85.0,
        'dek': 'Lincoln crushed the Falcons 9-1.',
        'dek_conf': 80.0,
        'byline': 'Ryan Lu',
        'body_texts': ['First paragraph.', 'Second paragraph.'],
        'body_confs': [82.0, 78.0],
        'section': 'sports',
    }
    base.update(overrides)
    return base

def test_build_article_id_is_slugified():
    article, _ = build_article(_raw_article(), 'Issue 6, April 2026', 'issue-6')
    assert article['id'] == 'tiger-baseball-wins-big'

def test_build_article_fields():
    article, _ = build_article(_raw_article(), 'Issue 6, April 2026', 'issue-6')
    assert article['title'] == 'Tiger Baseball Wins Big'
    assert article['author'] == 'Ryan Lu'
    assert article['section'] == 'sports'
    assert article['issue'] == 'Issue 6, April 2026'
    assert article['issueId'] == 'issue-6'
    assert article['ph'] == 'img-ph--sports'
    assert article['credit'] == ''
    assert article['photo'] is None

def test_build_article_body_wrapped_in_p_tags():
    article, _ = build_article(_raw_article(), 'Issue 6, April 2026', 'issue-6')
    assert article['body'] == '<p>First paragraph.</p><p>Second paragraph.</p>'

def test_build_article_published_true_when_conf_high():
    article, _ = build_article(_raw_article(), 'Issue 6, April 2026', 'issue-6')
    assert article['published'] is True

def test_build_article_published_false_when_conf_low():
    raw = _raw_article(headline_conf=40.0, body_confs=[35.0, 30.0])
    article, avg_conf = build_article(raw, 'Issue 3, Dec 2025', 'issue-3')
    assert article['published'] is False
    assert avg_conf < 60

def test_build_article_dek_omitted_when_conf_below_70():
    raw = _raw_article(dek='A dek.', dek_conf=65.0)
    article, _ = build_article(raw, 'Issue 6, April 2026', 'issue-6')
    assert article['dek'] == ''

def test_build_article_dek_included_when_conf_70_or_above():
    raw = _raw_article(dek='A dek.', dek_conf=70.0)
    article, _ = build_article(raw, 'Issue 6, April 2026', 'issue-6')
    assert article['dek'] == 'A dek.'

def test_build_article_body_empty_when_conf_below_60():
    raw = _raw_article(headline_conf=45.0, body_confs=[40.0])
    article, _ = build_article(raw, 'Issue 3, Dec 2025', 'issue-3')
    assert article['body'] == ''

def test_build_article_no_byline_defaults_to_railsplitter():
    raw = _raw_article(byline='')
    article, _ = build_article(raw, 'Issue 6, April 2026', 'issue-6')
    assert article['author'] == 'The Railsplitter'

def test_build_article_returns_avg_conf():
    # headline_conf=85, body_confs=[82, 78] → avg = (85+82+78)/3 = 81.67
    raw = _raw_article(headline_conf=85.0, body_confs=[82.0, 78.0])
    _, avg_conf = build_article(raw, 'Issue 6, April 2026', 'issue-6')
    assert abs(avg_conf - 81.67) < 0.1
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "build_article"
```

Expected: ImportError — `build_article` not defined.

- [ ] **Step 3: Implement `build_article` in `past/extract.py`**

Add after `segment_articles`:

```python
def build_article(raw: dict, issue_str: str, issue_id: str) -> tuple[dict, float]:
    """Converts raw article dict to content.json shape.
    Returns (article_dict, avg_conf).
    """
    all_confs = [raw['headline_conf']] + raw['body_confs']
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0

    dek = raw['dek'] if raw['dek'] and raw['dek_conf'] >= 70 else ''
    body = ''
    if avg_conf >= 60 and raw['body_texts']:
        body = ''.join(f'<p>{t}</p>' for t in raw['body_texts'])

    section = raw['section']
    article = {
        'id': slugify(raw['headline']),
        'title': raw['headline'],
        'author': raw['byline'] or 'The Railsplitter',
        'section': section,
        'issue': issue_str,
        'issueId': issue_id,
        'dek': dek,
        'body': body,
        'ph': f'img-ph--{section}',
        'credit': '',
        'photo': None,
        'published': avg_conf >= 60,
    }
    return article, avg_conf
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "build_article"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add build_article converting raw OCR to content.json shape"
```

---

### Task 7: merge_into_content_json

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
import json
import tempfile
from extract import merge_into_content_json

def _make_content_json(tmp_path, articles=None, issues=None):
    data = {
        'sections': [{'slug': 'news', 'title': 'Lincoln News', 'ph': 'img-ph--news'}],
        'issues': issues or [],
        'articles': articles or [],
    }
    p = tmp_path / 'content.json'
    p.write_text(json.dumps(data))
    return p

def _article(id, section='news'):
    return {'id': id, 'title': id, 'author': 'Test', 'section': section,
            'issue': 'Issue 1', 'issueId': 'issue-1', 'dek': '', 'body': '',
            'ph': f'img-ph--{section}', 'credit': '', 'photo': None, 'published': True}

def _issue(id, number='1'):
    return {'id': id, 'title': f'Issue {number}', 'date': 'Jan 2025', 'coverArticle': 'first-article'}

def test_merge_adds_new_articles(tmp_path):
    p = _make_content_json(tmp_path)
    articles_added, _ = merge_into_content_json([_article('new-article')], [], p)
    assert articles_added == 1
    data = json.loads(p.read_text())
    assert any(a['id'] == 'new-article' for a in data['articles'])

def test_merge_skips_duplicate_articles(tmp_path):
    existing = _article('existing-article')
    p = _make_content_json(tmp_path, articles=[existing])
    articles_added, _ = merge_into_content_json([_article('existing-article')], [], p)
    assert articles_added == 0
    data = json.loads(p.read_text())
    assert sum(1 for a in data['articles'] if a['id'] == 'existing-article') == 1

def test_merge_adds_new_issues(tmp_path):
    p = _make_content_json(tmp_path)
    _, issues_added = merge_into_content_json([], [_issue('issue-3', '3')], p)
    assert issues_added == 1
    data = json.loads(p.read_text())
    assert any(i['id'] == 'issue-3' for i in data['issues'])

def test_merge_skips_duplicate_issues(tmp_path):
    p = _make_content_json(tmp_path, issues=[_issue('issue-3', '3')])
    _, issues_added = merge_into_content_json([], [_issue('issue-3', '3')], p)
    assert issues_added == 0

def test_merge_idempotent(tmp_path):
    p = _make_content_json(tmp_path)
    article = _article('my-article')
    issue = _issue('issue-1')
    merge_into_content_json([article], [issue], p)
    merge_into_content_json([article], [issue], p)
    data = json.loads(p.read_text())
    assert sum(1 for a in data['articles'] if a['id'] == 'my-article') == 1
    assert sum(1 for i in data['issues'] if i['id'] == 'issue-1') == 1

def test_merge_preserves_existing_data(tmp_path):
    existing = _article('old-article')
    p = _make_content_json(tmp_path, articles=[existing])
    merge_into_content_json([_article('new-article')], [], p)
    data = json.loads(p.read_text())
    ids = [a['id'] for a in data['articles']]
    assert 'old-article' in ids
    assert 'new-article' in ids
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "merge"
```

Expected: ImportError — `merge_into_content_json` not defined.

- [ ] **Step 3: Implement `merge_into_content_json` in `past/extract.py`**

Add after `build_article`:

```python
def merge_into_content_json(
    new_articles: list[dict],
    new_issues: list[dict],
    content_path: Path,
) -> tuple[int, int]:
    """Merges articles and issues into content.json idempotently.
    Returns (articles_added, issues_added).
    """
    data = json.loads(content_path.read_text(encoding='utf-8'))

    existing_article_ids = {a['id'] for a in data['articles']}
    existing_issue_ids = {i['id'] for i in data['issues']}

    articles_added = 0
    for article in new_articles:
        if article['id'] in existing_article_ids:
            print(f'  Skipping duplicate: "{article["id"]}"')
            continue
        data['articles'].append(article)
        existing_article_ids.add(article['id'])
        articles_added += 1

    issues_added = 0
    for issue in new_issues:
        if issue['id'] in existing_issue_ids:
            continue
        data['issues'].append(issue)
        existing_issue_ids.add(issue['id'])
        issues_added += 1

    content_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return articles_added, issues_added
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "merge"
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add merge_into_content_json with duplicate protection"
```

---

### Task 8: System dependency checks

**Files:**
- Modify: `past/extract.py`
- Modify: `past/tests/test_extract.py`

- [ ] **Step 1: Write failing tests**

Append to `past/tests/test_extract.py`:

```python
from unittest.mock import patch
from extract import check_poppler, check_tesseract

def test_check_poppler_found():
    with patch('shutil.which', return_value='/usr/bin/pdftoppm'):
        assert check_poppler() is True

def test_check_poppler_not_found():
    with patch('shutil.which', return_value=None):
        assert check_poppler() is False

def test_check_tesseract_found():
    with patch('shutil.which', return_value='/usr/bin/tesseract'):
        assert check_tesseract() is True

def test_check_tesseract_not_found():
    with patch('shutil.which', return_value=None):
        assert check_tesseract() is False
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_extract.py -v -k "check_poppler or check_tesseract"
```

Expected: ImportError — functions not defined.

- [ ] **Step 3: Implement checks in `past/extract.py`**

Add after the imports block (before CONTENT_JSON):

```python
def check_poppler() -> bool:
    return shutil.which('pdftoppm') is not None


def check_tesseract() -> bool:
    return shutil.which('tesseract') is not None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v -k "check_poppler or check_tesseract"
```

Expected: all PASS.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
pytest tests/test_extract.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py past/tests/test_extract.py
git commit -m "feat: add check_poppler and check_tesseract dependency checks"
```

---

### Task 9: process_pdf pipeline and main CLI

**Files:**
- Modify: `past/extract.py`

- [ ] **Step 1: Implement `process_pdf` in `past/extract.py`**

Add after `merge_into_content_json`:

```python
def process_pdf(pdf_path: Path) -> dict:
    """Runs the full pipeline for one PDF.
    Returns a summary dict with keys: issue_str, pages, articles_added,
    published, flagged (list of (title, avg_conf)), issues_added.
    """
    images = convert_from_path(str(pdf_path), dpi=300)

    all_raw_articles: list[dict] = []
    issue_info: dict | None = None

    for page_num, image in enumerate(images, start=1):
        page_width, page_height = image.size
        ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)

        # Try to grab issue info from first two pages
        if issue_info is None and page_num <= 2:
            page_text = ' '.join(t for t in ocr_data['text'] if t.strip())
            issue_info = parse_issue_info(page_text)

        blocks = cluster_into_blocks(ocr_data)
        if not blocks:
            print(f'  Skipping page {page_num} — no headline detected (photo spread or ad?)')
            continue

        classified = classify_blocks(blocks, page_height)
        if not any(b['role'] == 'headline' for b in classified):
            print(f'  Skipping page {page_num} — no headline detected (photo spread or ad?)')
            continue

        page_articles = segment_articles(classified)
        all_raw_articles.extend(page_articles)

    issue_str = f"{issue_info['title']}, {issue_info['date']}" if issue_info else 'Unknown Issue'
    issue_id = issue_info['id'] if issue_info else 'issue-unknown'

    built_articles: list[dict] = []
    flagged: list[tuple[str, float]] = []

    for raw in all_raw_articles:
        article, avg_conf = build_article(raw, issue_str, issue_id)
        built_articles.append(article)
        if avg_conf < 60:
            flagged.append((article['title'], avg_conf))

    new_issues: list[dict] = []
    if issue_info and built_articles:
        new_issues = [{
            'id': issue_info['id'],
            'title': issue_info['title'],
            'date': issue_info['date'],
            'coverArticle': built_articles[0]['id'],
        }]

    articles_added, issues_added = merge_into_content_json(
        built_articles, new_issues, CONTENT_JSON
    )

    published = sum(1 for a in built_articles if a['published'])
    return {
        'issue_str': issue_str,
        'pages': len(images),
        'articles_added': articles_added,
        'published': published,
        'flagged': flagged,
        'issues_added': issues_added,
    }
```

- [ ] **Step 2: Implement `main` in `past/extract.py`**

Add at the end of the file:

```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract articles from a Railsplitter PDF into content.json'
    )
    parser.add_argument('pdf', help='Path to the PDF file (relative or absolute)')
    args = parser.parse_args()

    if not check_poppler():
        print('Error: poppler not found. Run: brew install poppler')
        sys.exit(1)

    if not check_tesseract():
        print('Error: tesseract not found. Run: brew install tesseract')
        sys.exit(1)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f'Error: PDF not found: {pdf_path}')
        sys.exit(1)

    summary = process_pdf(pdf_path)

    flagged_count = len(summary['flagged'])
    print(f"\n{summary['issue_str']} — {summary['pages']} pages processed")
    print(f"  ✓ {summary['articles_added']} articles added "
          f"({summary['published']} published, {flagged_count} flagged for review)")
    if summary['issues_added']:
        print(f"  ✓ {summary['issues_added']} new issues added to content.json")
    for title, conf in summary['flagged']:
        print(f'  ⚠ Low confidence: "{title}" (avg {conf:.0f}%) → published: false')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run full test suite to confirm everything still passes**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter/past
source .venv/bin/activate
pytest tests/test_extract.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add past/extract.py
git commit -m "feat: add process_pdf pipeline and main CLI entrypoint"
```

---

### Task 10: Smoke test on a real PDF

This task is manual — no unit tests. Verify the script works end-to-end on one of the real PDFs.

- [ ] **Step 1: Back up content.json**

```bash
cp /Users/ryan/Documents/Projects/Railsplitter/content.json \
   /Users/ryan/Documents/Projects/Railsplitter/content.json.bak
```

- [ ] **Step 2: Run the script on the smallest PDF**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter/past
source .venv/bin/activate
python extract.py RailsplitterIssue3December2026.pdf
```

Expected: console output showing issue name, page count, articles added, and any flagged articles.

- [ ] **Step 3: Inspect extracted articles**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
python3 -c "
import json
data = json.load(open('content.json'))
new = [a for a in data['articles'] if 'issue-3' in (a.get('issueId') or '')]
for a in new:
    print(a['id'], '|', a['title'][:50], '| pub:', a['published'])
"
```

Expected: a list of article IDs and titles from the December issue. Check that:
- IDs are reasonable slugs (no garbled characters)
- Titles look correct
- `published: false` articles are ones that visually appear low-quality in the PDF

- [ ] **Step 4: If OCR quality is poor, tune classification thresholds**

If most articles come out as body-only with no headlines detected, the `rel_h` thresholds in `classify_blocks` may need adjustment. Open one page image and check word heights:

```python
# Run this in a Python REPL in the venv
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

images = convert_from_path('RailsplitterIssue3December2026.pdf', dpi=300)
data = pytesseract.image_to_data(images[1], output_type=Output.DICT)
# Print unique word heights to understand the font size range
heights = [data['height'][i] for i, l in enumerate(data['level']) if l == 5 and data['text'][i].strip()]
print(sorted(set(heights)))
```

Adjust `0.55` and `0.28` thresholds in `classify_blocks` based on the actual height distribution. Headlines should be the top 2-3 height values; body text the lowest cluster.

- [ ] **Step 5: If satisfied, restore or keep the updated content.json**

If results look good:
```bash
rm /Users/ryan/Documents/Projects/Railsplitter/content.json.bak
```

If results need cleanup:
```bash
cp /Users/ryan/Documents/Projects/Railsplitter/content.json.bak \
   /Users/ryan/Documents/Projects/Railsplitter/content.json
# Fix thresholds, re-run
```

- [ ] **Step 6: Run on remaining PDFs**

```bash
python extract.py FinalRailsplitterIssue5Spring2026.pdf
python extract.py RaillsplitterIssue6April20264.pdf
python extract.py Railsplitter2026Issue42.pdf
```

- [ ] **Step 7: Commit final state**

```bash
cd /Users/ryan/Documents/Projects/Railsplitter
git add content.json past/extract.py
git commit -m "feat: backfill articles from past PDF issues via OCR extraction"
```
