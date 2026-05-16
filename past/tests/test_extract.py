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
