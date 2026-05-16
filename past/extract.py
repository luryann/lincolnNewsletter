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
