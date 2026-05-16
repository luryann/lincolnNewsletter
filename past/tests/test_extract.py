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
