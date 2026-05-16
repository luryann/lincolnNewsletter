import re
import sys
import json
import shutil
import argparse
from pathlib import Path

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output


def check_poppler() -> bool:
    return shutil.which('pdftoppm') is not None


def check_tesseract() -> bool:
    return shutil.which('tesseract') is not None


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
    text = re.sub(r"['']", '', text)          # drop apostrophes
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

        if rel_h > 0.55 and top_frac < 0.12 and is_known_section(b['text']):
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
