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

# parse_issue_info

def test_parse_issue_info_standard():
    from extract import parse_issue_info
    result = parse_issue_info("Issue 3, December 2025")
    assert result == {
        'number': '3', 'date': 'December 2025',
        'id': 'issue-3', 'title': 'Issue 3',
    }

def test_parse_issue_info_pipe_separator():
    from extract import parse_issue_info
    result = parse_issue_info("Issue 6 | April 2026")
    assert result is not None
    assert result['number'] == '6'
    assert result['date'] == 'April 2026'

def test_parse_issue_info_embedded_in_longer_text():
    from extract import parse_issue_info
    text = "THE RAILSPLITTER | Issue 5, March 2026 | Lincoln High School"
    result = parse_issue_info(text)
    assert result is not None
    assert result['number'] == '5'

def test_parse_issue_info_no_match_returns_none():
    from extract import parse_issue_info
    assert parse_issue_info("The Railsplitter Student Newspaper") is None

def test_parse_issue_info_id_format():
    from extract import parse_issue_info
    result = parse_issue_info("Issue 12, May 2025")
    assert result['id'] == 'issue-12'
    assert result['title'] == 'Issue 12'

# cluster_into_blocks

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

# merge_into_content_json

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
