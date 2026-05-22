"""Small local web UI for BookMem."""

from __future__ import annotations

from pathlib import Path
import html
import json
import subprocess
from typing import Any

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from . import __version__
from .config import get_settings
from .doctor import run_doctor
from .frontmatter import discover_book_files, read_markdown_with_frontmatter
from .taxonomy import load_taxonomy
from .search import search_books
from .router import route_query
from .duplicates import load_book_identities, find_duplicate_groups
from .review import review_file_path
from .topic_maps import map_topic
from .clean_check import assess_cleanliness, summarise_clean_check
from .index_versions import index_status


UI_VERSION = "0.1.0"

app = FastAPI(
    title="BookMem UI",
    version=UI_VERSION,
    description="Small local web interface for BookMem.",
)


NAV = [
    ("Dashboard", "/"),
    ("Books", "/books"),
    ("Classes", "/classes"),
    ("Search", "/search"),
    ("Topic Maps", "/topic-maps"),
    ("Review", "/review"),
    ("Duplicates", "/duplicates"),
    ("Clean Check", "/clean-check"),
    ("System", "/system"),
    ("Control", "/control"),
]


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def page(title: str, body: str) -> HTMLResponse:
    nav = "\n".join(
        f'<a href="{href}">{esc(label)}</a>'
        for label, href in NAV
    )
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{esc(title)} · BookMem</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
:root {{
  --bg: #111318;
  --panel: #1a1d24;
  --panel2: #222733;
  --text: #e8ebf0;
  --muted: #aab2c0;
  --accent: #8fb4ff;
  --good: #9fe29f;
  --warn: #ffd37a;
  --bad: #ff8f8f;
  --border: #303644;
}}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.45;
}}
header {{
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
  background: #0d0f14;
  position: sticky;
  top: 0;
  z-index: 10;
}}
header h1 {{
  margin: 0 0 .5rem 0;
  font-size: 1.25rem;
}}
nav {{
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
}}
nav a {{
  color: var(--accent);
  text-decoration: none;
  background: var(--panel);
  border: 1px solid var(--border);
  padding: .35rem .6rem;
  border-radius: .5rem;
  font-size: .9rem;
}}
main {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}}
.card, table, form, pre {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: .75rem;
}}
.card {{
  padding: 1rem;
}}
.metric {{
  font-size: 2rem;
  font-weight: 700;
}}
.muted {{
  color: var(--muted);
}}
table {{
  border-collapse: collapse;
  width: 100%;
  overflow: hidden;
  margin: 1rem 0;
}}
th, td {{
  padding: .55rem .7rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  text-align: left;
  font-size: .92rem;
}}
th {{
  background: var(--panel2);
}}
input, select, textarea {{
  width: 100%;
  box-sizing: border-box;
  background: #0f1117;
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: .4rem;
  padding: .5rem;
  margin: .25rem 0 .75rem 0;
}}
button {{
  background: var(--accent);
  color: #081021;
  border: 0;
  border-radius: .45rem;
  padding: .55rem .85rem;
  font-weight: 700;
  cursor: pointer;
}}
pre {{
  padding: 1rem;
  overflow-x: auto;
  white-space: pre-wrap;
}}
.ok {{ color: var(--good); }}
.warn {{ color: var(--warn); }}
.fail {{ color: var(--bad); }}
.pill {{
  display: inline-block;
  padding: .15rem .4rem;
  border-radius: 999px;
  background: var(--panel2);
  border: 1px solid var(--border);
  margin: .1rem;
  font-size: .78rem;
}}
a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <header>
<h1>BookMem UI <span class="muted">v{esc(__version__)}</span></h1>
<nav>{nav}</nav>
  </header>
  <main>
<h2>{esc(title)}</h2>
{body}
  </main>
</body>
</html>"""
    return HTMLResponse(content)


def topic_pills(topics: Any) -> str:
    return "".join(f'<span class="pill">{esc(t)}</span>' for t in (topics or [])[:6])


def status_class(status: str) -> str:
    status = (status or "").upper()
    if status == "OK":
        return "ok"
    if status == "WARN":
        return "warn"
    return "fail"


def book_rows(limit: int = 500) -> list[dict[str, Any]]:
    settings = get_settings()
    rows = []
    for path in discover_book_files(settings.books_dir)[:limit]:
        fm, _body, _had = read_markdown_with_frontmatter(path)
        classification = fm.get("classification") if isinstance(fm.get("classification"), dict) else {}
        rows.append({
            "path": str(path),
            "title": fm.get("title") or path.stem,
            "author": fm.get("author"),
            "class": classification.get("primary_class"),
            "class_label": classification.get("primary_label"),
            "topics": classification.get("topics", []),
            "book_id": fm.get("book_id"),
        })
    return rows


@app.get("/", response_class=HTMLResponse)
def dashboard():
    doctor = run_doctor(fix=False)
    idx = index_status()
    rows = book_rows()
    body = f"""
