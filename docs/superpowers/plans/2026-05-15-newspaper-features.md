# Newspaper Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add formal issue management, photo uploads to the GitHub repo, and a newspaper print layout to The Railsplitter.

**Architecture:** `content.json` gains a top-level `issues[]` array and two new article fields (`issueId`, `photo`). The `editor.html` CMS gets an Issues nav view (list/create/edit + bulk article assignment) and a photo upload panel in the article editor. A new `print.html` page renders a 3-column broadsheet layout for a given issue. `article.html` gains photo rendering with a fallback to the existing placeholder. All GitHub API calls follow the existing pattern in `App.github`.

**Tech Stack:** Vanilla JS, plain HTML/CSS, GitHub Contents API (already integrated), no build system — open files directly in browser.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `content.json` | Modify | Add `issues[]`, add `issueId` + `photo` to all articles |
| `styles.css` | Modify | Add `@media print` block |
| `print.html` | Create | Newspaper broadsheet layout page |
| `editor.html` | Modify | Issues nav item, `App.issueById`, `App.github.uploadFile`, `App.views.issues`, photo panel in article editor |
| `article.html` | Modify | Photo rendering + issueId-aware issue label |

---

## Task 1: Data model — add issues + photo fields to content.json

**Files:**
- Modify: `content.json`

- [ ] **Step 1: Add `issues` array at the top of content.json**

Insert after the closing `]` of `"sections"` and before `"articles"`:

```json
  "issues": [
    { "id": "issue-6", "title": "Issue 6", "date": "April 2026", "coverArticle": "bracket" },
    { "id": "issue-5", "title": "Issue 5", "date": "March 2026", "coverArticle": "spark" }
  ],
```

- [ ] **Step 2: Add `issueId` and `photo: null` to every article**

Map each article's existing `"issue"` string to an `issueId`:
- `"Issue 6, April 2026"` or `"April 2026"` → `"issueId": "issue-6"`
- `"March 2026"` → `"issueId": "issue-5"`

Add `"photo": null` to every article.

Apply to all 23 articles. Example of one article after change:

```json
{
  "id": "bracket",
  "title": "One Billion Reasons to Fill Out a Bracket",
  "author": "Ryan Lu",
  "section": "sports",
  "issue": "Issue 6, April 2026",
  "issueId": "issue-6",
  "dek": "...",
  "body": "...",
  "ph": "img-ph--sports",
  "credit": "Photo · NCAA.com",
  "photo": null,
  "published": true
}
```

March 2026 articles that get `"issueId": "issue-5"`: `spark`, `nancyguth`, `chavez`, `ocean`.
All remaining articles get `"issueId": "issue-6"`.

- [ ] **Step 3: Verify structure**

Open browser console on any page and run:
```javascript
fetch('content.json').then(r=>r.json()).then(d=>console.log(d.issues, d.articles[0].issueId, d.articles[0].photo))
```
Expected output: `[{id:'issue-6',...},{id:'issue-5',...}]` `"issue-6"` `null`

- [ ] **Step 4: Commit**

```bash
git add content.json
git commit -m "feat: add issues array and issueId/photo fields to content.json"
```

---

## Task 2: Print CSS — @media print rules in styles.css

**Files:**
- Modify: `styles.css`

- [ ] **Step 1: Append @media print block to the end of styles.css**

```css
/* ── Print ───────────────────────────────────────────────────────────────── */
@media print {
  .top-bar,
  nav.nav,
  .tweaks-fab,
  .tweaks-panel,
  .related,
  footer.footer,
  .survey-note,
  button { display: none !important; }

  body { background: #fff; color: #000; font-size: 11pt; }

  /* article.html */
  .art-header { max-width: 100%; padding: 0; }
  .art-body   { max-width: 100%; column-count: 1; }
  .img-ph     { display: none; }
  .art-lead-img img { max-width: 100%; height: auto; }

  /* section.html */
  .sec-card .img-ph { display: none; }
  .sec-card { break-inside: avoid; border-bottom: 1px solid #ccc; padding-bottom: 12pt; margin-bottom: 12pt; }
}
```

- [ ] **Step 2: Verify**

