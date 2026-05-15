# Design: Issue Management, Photo Support & Print Format

**Date:** 2026-05-15
**Project:** The Railsplitter — Lincoln High School student newspaper

---

## Overview

Three interrelated features built around a new first-class Issue concept:

1. **Issue management** — formal issues in the data model and editor
2. **Photo support** — real images uploaded to the GitHub repo via API
3. **Print format** — dedicated newspaper-layout print page + clean `@media print` CSS

---

## 1. Data Model (`content.json`)

### New `issues` array (top-level)

```json
"issues": [
  {
    "id": "issue-6",
    "title": "Issue 6",
    "date": "April 2026",
    "coverArticle": "bracket"
  }
]
```

### Article changes

Two new optional fields per article:

| Field | Type | Notes |
|---|---|---|
| `issueId` | string \| null | References `issues[].id`. Replaces freeform `issue` string. |
| `photo` | string \| null | Repo-relative path, e.g. `"photos/bracket.jpg"`. Null = no photo. |

The existing `"issue"` string field is kept on all articles during migration. The site falls back to it when `issueId` is absent, so no article breaks before migration is complete. Migration happens via the editor's bulk-assign UI, not by hand.

---

## 2. Editor Changes (`editor.html`)

### 2a. Issues view

New sidebar nav item added between "Sections" and the "System" group, labelled **Issues**.

**List view:**
- Issues listed most-recent-first
- Each row: title, date, article count badge, **Print** button, **Edit** pencil
- **New Issue** button in topbar opens a creation modal

**Create/Edit modal fields:**
- Title (e.g. "Issue 7")
- Date (e.g. "May 2026")
- Cover article (dropdown of published articles)

**Edit issue — article assignment:**
- Below the metadata fields: a checklist of all articles
- Pre-checked if the article's `issueId` matches this issue (or its freeform `issue` string matches as a fallback)
- Saving the issue writes updated `issueId` fields to all affected articles in `content.json` via GitHub API

**Print button:** Opens `print.html?issue=<id>` in a new tab.

### 2b. Article editor — photo panel

Added above the existing placeholder color picker in the article edit right sidebar.

- **"Upload Photo"** button opens a native file picker (accepts jpg, jpeg, png, gif, webp)
- On file select:
  1. Read as base64
  2. Commit to `photos/<article-id>.<ext>` via GitHub API (create or update)
  3. Set `article.photo` to the repo-relative path
  4. Save `content.json` with updated photo field
- Shows a small `<img>` preview thumbnail once uploaded
- **"Remove"** link sets `photo` to null in the data (does not delete the file from the repo)
- Upload progress shown via the existing `.spinner` pattern
- Error shown via the existing `.notice-error` pattern

---

## 3. Print System

### 3a. `print.html` — dedicated print layout page

URL: `print.html?issue=<issue-id>`

**Entry point:** "Print" button in the Issues view of the editor (opens in new tab).

**Rendering:**
- Loads `content.json`, resolves the issue and all articles where `issueId` matches
- **Masthead row:** "The Railsplitter" wordmark, issue title + date, Lincoln High School tagline
- **Cover story:** full-width hero — large headline (display type), dek, author, photo (`<img>`) or placeholder block
- **Article grid:** 3-column broadsheet layout for remaining articles, each card showing hed, dek, author, and body text if present (italic note "Full article not yet written" if body is empty)
- Photos render as `<img>` tags; articles without photos use `div.img-ph` placeholder blocks
- No nav, no editor chrome, no tweaks panel
- **"Print"** button (top-right, screen-only) calls `window.print()` and hides itself via `@media print`

### 3b. `@media print` CSS in `styles.css`

Applied to the existing public pages:

**Hidden on print:**
- `.top-bar`, `nav`, `.tweaks-fab`, all `<button>` elements, `.survey-note` decorative blocks

**`article.html` print adjustments:**
- Single column, full width
- Body font switches to serif for readability
- Decorative horizontal rules removed
- `div.img-ph` blocks hidden (placeholder images don't print meaningfully)

**`section.html` print adjustments:**
- Clean article list: hed + dek + author per item, no placeholder image blocks
- Page breaks avoided mid-article-card (`break-inside: avoid`)

---

## 4. Article Page Changes (`article.html`)

The existing article-render JS checks `article.photo` on load:

- **Photo present:** Replace `div.img-ph` with `<img src="https://raw.githubusercontent.com/luryann/lincolnNewsletter/main/<photo>" alt="">`, preserve the credit line below
- **No photo:** Keep existing `div.img-ph` placeholder — no visible change

No changes to `section.html` or `index.html` — those show article cards and keep placeholder blocks.

---

## Files Touched

| File | Change |
|---|---|
| `content.json` | Add `issues[]`, add `issueId` + `photo` fields to articles |
| `editor.html` | Issues nav item + view, photo upload panel in article editor |
| `print.html` | New file — newspaper print layout |
| `styles.css` | `@media print` rules |
| `article.html` | Photo rendering logic in existing article JS |

---

## Out of Scope

- Public issues archive page (`issues.html`) — not requested
- Deleting photos from the repo (remove only nulls the reference)
- PDF generation library — browser native `window.print()` is sufficient