<div class="grid">
  <div class="card"><div class="metric">{len(rows)}</div><div class="muted">Books</div></div>
  <div class="card"><div class="metric">{doctor['counts'].get('indexed_chunks', 0)}</div><div class="muted">Indexed chunks</div></div>
  <div class="card"><div class="metric">{doctor['counts'].get('review_items', 0)}</div><div class="muted">Review items</div></div>
  <div class="card"><div class="metric">{doctor['counts'].get('unclassified', 0)}</div><div class="muted">Unclassified</div></div>
</div>

<div class="grid" style="margin-top:1rem">
  <div class="card">
<h3>System status</h3>
<p class="{status_class(doctor['status'])}"><strong>{esc(doctor['status'])}</strong></p>
<p>{esc('; '.join(doctor.get('reasons') or ['No issues reported.']))}</p>
  </div>
  <div class="card">
<h3>Index status</h3>
<p class="{'warn' if idx['stale'] else 'ok'}"><strong>{'STALE' if idx['stale'] else 'OK'}</strong></p>
<p>{esc('; '.join(idx.get('reasons') or ['Index fingerprint matches current code/config.']))}</p>
  </div>
</div>
"""
    return page("Dashboard", body)


@app.get("/books", response_class=HTMLResponse)
def books(q: str = "", class_code: str = ""):
    rows = book_rows(limit=2000)
    if q:
        qn = q.lower()
        rows = [r for r in rows if qn in f"{r['title']} {r.get('author','')} {' '.join(r.get('topics') or [])}".lower()]
    if class_code:
        rows = [r for r in rows if str(r.get("class") or "") == class_code]

    tr = "\n".join(
        f"<tr><td>{esc(r['title'])}</td><td>{esc(r['author'])}</td><td>{esc(r['class'])}</td><td>{esc(r['class_label'])}</td><td>{topic_pills(r.get('topics'))}</td><td>{esc(r['path'])}</td></tr>"
        for r in rows
    )
    body = f"""
<form method="get">
  <label>Search books</label>
  <input name="q" value="{esc(q)}" placeholder="Title, author, topic">
  <label>Class code</label>
  <input name="class_code" value="{esc(class_code)}" placeholder="158">
  <button>Filter</button>
</form>
<p class="muted">{len(rows)} book(s)</p>
<table><thead><tr><th>Title</th><th>Author</th><th>Class</th><th>Label</th><th>Topics</th><th>Path</th></tr></thead><tbody>{tr}</tbody></table>
"""
    return page("Books", body)


@app.get("/classes", response_class=HTMLResponse)
def classes():
    taxonomy = load_taxonomy()
    rows = book_rows(limit=5000)
    counts: dict[str, int] = {}
    for r in rows:
        code = str(r.get("class") or "unclassified")
        counts[code] = counts.get(code, 0) + 1

    classes = taxonomy.get("classes", {}) if isinstance(taxonomy, dict) else {}
    tr = ""
    for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        label = classes.get(code, {}).get("label") if isinstance(classes.get(code), dict) else ""
        tr += f"<tr><td><a href='/books?class_code={esc(code)}'>{esc(code)}</a></td><td>{esc(label)}</td><td>{count}</td></tr>"
    body = f"<table><thead><tr><th>Class</th><th>Label</th><th>Books</th></tr></thead><tbody>{tr}</tbody></table>"
    return page("Classes", body)


@app.get("/search", response_class=HTMLResponse)
def search(q: str = "", limit: int = 10):
    body = f"""
<form method="get">
  <label>Search corpus</label>
  <input name="q" value="{esc(q)}" placeholder="systems versus goals">
  <label>Limit</label>
  <input name="limit" type="number" value="{limit}">
  <button>Search</button>
</form>
"""
    if q:
        try:
            route = route_query(q)
            rows = search_books(q, limit=limit)
            body += f"<div class='card'><h3>Route</h3><pre>{esc(json.dumps(route.model_dump() if hasattr(route, 'model_dump') else getattr(route, '__dict__', str(route)), indent=2))}</pre></div>"
            tr = ""
            for row in rows:
                excerpt = (row.get("text") or "")[:500]
                tr += f"<tr><td>{esc(row.get('title'))}<br><span class='muted'>{esc(row.get('author'))}</span></td><td>{esc(row.get('heading_path'))}</td><td>{esc(row.get('citation'))}</td><td>{esc(excerpt)}</td></tr>"
            body += f"<table><thead><tr><th>Book</th><th>Location</th><th>Citation</th><th>Excerpt</th></tr></thead><tbody>{tr}</tbody></table>"
        except Exception as exc:
            body += f"<pre class='fail'>{esc(exc)}</pre>"
    return page("Search", body)


@app.get("/topic-maps", response_class=HTMLResponse)
def topic_maps(topic: str = "systems thinking"):
    body = f"""
<form method="get">
  <label>Topic</label>
  <input name="topic" value="{esc(topic)}">
  <button>Map topic</button>
