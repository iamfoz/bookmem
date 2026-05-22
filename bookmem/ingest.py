from __future__ import annotations

from pathlib import Path

import lancedb
import pandas as pd
from rich.console import Console

from .chunking import chunk_markdown_file
from .config import get_settings
from .embeddings import embed_texts
from .manifest import mark_indexed, status_for_book
from .index_versions import update_manifest_index_metadata
from .book_files import discover_book_markdown_files

console = Console()


def find_markdown_files(books_dir: Path) -> list[Path]:
    return discover_book_markdown_files(books_dir)


def _delete_existing_rows(table, source_path: Path) -> None:
    source = str(source_path)
    safe_source = source.replace("'", "''")
    try:
        table.delete(f"source_path = '{safe_source}'")
    except Exception:
        # Some LanceDB versions are fussy about delete support depending on table
        # state. In the worst case, a full --reset rebuild remains available.
        pass


def ingest_books(reset: bool = False, changed_only: bool = False) -> None:
    settings = get_settings()
    settings.db_dir.mkdir(parents=True, exist_ok=True)

    md_files = find_markdown_files(settings.books_dir)
    if not md_files:
        console.print(f"[yellow]No Markdown files found in {settings.books_dir}[/yellow]")
        return

    if changed_only and not reset:
        statuses = [status_for_book(path) for path in md_files]
        md_files = [status.path for status in statuses if status.needs_index]
        skipped = len(statuses) - len(md_files)
        console.print(f"[cyan]{len(md_files)} changed/new files to index; {skipped} unchanged files skipped[/cyan]")
        if not md_files:
            console.print("[green]Index is already up to date[/green]")
            return
    else:
        console.print(f"[cyan]Found {len(md_files)} Markdown files[/cyan]")

    db = lancedb.connect(str(settings.db_dir))

    if reset:
        try:
            db.drop_table(settings.table_name)
            console.print(f"[yellow]Dropped existing table: {settings.table_name}[/yellow]")
        except Exception:
            pass

    table = None
    if settings.table_name in db.table_names():
        table = db.open_table(settings.table_name)

    all_rows: list[dict] = []
    chunk_counts: dict[Path, tuple[str, int, str]] = {}

    for path in md_files:
        chunks = chunk_markdown_file(
            path,
            books_dir=settings.books_dir,
            target_chars=settings.chunk_target_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        console.print(f"[green]{path}[/green]: {len(chunks)} chunks")
        if not chunks:
            continue
        first = chunks[0]
        # All chunks from one file carry the same book_id/classification source.
        classification_source = ""
        try:
            from .manifest import classification_source_from_frontmatter
            classification_source = classification_source_from_frontmatter(path)
        except Exception:
            pass
        chunk_counts[path] = (first.book_id, len(chunks), classification_source)
        all_rows.extend(chunk.__dict__.copy() for chunk in chunks)

    if not all_rows:
        console.print("[yellow]No chunks generated[/yellow]")
        return

    console.print(f"[cyan]Embedding {len(all_rows)} chunks[/cyan]")
    vectors = embed_texts([row["text"] for row in all_rows])
    for row, vector in zip(all_rows, vectors):
        row["vector"] = vector

    df = pd.DataFrame(all_rows)

    if table is None:
        table = db.create_table(settings.table_name, data=df)
        console.print(f"[green]Created table: {settings.table_name}[/green]")
    else:
        # Adding to an existing table: drop any prior rows for the files being
        # ingested first, so re-running `ingest` is idempotent and never
        # accumulates duplicate chunks.
        for path in md_files:
            _delete_existing_rows(table, path)
        table.add(df)
        console.print(f"[green]Added rows to table: {settings.table_name}[/green]")

    try:
        table.create_fts_index("text", replace=True)
        console.print("[green]Created full-text index on text column[/green]")
    except Exception as exc:
        console.print(f"[yellow]Could not create FTS index: {exc}[/yellow]")

    for path, (book_id, chunk_count, classification_source) in chunk_counts.items():
        mark_indexed(
            canonical_path=path,
            book_id=book_id,
            chunk_count=chunk_count,
            classification_source=classification_source,
        )

    update_manifest_index_metadata(chunk_count=len(all_rows), book_count=len(chunk_counts))

    console.print("[bold green]Ingest complete[/bold green]")