Open `article.html?id=bracket` in browser → press Ctrl+P / Cmd+P → check print preview:
- Top bar hidden
- Nav hidden
- Tweaks FAB hidden
- Related section hidden
- Body text readable

- [ ] **Step 3: Commit**

```bash
git add styles.css
git commit -m "feat: add @media print rules for article and section pages"
```

---

## Task 3: print.html — newspaper broadsheet layout

**Files:**
- Create: `print.html`

- [ ] **Step 1: Create print.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Print — The Railsplitter</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:Georgia,'Times New Roman',serif;background:#fff;color:#111;font-size:10pt;padding:20px;}
.no-print-btn{position:fixed;top:16px;right:16px;background:#C85500;color:#fff;border:none;padding:10px 20px;font-size:14px;border-radius:5px;cursor:pointer;font-family:sans-serif;}
@media print{.no-print-btn{display:none;}}

/* Masthead */
.mast{text-align:center;border-top:3px solid #111;border-bottom:3px solid #111;padding:10px 0;margin-bottom:16px;}
.mast__name{font-size:36pt;font-weight:700;letter-spacing:-.02em;line-height:1;}
.mast__meta{font-size:9pt;color:#555;margin-top:4px;letter-spacing:.05em;text-transform:uppercase;}
.mast-rule{border:none;border-top:1px solid #111;margin:6px 0;}

/* Cover story */
.cover{border-bottom:2px solid #111;padding-bottom:16px;margin-bottom:16px;}
.cover__label{font-size:8pt;text-transform:uppercase;letter-spacing:.1em;color:#C85500;font-family:sans-serif;margin-bottom:4px;}
.cover__hed{font-size:28pt;font-weight:700;line-height:1.05;margin-bottom:8px;}
.cover__dek{font-size:12pt;color:#333;margin-bottom:8px;line-height:1.4;}
.cover__byline{font-size:9pt;color:#555;font-family:sans-serif;}
.cover__img{width:100%;max-height:260px;object-fit:cover;margin:10px 0;}
.cover__img-ph{width:100%;height:200px;background:#ddd;margin:10px 0;}
.cover__body{margin-top:10px;font-size:10pt;line-height:1.65;column-count:3;column-gap:20px;}
.cover__body p{margin-bottom:8pt;}
.cover__body h3{font-size:11pt;margin:10pt 0 4pt;column-span:none;}
.cover__body blockquote{border-left:3px solid #C85500;padding-left:8px;margin:8pt 0;font-style:italic;}

/* Article grid */
.grid-heading{font-size:9pt;text-transform:uppercase;letter-spacing:.1em;color:#888;font-family:sans-serif;margin-bottom:8px;border-bottom:1px solid #ddd;padding-bottom:4px;}
.grid{column-count:3;column-gap:20px;}
.art-card{break-inside:avoid;margin-bottom:14pt;padding-bottom:14pt;border-bottom:1px solid #ddd;}
.art-card__section{font-size:7.5pt;text-transform:uppercase;letter-spacing:.1em;color:#C85500;font-family:sans-serif;}
.art-card__hed{font-size:13pt;font-weight:700;line-height:1.15;margin:3pt 0 4pt;}
.art-card__dek{font-size:9pt;color:#444;line-height:1.4;margin-bottom:4pt;}
.art-card__byline{font-size:8pt;color:#888;font-family:sans-serif;}
.art-card__body{margin-top:6pt;font-size:9pt;line-height:1.55;}
.art-card__body p{margin-bottom:5pt;}
.art-card__img{width:100%;height:80px;object-fit:cover;margin-bottom:6pt;}
.art-card__img-ph{width:100%;height:60px;background:#e8e5e0;margin-bottom:6pt;}
.art-card__stub{font-size:8pt;color:#aaa;font-style:italic;margin-top:4pt;}
.error{padding:40px;text-align:center;font-family:sans-serif;color:#888;}
</style>
</head>
<body>

<button class="no-print-btn" onclick="window.print()">Print / Save PDF</button>
<div id="root"><p class="error">Loading…</p></div>

<script>
var RAW_BASE = 'https://raw.githubusercontent.com/luryann/lincolnNewsletter/main/';

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

var params  = new URLSearchParams(window.location.search);
var issueId = params.get('issue') || '';

fetch('content.json').then(function(r){ return r.json(); }).then(function(data) {
  var issues   = data.issues || [];
  var articles = data.articles || [];
  var sections = data.sections || [];

  var issue = issues.find(function(i){ return i.id === issueId; });
  if (!issue) {
    document.getElementById('root').innerHTML = '<p class="error">Issue not found: ' + esc(issueId) + '</p>';
    return;
  }

  var issueArticles = articles.filter(function(a){ return a.issueId === issueId && a.published; });
  var cover = issueArticles.find(function(a){ return a.id === issue.coverArticle; }) || issueArticles[0];
  var rest  = issueArticles.filter(function(a){ return !cover || a.id !== cover.id; });

  function sectionTitle(slug) {
    var s = sections.find(function(x){ return x.slug === slug; });
    return s ? s.title : slug;
  }

  function imgOrPh(article, isCover) {
    if (article.photo) {
      return '<img class="' + (isCover ? 'cover__img' : 'art-card__img') + '" src="' + esc(RAW_BASE + article.photo) + '" alt="">';
    }
    return '<div class="' + (isCover ? 'cover__img-ph' : 'art-card__img-ph') + '"></div>';
  }

  var coverHTML = '';
  if (cover) {
    var bodyHTML = '';
    if (cover.body) {
      bodyHTML = '<div class="cover__body">' + cover.body + '</div>';
    }
    coverHTML =
      '<div class="cover">' +
        '<div class="cover__label">' + esc(sectionTitle(cover.section)) + ' — Cover Story</div>' +
        imgOrPh(cover, true) +
        '<h1 class="cover__hed">' + esc(cover.title) + '</h1>' +
        '<p class="cover__dek">' + esc(cover.dek) + '</p>' +
        '<p class="cover__byline">By ' + esc(cover.author) + '</p>' +
        bodyHTML +
      '</div>';
  }

  var cardsHTML = rest.map(function(a) {
    var bodySnippet = '';
    if (a.body) {
      var tmp = document.createElement('div');
      tmp.innerHTML = a.body;
      var text = tmp.textContent || '';
      bodySnippet = '<div class="art-card__body"><p>' + esc(text.slice(0, 300)) + (text.length > 300 ? '…' : '') + '</p></div>';
    } else {
      bodySnippet = '<p class="art-card__stub">Full article not yet written.</p>';
    }
    return '<div class="art-card">' +
      '<div class="art-card__section">' + esc(sectionTitle(a.section)) + '</div>' +
      imgOrPh(a, false) +
      '<h2 class="art-card__hed">' + esc(a.title) + '</h2>' +
      '<p class="art-card__dek">' + esc(a.dek) + '</p>' +
      '<p class="art-card__byline">By ' + esc(a.author) + '</p>' +
      bodySnippet +
    '</div>';
  }).join('');

  document.title = issue.title + ', ' + issue.date + ' — The Railsplitter';
  document.getElementById('root').innerHTML =
    '<div class="mast">' +
      '<div class="mast__name">The Railsplitter</div>' +
      '<hr class="mast-rule">' +
      '<div class="mast__meta">Lincoln High School &nbsp;·&nbsp; Los Angeles, CA &nbsp;·&nbsp; ' + esc(issue.title) + ', ' + esc(issue.date) + '</div>' +
    '</div>' +
    coverHTML +
    (rest.length ? '<div class="grid-heading">More in this issue</div><div class="grid">' + cardsHTML + '</div>' : '');

}).catch(function(err) {
  document.getElementById('root').innerHTML = '<p class="error">Failed to load content: ' + esc(err.message) + '</p>';
});
</script>
</body>
</html>
```

- [ ] **Step 2: Verify**

Open `print.html?issue=issue-6` in browser. Confirm:
- Masthead shows "The Railsplitter" and "Issue 6, April 2026"
- Cover story (bracket article) appears full-width with headline and body text
- Remaining issue-6 articles appear in 3-column grid below
- "Print / Save PDF" button triggers browser print dialog
- Button is hidden in print preview

Then open `print.html?issue=issue-5` — confirm 4 March 2026 articles render with `spark` as cover story.

- [ ] **Step 3: Commit**

```bash
git add print.html
git commit -m "feat: add print.html newspaper broadsheet layout page"
```

---

## Task 4: Editor — add Issues sidebar nav item and helpers

**Files:**
- Modify: `editor.html`

- [ ] **Step 1: Add Issues nav item to sidebar HTML**

Find this block in `editor.html` (around line 146):
```html
      <button class="nav-item" data-view="sections">
```

Insert a new button **before** the `<div class="nav-label">System</div>` line:
```html
      <button class="nav-item" data-view="issues">
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"/></svg>
        Issues
      </button>
```

- [ ] **Step 2: Add `issueById` helper to the App object**

Find the `sectionBySlug` function in `editor.html`:
```javascript
  sectionBySlug: function(slug) {
    return App.state.content.sections.find(function(s) { return s.slug === slug; });
  },
```

Add directly after it:
```javascript
  issueById: function(id) {
    var issues = App.state.content.issues || [];
    return issues.find(function(i) { return i.id === id; });
  },
```

- [ ] **Step 3: Ensure content.issues is initialized on new article creation**

In the `newArticleBtn` click handler (around line 472), the new article object is pushed. Update it to include `issueId: null` and `photo: null`:

Find:
```javascript
      App.state.content.articles.push({
        id: newId, title: 'Untitled', author: '', section: App.state.content.sections[0].slug,
        issue: '', dek: '', body: '', ph: App.state.content.sections[0].ph, credit: '', published: false
      });
```

Replace with:
```javascript
      App.state.content.articles.push({
        id: newId, title: 'Untitled', author: '', section: App.state.content.sections[0].slug,
        issue: '', issueId: null, dek: '', body: '', ph: App.state.content.sections[0].ph,
        credit: '', photo: null, published: false
      });
```

- [ ] **Step 4: Verify**

Open `editor.html` in browser (with a valid GitHub token set). Confirm "Issues" appears in the sidebar nav between "Sections" and "System". Clicking it should throw a JS error (view not yet defined) — that's expected at this stage.

- [ ] **Step 5: Commit**

```bash
git add editor.html
git commit -m "feat: add Issues nav item and issueById helper to editor"
```

---

## Task 5: Editor — App.views.issues (list, create, edit, assign)

**Files:**
- Modify: `editor.html`

- [ ] **Step 1: Add CSS for Issues view**

Find the end of the `<style>` block in `editor.html` (before `</style>`). Add:

```css
/* ── Issues view ── */
.issue-row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #f0ede8;}
.issue-row:last-child{border-bottom:none;}
.issue-info{flex:1;}
.issue-title{font-size:14px;font-weight:600;}
.issue-meta{font-size:11px;color:#aaa;margin-top:2px;}
.issue-actions{display:flex;gap:6px;}
.assign-list{max-height:360px;overflow-y:auto;border:1px solid #e8e5e0;border-radius:6px;margin-top:8px;}
.assign-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid #f0ede8;cursor:pointer;}
.assign-item:last-child{border-bottom:none;}
.assign-item:hover{background:#fff8f4;}
.assign-item input[type=checkbox]{width:15px;height:15px;cursor:pointer;flex-shrink:0;}
.assign-item-info{flex:1;}
.assign-item-hed{font-size:13px;font-weight:500;}
.assign-item-meta{font-size:11px;color:#888;margin-top:2px;}
```

- [ ] **Step 2: Add `App.views.issues` before `App.init()`**

Find the line `App.init();` at the bottom of the script (it will be near the very end). Insert the following block directly before it:

```javascript
// ── Issues view ────────────────────────────────────────────────────────────
App.views.issues = {
  render: function() {
    document.getElementById('topbarTitle').textContent = 'Issues';
    document.getElementById('topbarActions').innerHTML =
      '<button class="btn btn-primary" id="newIssueBtn">+ New Issue</button>';

    App.views.issues.renderList();

    document.getElementById('newIssueBtn').addEventListener('click', function() {
      App.views.issues.openCreateModal();
    });
  },

  renderList: function() {
    var issues = (App.state.content.issues || []).slice().reverse();
    var articles = App.state.content.articles;

    if (!issues.length) {
      document.getElementById('contentArea').innerHTML =
        '<div class="card"><p style="color:#888;font-size:13px;">No issues yet. Click "+ New Issue" to create one.</p></div>';
      return;
    }

    var rowsHTML = issues.map(function(issue) {
      var count = articles.filter(function(a){ return a.issueId === issue.id; }).length;
      return '<div class="issue-row">' +
        '<div class="issue-info">' +
          '<div class="issue-title">' + App.esc(issue.title) + ' &mdash; ' + App.esc(issue.date) + '</div>' +
          '<div class="issue-meta">' + count + ' article' + (count === 1 ? '' : 's') + ' &nbsp;&middot;&nbsp; Cover: ' +
            App.esc((App.articleById(issue.coverArticle) || {title: 'None'}).title) +
          '</div>' +
        '</div>' +
        '<div class="issue-actions">' +
          '<button class="btn btn-secondary issue-print" data-id="' + App.esc(issue.id) + '" style="font-size:12px;">Print</button>' +
          '<button class="btn btn-secondary issue-edit" data-id="' + App.esc(issue.id) + '" style="font-size:12px;">Edit</button>' +
        '</div>' +
      '</div>';
    }).join('');

    document.getElementById('contentArea').innerHTML =
      '<div class="card" style="padding:0 20px;">' + rowsHTML + '</div>';

    document.querySelectorAll('.issue-print').forEach(function(btn) {
      btn.addEventListener('click', function() {
        window.open('print.html?issue=' + encodeURIComponent(btn.dataset.id), '_blank');
      });
    });

    document.querySelectorAll('.issue-edit').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var issue = App.issueById(btn.dataset.id);
        if (issue) App.views.issues.openEditModal(issue);
      });
    });
  },

  openCreateModal: function() {
    var articles = App.state.content.articles.filter(function(a){ return a.published; });
    var artOptions = articles.map(function(a) {
      return '<option value="' + App.esc(a.id) + '">' + App.esc(a.title) + '</option>';
    }).join('');

    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML =
      '<div class="modal">' +
        '<h3>New Issue</h3>' +
        '<div class="field"><label>Title (e.g. "Issue 7")</label><input type="text" id="mi-title" placeholder="Issue 7"></div>' +
        '<div class="field"><label>Date (e.g. "May 2026")</label><input type="text" id="mi-date" placeholder="May 2026"></div>' +
        '<div class="field"><label>Cover Article</label><select id="mi-cover"><option value="">— None —</option>' + artOptions + '</select></div>' +
        '<div class="modal-actions">' +
          '<button class="btn btn-secondary" id="mi-cancel">Cancel</button>' +
          '<button class="btn btn-primary" id="mi-save">Create Issue</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(backdrop);

    document.getElementById('mi-cancel').addEventListener('click', function() { backdrop.remove(); });
    document.getElementById('mi-save').addEventListener('click', function() {
      var title = document.getElementById('mi-title').value.trim();
      var date  = document.getElementById('mi-date').value.trim();
      var cover = document.getElementById('mi-cover').value;
      if (!title || !date) { alert('Title and date are required.'); return; }

      if (!App.state.content.issues) App.state.content.issues = [];
      var id = 'issue-' + title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      App.state.content.issues.push({ id: id, title: title, date: date, coverArticle: cover || null });

      var saveBtn = document.getElementById('mi-save');
      saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
      App.github.saveContent('Issues: create ' + title).then(function() {
        backdrop.remove();
        App.showSuccess('Issue created.');
        App.views.issues.renderList();
      }).catch(function(err) {
        saveBtn.disabled = false; saveBtn.textContent = 'Create Issue';
        App.handleApiError(err);
      });
    });
  },

  openEditModal: function(issue) {
    var articles = App.state.content.articles;
    var artOptions = App.state.content.articles
      .filter(function(a){ return a.published; })
      .map(function(a) {
        return '<option value="' + App.esc(a.id) + '"' + (issue.coverArticle === a.id ? ' selected' : '') + '>' + App.esc(a.title) + '</option>';
      }).join('');

    var assignItems = articles.map(function(a) {
      var checked = a.issueId === issue.id ? ' checked' : '';
      var secObj  = App.sectionBySlug(a.section) || {};
      return '<label class="assign-item">' +
        '<input type="checkbox" class="assign-check" data-id="' + App.esc(a.id) + '"' + checked + '>' +
        '<div class="assign-item-info">' +
          '<div class="assign-item-hed">' + App.esc(a.title) + '</div>' +
          '<div class="assign-item-meta">' + App.esc(a.author) + ' &nbsp;&middot;&nbsp; ' + App.esc(secObj.title || a.section) + '</div>' +
        '</div>' +
      '</label>';
    }).join('');

    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML =
      '<div class="modal" style="width:560px;max-height:85vh;display:flex;flex-direction:column;">' +
        '<h3>Edit Issue</h3>' +
        '<div style="overflow-y:auto;flex:1;">' +
          '<div class="field"><label>Title</label><input type="text" id="ei-title" value="' + App.esc(issue.title) + '"></div>' +
          '<div class="field"><label>Date</label><input type="text" id="ei-date" value="' + App.esc(issue.date) + '"></div>' +
          '<div class="field"><label>Cover Article</label><select id="ei-cover"><option value="">— None —</option>' + artOptions + '</select></div>' +
          '<div style="font-size:12px;font-weight:500;color:#555;margin-bottom:5px;">Articles in this Issue</div>' +
          '<div class="assign-list">' + assignItems + '</div>' +
        '</div>' +
        '<div class="modal-actions">' +
          '<button class="btn btn-secondary" id="ei-cancel">Cancel</button>' +
          '<button class="btn btn-primary" id="ei-save">Save Changes</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(backdrop);

    document.getElementById('ei-cancel').addEventListener('click', function() { backdrop.remove(); });
    document.getElementById('ei-save').addEventListener('click', function() {
      issue.title        = document.getElementById('ei-title').value.trim();
      issue.date         = document.getElementById('ei-date').value.trim();
      issue.coverArticle = document.getElementById('ei-cover').value || null;

      document.querySelectorAll('.assign-check').forEach(function(cb) {
        var a = App.articleById(cb.dataset.id);
        if (!a) return;
        if (cb.checked) {
          a.issueId = issue.id;
        } else if (a.issueId === issue.id) {
          a.issueId = null;
        }
      });

      var saveBtn = document.getElementById('ei-save');
      saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
      App.github.saveContent('Issues: update ' + issue.title).then(function() {
        backdrop.remove();
        App.showSuccess('Issue saved.');
        App.views.issues.renderList();
      }).catch(function(err) {
        saveBtn.disabled = false; saveBtn.textContent = 'Save Changes';
        App.handleApiError(err);
      });
    });
  }
};
```

- [ ] **Step 3: Verify**

Open `editor.html`. Click "Issues" in the sidebar:
- Issue list renders showing Issue 6 (19 articles) and Issue 5 (4 articles)
- "Print" button opens `print.html?issue=issue-6` in a new tab
- "Edit" button opens the edit modal with title/date/cover fields and article checklist
- "+ New Issue" button opens the create modal
- Creating a new issue saves to GitHub and appears in the list

- [ ] **Step 4: Commit**

```bash
git add editor.html
git commit -m "feat: add Issues view to editor — list, create, edit, and article assignment"
```

---

## Task 6: Editor — photo upload panel in article editor

**Files:**
- Modify: `editor.html`

- [ ] **Step 1: Add `App.github.uploadFile` method**

Find `App.github.saveContent` function and add `uploadFile` directly after it (before the closing `},` of `App.github`):

```javascript
    uploadFile: function(path, base64content, message) {
      var url = App.github.apiBase + '/repos/' + App.REPO_OWNER + '/' + App.REPO_NAME + '/contents/' + path;
      return fetch(url, { headers: App.github.headers() }).then(function(r) {
        return r.ok ? r.json() : null;
      }).then(function(existing) {
        var body = { message: message, content: base64content };
        if (existing && existing.sha) body.sha = existing.sha;
        return fetch(url, { method: 'PUT', headers: App.github.headers(), body: JSON.stringify(body) });
      }).then(function(r) {
        if (r.status === 401) throw new Error('AUTH_ERROR');
        if (!r.ok) throw new Error('HTTP_' + r.status);
        return r.json();
      });
    },
```

- [ ] **Step 2: Add photo panel CSS**

Append to the `<style>` block (before `</style>`):

```css
/* ── Photo upload panel ── */
.photo-panel{margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #f0ede8;}
.photo-preview{width:100%;height:90px;object-fit:cover;border-radius:5px;margin-bottom:6px;display:block;}
.photo-ph-strip{width:100%;height:60px;background:#e8e5e0;border-radius:5px;margin-bottom:6px;display:flex;align-items:center;justify-content:center;font-size:11px;color:#aaa;}
.photo-remove{font-size:11px;color:#b91c1c;cursor:pointer;background:none;border:none;padding:0;text-decoration:underline;}
```

- [ ] **Step 3: Add photo panel HTML to the article editor**

In `App.views.articleEditor.render()`, find this string in the HTML template:

```javascript
          '<div style="margin-bottom:14px;">' +
            '<div style="font-size:12px;font-weight:500;color:#555;margin-bottom:6px;">Photo Placeholder</div>' +
            '<div class="ph-grid" id="phGrid">' + swatchesHTML + '</div>' +
          '</div>' +
```

Replace it with:

```javascript
          '<div class="photo-panel">' +
            '<div style="font-size:12px;font-weight:500;color:#555;margin-bottom:6px;">Photo</div>' +
            '<div id="photoPanel">' +
              (a.photo
                ? '<img class="photo-preview" id="photoPreview" src="https://raw.githubusercontent.com/' + App.REPO_OWNER + '/' + App.REPO_NAME + '/main/' + App.esc(a.photo) + '" alt="">' +
                  '<div style="display:flex;align-items:center;justify-content:space-between;">' +
                    '<span style="font-size:11px;color:#888;">' + App.esc(a.photo) + '</span>' +
                    '<button class="photo-remove" id="photoRemove">Remove</button>' +
                  '</div>'
                : '<div class="photo-ph-strip">No photo uploaded</div>' +
                  '<input type="file" id="photoInput" accept="image/jpeg,image/png,image/gif,image/webp" style="display:none;">' +
                  '<button class="btn btn-secondary" id="photoUploadBtn" style="width:100%;font-size:12px;">Upload Photo</button>'
              ) +
            '</div>' +
          '</div>' +
          '<div style="margin-bottom:14px;">' +
            '<div style="font-size:12px;font-weight:500;color:#555;margin-bottom:6px;">Photo Placeholder</div>' +
            '<div class="ph-grid" id="phGrid">' + swatchesHTML + '</div>' +
          '</div>' +
```

- [ ] **Step 4: Wire up photo upload and remove event listeners**

In `App.views.articleEditor.render()`, after the `document.getElementById('phGrid').addEventListener` block, add:

```javascript
    var uploadBtn = document.getElementById('photoUploadBtn');
    var photoInput = document.getElementById('photoInput');
    var photoRemove = document.getElementById('photoRemove');

    if (uploadBtn && photoInput) {
      uploadBtn.addEventListener('click', function() { photoInput.click(); });
      photoInput.addEventListener('change', function() {
        var file = photoInput.files[0];
        if (!file) return;
        var ext = file.name.split('.').pop().toLowerCase();
        var path = 'photos/' + a.id + '.' + ext;

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading…';

        var reader = new FileReader();
        reader.onload = function(ev) {
          var dataUrl = ev.target.result;
          var base64  = dataUrl.split(',')[1];
          App.github.uploadFile(path, base64, 'Photo: upload for ' + a.id).then(function() {
            a.photo = path;
            return App.github.saveContent('Photo: set photo for ' + a.title);
          }).then(function() {
            App.showSuccess('Photo uploaded.');
            App.views.articleEditor.render();
          }).catch(function(err) {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload Photo';
            App.handleApiError(err);
          });
        };
        reader.readAsDataURL(file);
      });
    }

    if (photoRemove) {
      photoRemove.addEventListener('click', function() {
        if (!confirm('Remove photo from this article? (The file stays in the repo.)')) return;
        a.photo = null;
        App.github.saveContent('Photo: remove from ' + a.title).then(function() {
          App.showSuccess('Photo removed.');
          App.views.articleEditor.render();
        }).catch(App.handleApiError);
      });
    }
```

- [ ] **Step 5: Verify**

Open `editor.html` → edit any article. Confirm:
- "Photo" panel appears above "Photo Placeholder" swatches in the right sidebar
- "Upload Photo" button opens a file picker
- Selecting an image shows an uploading spinner-like disabled state, then re-renders with a thumbnail and the file path
- "Remove" link shows a confirm dialog, then removes the photo and shows "No photo uploaded" again
- Repeat for an article that already has a photo: thumbnail shows on load

- [ ] **Step 6: Commit**

```bash
git add editor.html
git commit -m "feat: add photo upload panel to article editor with GitHub API commit"
```

---

## Task 7: article.html — photo rendering and issueId-aware label

**Files:**
- Modify: `article.html`

- [ ] **Step 1: Update the lead image block to render real photos**

Find this block in the article render script:

```javascript
      // Lead image placeholder
      var leadImg = document.querySelector('.art-lead-img .img-ph');
      if (leadImg) {
        leadImg.className = 'img-ph ' + a.ph;
        var credit = leadImg.querySelector('.img-ph__credit');
        if (credit && a.credit) credit.textContent = a.credit;
      }
```

Replace with:

```javascript
      // Lead image
      var leadImgWrap = document.querySelector('.art-lead-img');
      if (leadImgWrap) {
        if (a.photo) {
          var rawBase = 'https://raw.githubusercontent.com/luryann/lincolnNewsletter/main/';
          leadImgWrap.innerHTML =
            '<img src="' + rawBase + esc(a.photo) + '" alt="" style="width:100%;aspect-ratio:16/9;object-fit:cover;">' +
            (a.credit ? '<p class="art-caption">' + esc(a.credit) + '</p>' : '');
        } else {
          var leadImg = leadImgWrap.querySelector('.img-ph');
          if (leadImg) {
            leadImg.className = 'img-ph ' + esc(a.ph);
            var credit = leadImg.querySelector('.img-ph__credit');
            if (credit && a.credit) credit.textContent = a.credit;
          }
        }
      }
```

- [ ] **Step 2: Update the issue label to use issueId lookup with fallback**

Find:
```javascript
      var issueEl = document.querySelector('.art-header__issue');
      if (issueEl) issueEl.textContent = a.issue;
```

Replace with:
```javascript
      var issueEl = document.querySelector('.art-header__issue');
      if (issueEl) {
        var issueLabel = a.issue || '';
        if (a.issueId) {
          var issues = data.issues || [];
          var issueObj = issues.find(function(i){ return i.id === a.issueId; });
          if (issueObj) issueLabel = issueObj.title + ' · ' + issueObj.date;
        }
        issueEl.textContent = issueLabel;
      }
```

- [ ] **Step 3: Verify**

Open `article.html?id=bracket` in browser:
- If bracket has a photo uploaded: real `<img>` tag renders where the placeholder was
- If no photo: `div.img-ph--sports` placeholder renders as before (no visible change)
- Issue label shows "Issue 6 · April 2026" (from `issueObj` lookup)

Test an article with no `issueId` but with a freeform `issue` string — confirm it still shows the freeform string as fallback.

- [ ] **Step 4: Commit**

```bash
git add article.html
git commit -m "feat: render real photos in article.html with img-ph fallback, issueId label"
```

---

## Done

All features are now implemented. Summary of what was built:

| Feature | Files |
|---|---|
| Issue management | `content.json`, `editor.html` (Issues view) |
| Photo upload | `editor.html` (photo panel + `App.github.uploadFile`) |
| Photo rendering | `article.html` |
| Print page | `print.html` |
| Print CSS | `styles.css` |
