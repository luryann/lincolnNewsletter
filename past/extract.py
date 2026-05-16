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