</form>
"""
    if topic:
        try:
            result = map_topic(topic).to_dict()
            body += f"<pre>{esc(json.dumps(result, indent=2, ensure_ascii=False))}</pre>"
        except Exception as exc:
            body += f"<pre class='fail'>{esc(exc)}</pre>"
    return page("Topic Maps", body)


@app.get("/review", response_class=HTMLResponse)
def review():
    names = ["needs_metadata.yaml", "needs_classification.yaml", "low_confidence_matches.yaml", "possible_duplicates.yaml"]
    sections = []
    for name in names:
        path = review_file_path(name)
        if not path.exists():
            sections.append(f"<div class='card'><h3>{esc(name)}</h3><p class='muted'>No file found.</p></div>")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            text = str(exc)
        sections.append(f"<div class='card'><h3>{esc(name)}</h3><pre>{esc(text[:12000])}</pre></div>")
    return page("Review Queue", "\n".join(sections))


@app.get("/duplicates", response_class=HTMLResponse)
def duplicates(by: str = "isbn"):
    body = f"""
<form method="get">
  <label>Detection mode</label>
  <select name="by">
<option value="isbn" {'selected' if by == 'isbn' else ''}>ISBN</option>
<option value="title-author" {'selected' if by == 'title-author' else ''}>Title + Author</option>
<option value="content" {'selected' if by == 'content' else ''}>Content hash</option>
  </select>
  <button>Check</button>
</form>
"""
    try:
        identities = load_book_identities(get_settings().books_dir, include_raw=True)
        groups = find_duplicate_groups(identities, by=by)
        for group in groups:
            body += f"<div class='card'><h3>{esc(group.reason)}</h3><ul>"
            for book in group.books:
                body += f"<li>{esc(book.title)} — {esc(book.author)}<br><span class='muted'>{esc(book.path)}</span></li>"
            body += "</ul></div>"
        if not groups:
            body += "<p class='ok'>No duplicates found for this mode.</p>"
    except Exception as exc:
        body += f"<pre class='fail'>{esc(exc)}</pre>"
    return page("Duplicates", body)


@app.get("/clean-check", response_class=HTMLResponse)
def clean_check(path: str = ""):
    body = f"""
<form method="get">
  <label>Markdown file path</label>
  <input name="path" value="{esc(path)}" placeholder="data/books/.../Book.md">
  <button>Run clean check</button>
</form>
"""
    if path:
        try:
            report = assess_cleanliness(Path(path))
            summary = summarise_clean_check(report)
            body += f"<pre>{esc(json.dumps(summary, indent=2, ensure_ascii=False))}</pre>"
            if report.get("recommendations"):
                body += "<h3>Recommendations</h3><ul>"
                for rec in report["recommendations"]:
                    body += f"<li>{esc(rec)}</li>"
                body += "</ul>"
        except Exception as exc:
            body += f"<pre class='fail'>{esc(exc)}</pre>"
    return page("Clean-check Reports", body)


@app.get("/system", response_class=HTMLResponse)
def system():
    doctor = run_doctor(fix=False)
    idx = index_status()
    body = f"""
<h3>Doctor</h3>
<pre>{esc(json.dumps(doctor, indent=2, ensure_ascii=False))}</pre>
<h3>Index status</h3>
<pre>{esc(json.dumps(idx, indent=2, ensure_ascii=False))}</pre>
"""
    return page("System Status", body)


SAFE_COMMANDS = {
    "doctor": ["bookmem", "doctor"],
    "doctor-fix": ["bookmem", "doctor", "--fix"],
    "index-status": ["bookmem", "index-status"],
    "build-graph": ["bookmem", "build-graph"],
    "eval-retrieval": ["bookmem", "eval", "retrieval"],
}


@app.get("/control", response_class=HTMLResponse)
def control():
    options = "\n".join(f"<option value='{esc(k)}'>{esc(k)}: {' '.join(v)}</option>" for k, v in SAFE_COMMANDS.items())
    body = f"""
<form method="post" action="/control/run">
  <label>Safe command</label>
  <select name="command">{options}</select>
  <button>Run</button>
</form>
<p class="muted">Only allowlisted safe commands can be run from the UI.</p>
"""
    return page("Control Panel", body)


@app.post("/control/run", response_class=HTMLResponse)
def control_run(command: str = Form(...)):
    if command not in SAFE_COMMANDS:
        return page("Control Panel", f"<pre class='fail'>Unknown command: {esc(command)}</pre>")
    cmd = SAFE_COMMANDS[command]
    try:
        proc = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True, timeout=300)
        body = f"<p><a href='/control'>Back</a></p><h3>{esc(' '.join(cmd))}</h3><pre>{esc(proc.stdout)}\n{esc(proc.stderr)}</pre>"
    except Exception as exc:
        body = f"<p><a href='/control'>Back</a></p><pre class='fail'>{esc(exc)}</pre>"
    return page("Control Panel Result", body)


def run_ui(host: str = "127.0.0.1", port: int = 8787, reload: bool = False) -> None:
    import uvicorn

    uvicorn.run("bookmem.web_ui:app", host=host, port=port, reload=reload)
