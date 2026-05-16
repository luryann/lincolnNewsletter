# PDF Backfill Script — Design Spec

**Date:** 2026-05-15  
**Project:** The Railsplitter

## Overview

A Python script (`past/extract.py`) that processes image-based newspaper PDFs from `/past/` and backfills extracted articles into `content.json`. It uses block-level OCR (pytesseract) to handle multi-column newspaper layouts, segments articles by headline detection, and merges results into the live data file idempotently.

## Invocation

```bash
cd past
source .venv/bin/activate
python extract.py RailsplitterIssue3December2026.pdf
```

Dependencies are installed in a venv at `past/.venv/`. A `past/requirements.txt` is included. Requires `poppler` installed via Homebrew (`brew install poppler`).

## Pipeline

1. **PDF → images** — `pdf2image.convert_from_path()` renders each page at 300 DPI to a PIL Image.
2. **Block-level OCR** — `pytesseract.image_to_data()` returns per-word bounding boxes and confidence scores. Words are clustered into text blocks by proximity (gap threshold ~20px vertically, ~10px horizontally within a line).
3. **Article segmentation** — blocks are classified by relative font size:
   - Largest blocks (top ~15% height relative to page) → headline candidates
   - Medium blocks immediately below a headline → dek candidates
   - Small italic/bold single-line blocks → byline candidates
   - Everything else between two headline blocks → body copy
4. **Section detection** — section banner text (e.g. "SPORTS", "OPINION") is detected at the top of each page and mapped to site slugs: `news`, `features`, `opinion`, `sports`, `reviews`. Unrecognized banners default to `"news"` with a console warning.
5. **Issue detection** — issue number and date are parsed from the cover page or masthead (e.g. "Issue 3, December 2025"). Used to populate `issue`, `issueId`, and to add a new entry to `content.json["issues"]` if not already present. The `coverArticle` field for new issues defaults to the first extracted article's `id`.
6. **Merge into content.json** — `content.json` is resolved relative to the script file (`../content.json` from `past/`), so it works regardless of working directory. New articles are appended. Articles whose slugified `id` already exists are skipped. Idempotent: running the script twice on the same PDF produces no duplicates.

## Data Model

Each extracted article maps to the existing `content.json` article shape:

| Field | Source |
|---|---|
| `id` | slugified headline (lowercase, hyphens, max 60 chars) |
| `title` | headline block text |
| `author` | byline block, stripped of "By " / "BY " prefix |
| `section` | detected section slug |
| `issue` | e.g. `"Issue 3, December 2025"` |
| `issueId` | e.g. `"issue-3"` |
| `dek` | block below headline if confidence ≥ 70%, else `""` |
| `body` | body blocks joined as `<p>` tags if avg confidence ≥ 60%, else `""` |
| `ph` | `"img-ph--<section>"` |
| `credit` | `""` |
| `photo` | `null` |
| `published` | `true` if avg OCR confidence ≥ 60%, else `false` |

## Confidence & Flagging

- Per-word confidence from pytesseract (0–100) is averaged per article.
- Articles with avg confidence < 60% are written with `"published": false` and logged as warnings.
- Articles with avg confidence ≥ 60% are written with `"published": true`.
- Deks are only extracted when their block confidence ≥ 70% (headline-adjacent blocks are sometimes stylized and OCR poorly).

## Error Handling

| Condition | Behavior |
|---|---|
| `poppler` not installed | Exit immediately with message: `Error: poppler not found. Run: brew install poppler` |
| PDF not found | Exit with clear path error |
| No headline detected on a page | Skip page, log: `Skipping page N — no headline detected (photo spread or ad?)` |
| Unrecognized section banner | Assign `"news"`, log: `Unknown section "<text>" on page N — defaulting to news` |
| Article ID already in content.json | Skip, log: `Skipping duplicate: "<id>"` |

## Console Output Format

```
Issue 3, December 2025 — 8 pages processed
  ✓ 14 articles extracted (12 published, 2 flagged for review)
  ✓ 2 new issues added to content.json
  ⚠ Low confidence: "Lincoln Tiger Cat" (avg 52%) → published: false
  ⚠ Low confidence: "Pi Day Recap" (avg 48%) → published: false
```

## File Layout

```
past/
  extract.py          # main script
  requirements.txt    # pdf2image, pytesseract, pillow
  .venv/              # gitignored
  *.pdf               # source issues
```

`past/.venv/` is gitignored. `past/requirements.txt` is committed.

## Out of Scope

- Photo/image extraction from PDFs
- Interactive review mode (review warnings after the run, edit content.json manually)
- Support for text-based (non-image) PDFs
- Windows support (poppler install path assumes macOS/Homebrew)
