from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .ingest import find_markdown_files, ingest_books
from .search import format_markdown_citation, format_source_location, get_table, read_around as search_read_around, read_chapter as search_read_chapter, read_chunk, read_section as search_read_section, search_books
from .taxonomy import all_routing_aliases, load_taxonomy, resolve_alias
from .loc import enrich_file_with_loc, lookup_loc_by_isbn
from .frontmatter import find_isbns_in_text
from .prepare import prepare_book as prepare_one_book
from .manifest import load_manifest, manifest_path, status_for_book
from .summaries import search_summaries as search_summary_index, summarise_book as summarise_one_book, summarise_books as summarise_many_books
from .router import route_query
from .review import apply_review_queue, load_review_queue, review_file_path, write_review_queues

app = typer.Typer(help="BookMem: agent-readable Markdown book corpus")
review_app = typer.Typer(help="Generate, inspect and apply review queues")
app.add_typer(review_app, name="review")
console = Console()


def _print_review_table(queue_name: str, issues: list[dict]) -> None:
    if not issues:
        console.print(f"[green]No {queue_name} review issues found[/green]")
        return

    table_out = Table(title=f"Review queue: {queue_name}")
    table_out.add_column("Issue")
    table_out.add_column("Severity")
    table_out.add_column("Class")
    table_out.add_column("Title")
    table_out.add_column("Path")

    for issue in issues:
        table_out.add_row(
            str(issue.get("issue", "")),
            str(issue.get("severity", "")),
            str(issue.get("primary_class") or issue.get("suggested_primary_class") or ""),
            str(issue.get("title", "")),
            str(issue.get("path", "")),
        )
    console.print(table_out)


@review_app.callback(invoke_without_command=True)
def review_command(
    ctx: typer.Context,
    books_dir: Path | None = typer.Option(None, "--books-dir", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
):
    """Generate and summarise review queue files."""
    if ctx.invoked_subcommand is not None:
        return
    summary = write_review_queues(books_dir=books_dir)
    console.print(
        Panel(
            f"Review directory: {summary.review_dir}\n\n"
            f"Needs metadata: {summary.metadata_count}\n"
            f"Needs classification: {summary.classification_count}\n"
            f"Low-confidence matches: {summary.low_confidence_count}",
            title="Review queues generated",
            expand=False,
        )
    )
    console.print(f"[dim]{review_file_path('metadata', summary.review_dir)}[/dim]")
    console.print(f"[dim]{review_file_path('classification', summary.review_dir)}[/dim]")
    console.print(f"[dim]{review_file_path('low_confidence', summary.review_dir)}[/dim]")


@review_app.command("classifications")
def review_classifications_command(
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate review files before displaying."),
    books_dir: Path | None = typer.Option(None, "--books-dir"),
):
    """Show books needing classification review."""
    if regenerate:
        write_review_queues(books_dir=books_dir)
    data = load_review_queue("classification")
    _print_review_table("needs_classification", data.get("issues", []))


@review_app.command("isbn-conflicts")
def review_isbn_conflicts_command(
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate review files before displaying."),
    books_dir: Path | None = typer.Option(None, "--books-dir"),
):
    """Show ISBN-related conflicts and duplicate candidates."""
    if regenerate:
        write_review_queues(books_dir=books_dir)
    metadata = load_review_queue("metadata").get("issues", [])
    classification = load_review_queue("classification").get("issues", [])
    relevant = [
        issue for issue in metadata + classification
        if str(issue.get("issue", "")).startswith("duplicate_")
        or issue.get("issue") == "multiple_isbns_found"
        or issue.get("issue") == "loc_class_conflict"
    ]
    _print_review_table("isbn_conflicts", relevant)


@review_app.command("metadata")
def review_metadata_command(
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate review files before displaying."),
    books_dir: Path | None = typer.Option(None, "--books-dir"),
):
    """Show books needing metadata review."""
    if regenerate:
        write_review_queues(books_dir=books_dir)
    data = load_review_queue("metadata")
    _print_review_table("needs_metadata", data.get("issues", []))


@review_app.command("low-confidence")
def review_low_confidence_command(
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate review files before displaying."),
    books_dir: Path | None = typer.Option(None, "--books-dir"),
):
    """Show low-confidence classification matches."""
    if regenerate:
        write_review_queues(books_dir=books_dir)
    data = load_review_queue("low_confidence")
    _print_review_table("low_confidence_matches", data.get("issues", []))


@review_app.command("apply")
def review_apply_command(
    regenerate_after: bool = typer.Option(True, "--regenerate-after/--no-regenerate-after", help="Regenerate review files after applying approved changes."),
):
    """Apply approved edits from review YAML files to Markdown frontmatter."""
    results = apply_review_queue()
    if not results:
        console.print("[yellow]No approved review entries to apply[/yellow]")
        return

    table_out = Table(title="Applied review changes")
    table_out.add_column("Status")
    table_out.add_column("Class")
    table_out.add_column("Path")
    for result in results:
        table_out.add_row(str(result.get("status", "")), str(result.get("primary_class", "")), str(result.get("path", "")))
    console.print(table_out)
    if regenerate_after:
        summary = write_review_queues()
        console.print(
            f"[green]Review queues regenerated:[/green] "
            f"metadata={summary.metadata_count}, "
            f"classification={summary.classification_count}, "
            f"low_confidence={summary.low_confidence_count}"
        )


@app.command("status")
def status_command(
    books_dir: Path | None = typer.Option(None, "--books-dir", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
):
    """Show manifest and changed-file status for canonical books."""
    from .config import get_settings

    settings = get_settings()
    books_root = books_dir or settings.books_dir
    files = find_markdown_files(books_root)
    data = load_manifest()

    console.print(f"[bold]Manifest:[/bold] {manifest_path()}")
    console.print(f"[bold]Tracked records:[/bold] {len(data.get('books', []))}")

    if not files:
        console.print(f"[yellow]No Markdown files found under {books_root}[/yellow]")
        return

    table_out = Table(title="BookMem status")
    table_out.add_column("State")
    table_out.add_column("Class/source")
    table_out.add_column("Title")
    table_out.add_column("Path")
    table_out.add_column("Chunks", justify="right")

    counts = {"up_to_date": 0, "needs_index": 0}
    for file_path in files:
        st = status_for_book(file_path)
        state = "needs index" if st.needs_index else "up to date"
        if st.needs_index:
            counts["needs_index"] += 1
        else:
            counts["up_to_date"] += 1
        reasons = []
        if not st.indexed:
            reasons.append("new")
        if st.content_changed:
            reasons.append("content")
        if st.frontmatter_changed:
            reasons.append("frontmatter")
        if reasons:
            state += f" ({', '.join(reasons)})"

        try:
            rel = str(file_path.relative_to(books_root))
        except Exception:
            rel = str(file_path)
        table_out.add_row(
            state,
            st.classification_source or "",
            st.title,
            rel,
            str(st.chunk_count or ""),
        )

    console.print(table_out)
    console.print(
        f"[green]{counts['up_to_date']}[/green] up to date; "
        f"[yellow]{counts['needs_index']}[/yellow] need indexing"
    )


@app.command()
def ingest(
    reset: bool = typer.Option(False, "--reset", help="Drop and rebuild the index"),
    changed_only: bool = typer.Option(False, "--changed-only", help="Only index new or changed canonical books"),
):
    """Ingest Markdown books into LanceDB."""
    ingest_books(reset=reset, changed_only=changed_only)


@app.command()
def search(
    query: str,
    limit: int = typer.Option(8, "--limit", "-n"),
    book: str | None = typer.Option(None, "--book"),
    class_code: list[str] = typer.Option(
        None,
        "--class",
        "--class-code",
        help="BMDC class code, repeatable",
    ),
    alias: list[str] = typer.Option(None, "--alias", help="Routing alias, repeatable"),
    mode: str = typer.Option("hybrid", "--mode", help="hybrid, vector, or fts"),
):
    """Search the book corpus."""
    results = search_books(
        query=query,
        limit=limit,
        book=book,
        class_code=class_code,
        alias=alias,
        mode=mode,
    )

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    for idx, row in enumerate(results, start=1):
        title = row.get("title", "Untitled")
        author = row.get("author") or "Unknown author"
        heading = row.get("heading_path") or ""
        chunk_id = row.get("chunk_id")
        source_location = format_source_location(row)
        citation = format_markdown_citation(row)
        primary_class = row.get("primary_class")
        primary_label = row.get("primary_class_label")
        text = row.get("text", "")

        excerpt = text[:900].strip()
        if len(text) > 900:
            excerpt += "..."

        console.print(
            Panel(
                f"[bold]{title}[/bold]\n"
                f"{author}\n"
                f"[dim]{primary_class} — {primary_label}[/dim]\n"
                f"[dim]{heading}[/dim]\n"
                f"[dim]{source_location}[/dim]\n\n"
                f"{excerpt}\n\n"
                f"[cyan]chunk_id:[/cyan] {chunk_id}\n"
                f"[cyan]citation:[/cyan] {citation}",
                title=f"Result {idx}",
                expand=False,
            )
        )


def _print_read_rows(chunks: list[dict], empty_message: str = "No matching chunks found") -> None:
    if not chunks:
        console.print(f"[yellow]{empty_message}[/yellow]")
        return

    for row in chunks:
        title = row.get("title", "Untitled")
        author = row.get("author") or "Unknown author"
        heading = row.get("heading_path") or ""
        chapter_title = row.get("chapter_title") or ""
        section_title = row.get("section_title") or ""
        chunk_index = row.get("chunk_index")
        start_line = row.get("start_line")
        end_line = row.get("end_line")
        citation = format_markdown_citation(row)
        previous_chunk_id = row.get("previous_chunk_id") or ""
        next_chunk_id = row.get("next_chunk_id") or ""
        text = row.get("text", "")

        console.print(
            Panel(
                f"[bold]{title}[/bold]\n"
                f"{author}\n"
                f"[dim]{heading}[/dim]\n"
                f"[dim]chapter: {chapter_title} | section: {section_title}[/dim]\n"
                f"[dim]chunk_index: {chunk_index} | lines: {start_line or '?'}-{end_line or '?'}[/dim]\n"
                f"[dim]previous: {previous_chunk_id or '-'} | next: {next_chunk_id or '-'}[/dim]\n"
                f"[cyan]citation:[/cyan] {citation}\n\n"
                f"{text}",
                title=row.get("chunk_id"),
                expand=False,
            )
        )


@app.command("read")
def read(
    chunk_id: str,
    context: int = typer.Option(1, "--context", "-c"),
):
    """Read a chunk plus equal neighbouring context on both sides."""
    chunks = read_chunk(chunk_id=chunk_id, context=context)
    _print_read_rows(chunks, empty_message="Chunk not found")


@app.command("read-around")
def read_around(
    chunk_id: str,
    before: int = typer.Option(2, "--before", help="Number of chunks before the target chunk"),
    after: int = typer.Option(3, "--after", help="Number of chunks after the target chunk"),
):
    """Read a chunk with separate before/after context controls."""
    chunks = search_read_around(chunk_id=chunk_id, before=before, after=after)
    _print_read_rows(chunks, empty_message="Chunk not found")


@app.command("read-section")
def read_section(
    chunk_id: str = typer.Option(..., "--chunk-id", help="Chunk ID inside the section to read"),
):
    """Read the complete section containing a chunk."""
    chunks = search_read_section(chunk_id=chunk_id)
    _print_read_rows(chunks, empty_message="Section not found")


@app.command("read-chapter")
def read_chapter(
    book: str = typer.Option(..., "--book", help="Book ID or exact title"),
    chapter: str = typer.Option(..., "--chapter", help="Chapter title, e.g. 'Chapter 6'"),
):
    """Read all indexed chunks for a chapter in a book."""
    chunks = search_read_chapter(book=book, chapter=chapter)
    _print_read_rows(chunks, empty_message="Chapter not found")


@app.command("list-books")
def list_books(
    class_code: str | None = typer.Option(None, "--class", "--class-code"),
    alias: str | None = typer.Option(None, "--alias"),
):
    """List indexed books."""
    table = get_table()
    rows = table.to_pandas()

    if rows.empty:
        console.print("[yellow]No indexed books[/yellow]")
        return

    if class_code:
        rows = rows[
            (rows["primary_class"] == class_code)
            | (rows["secondary_class_text"].str.contains(class_code, na=False))
        ]

    if alias:
        resolved = resolve_alias(alias)
        codes = set(resolved.get("primary_class", []) + resolved.get("secondary_class", []))
        rows = rows[
            rows["primary_class"].isin(codes)
            | rows["secondary_class_text"].apply(lambda value: any(code in str(value) for code in codes))
        ]

    grouped = (
        rows.groupby(["book_id", "title", "author", "primary_class", "primary_class_label"], dropna=False)
        .size()
        .reset_index(name="chunks")
        .sort_values(["primary_class", "title"])
    )

    table_out = Table(title="Indexed Books")
    table_out.add_column("Class")
    table_out.add_column("Class label")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Chunks", justify="right")

    for _, row in grouped.iterrows():
        table_out.add_row(
            str(row["primary_class"]),
            str(row["primary_class_label"]),
            str(row["title"]),
            str(row["author"] or ""),
            str(row["chunks"]),
        )

    console.print(table_out)


@app.command("list-taxonomy")
def list_taxonomy():
    """List the configured BMDC classes."""
    taxonomy = load_taxonomy()
    table_out = Table(title="BookMem Decimal Classification")
    table_out.add_column("Code")
    table_out.add_column("Label")
    table_out.add_column("Aliases")

    for code, data in sorted(taxonomy.get("classes", {}).items()):
        table_out.add_row(code, data.get("label", ""), ", ".join(data.get("aliases", [])))

    console.print(table_out)


@app.command("list-aliases")
def list_aliases():
    """List routing aliases."""
    aliases = all_routing_aliases()
    table_out = Table(title="Routing Aliases")
    table_out.add_column("Alias")
    for item in aliases:
        table_out.add_row(item)
    console.print(table_out)




@app.command("scan-isbns")
def scan_isbns(
    path: Path,
):
    """Scan a Markdown file for ISBNs without relying on filename formatting."""
    text = path.read_text(encoding="utf-8", errors="replace")
    isbns = find_isbns_in_text(text)

    if not isbns:
        console.print(f"[yellow]{path}: no ISBNs found[/yellow]")
        raise typer.Exit(code=1)

    table_out = Table(title=f"ISBNs found in {path.name}")
    table_out.add_column("ISBN")
    table_out.add_column("Type")
    for isbn in isbns:
        table_out.add_row(isbn, f"ISBN-{len(isbn)}")
    console.print(table_out)


@app.command("loc-lookup")
def loc_lookup(
    isbn: str,
    timeout: int = typer.Option(20, "--timeout"),
):
    """Look up a single ISBN using the Library of Congress SRU catalogue interface."""
    result = lookup_loc_by_isbn(isbn, timeout=timeout)
    if result.error:
        console.print(f"[red]{result.error}[/red]")
        raise typer.Exit(code=1)
    if not result.found:
        console.print("[yellow]No Library of Congress record found[/yellow]")
        raise typer.Exit(code=1)

    table_out = Table(title="Library of Congress ISBN lookup")
    table_out.add_column("Field")
    table_out.add_column("Value")
    table_out.add_row("ISBN", result.isbn or "")
    table_out.add_row("Title", result.title or "")
    table_out.add_row("Author", result.author or "")
    table_out.add_row("Class", result.class_number or "")
    table_out.add_row("Raw classification", result.raw_classification_number or "")
    table_out.add_row("Source field", result.class_source_field or "")
    table_out.add_row("LCCN / record id", result.lccn or "")
    table_out.add_row("Records", str(result.record_count))
    console.print(table_out)


@app.command("enrich-loc")
def enrich_loc(
    path: Path,
    write: bool = typer.Option(False, "--write", help="Write LoC enrichment into frontmatter"),
    overwrite_classification: bool = typer.Option(
        False,
        "--overwrite-classification",
        help="Replace existing primary classification with the LoC class number",
    ),
    timeout: int = typer.Option(20, "--timeout"),
):
    """Enrich one Markdown book's frontmatter from Library of Congress by ISBN."""
    result, frontmatter = enrich_file_with_loc(
        path,
        write=write,
        overwrite_classification=overwrite_classification,
        timeout=timeout,
    )

    if result.error:
        console.print(f"[yellow]{path}: {result.error}[/yellow]")
        raise typer.Exit(code=1)
    if not result.found:
        console.print(f"[yellow]{path}: no Library of Congress record found[/yellow]")
        raise typer.Exit(code=1)

    classification = frontmatter.get("classification") or {}
    console.print(
        Panel(
            f"[bold]{frontmatter.get('title', path.stem)}[/bold]\n"
            f"{frontmatter.get('author') or 'Unknown author'}\n\n"
            f"LoC title: {result.title or ''}\n"
            f"LoC author: {result.author or ''}\n"
            f"LoC raw class: {result.raw_classification_number or ''}\n"
            f"BookMem class: {classification.get('primary_class', '')} — {classification.get('primary_label', '')}\n\n"
            f"Written: {'yes' if write else 'no'}",
            title="LoC enrichment",
            expand=False,
        )
    )


@app.command("enrich-loc-books")
def enrich_loc_books(
    books_dir: Path,
    write: bool = typer.Option(False, "--write", help="Write LoC enrichment into frontmatter"),
    overwrite_classification: bool = typer.Option(False, "--overwrite-classification"),
    timeout: int = typer.Option(20, "--timeout"),
):
    """Enrich Markdown books under a directory from Library of Congress by ISBN."""
    files = sorted(books_dir.glob("**/*.md"))
    if not files:
        console.print(f"[yellow]No Markdown files found under {books_dir}[/yellow]")
        return

    table_out = Table(title="Library of Congress bulk enrichment")
    table_out.add_column("File")
    table_out.add_column("Status")
    table_out.add_column("Class")
    table_out.add_column("Raw")

    ok = 0
    for file_path in files:
        result, frontmatter = enrich_file_with_loc(
            file_path,
            write=write,
            overwrite_classification=overwrite_classification,
            timeout=timeout,
        )
        classification = frontmatter.get("classification") or {}
        if result.found:
            ok += 1
            status = "found"
        else:
            status = result.error or "not found"
        table_out.add_row(
            str(file_path.relative_to(books_dir)),
            status,
            str(classification.get("primary_class", "")),
            result.raw_classification_number or "",
        )

    console.print(table_out)
    console.print(f"[green]{ok}[/green] / {len(files)} files enriched")


@app.command("prepare-book")
def prepare_book_command(
    source_path: Path,
    output_root: Path | None = typer.Option(None, "--output-root", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
    no_clean: bool = typer.Option(False, "--no-clean", help="Treat the source as already cleaned Markdown."),
    enrich_loc: bool = typer.Option(False, "--enrich-loc", help="Use Library of Congress ISBN lookup when possible."),
    overwrite_frontmatter: bool = typer.Option(False, "--overwrite-frontmatter", help="Regenerate existing frontmatter."),
    overwrite_file: bool = typer.Option(False, "--overwrite-file", help="Overwrite the final canonical file if it exists."),
    delete_source: bool = typer.Option(False, "--delete-source", help="Delete the raw source after successful preparation."),
    timeout: int = typer.Option(20, "--timeout"),
    changed_only: bool = typer.Option(False, "--changed-only", help="Skip if the raw source has already been prepared unchanged."),
):
    """Clean, frontmatter, classify, rename and place one Markdown book."""
    result = prepare_one_book(
        source_path=source_path,
        output_root=output_root,
        clean=not no_clean,
        enrich_loc=enrich_loc,
        overwrite_frontmatter=overwrite_frontmatter,
        overwrite_file=overwrite_file,
        delete_source=delete_source,
        timeout=timeout,
        changed_only=changed_only,
    )

    if result.skipped:
        console.print(f"[green]{source_path}: unchanged, skipped[/green]")
        return

    console.print(
        Panel(
            f"[bold]{result.title}[/bold]\n"
            f"{result.author or 'Unknown author'}\n"
            f"ISBN: {result.isbn or ''}\n\n"
            f"Class: {result.primary_class} — {result.primary_label}\n"
            f"Classification source: {result.classification_source}\n\n"
            f"Output: {result.output_path}\n"
            f"Cleaned: {'yes' if result.cleaned else 'no'}\n"
            f"Moved/renamed: {'yes' if result.moved_file else 'no'}",
            title="Book prepared",
            expand=False,
        )
    )


@app.command("prepare-books")
def prepare_books_command(
    source_dir: Path,
    output_root: Path | None = typer.Option(None, "--output-root", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
    no_clean: bool = typer.Option(False, "--no-clean", help="Treat sources as already cleaned Markdown."),
    enrich_loc: bool = typer.Option(False, "--enrich-loc", help="Use Library of Congress ISBN lookup when possible."),
    overwrite_frontmatter: bool = typer.Option(False, "--overwrite-frontmatter"),
    overwrite_file: bool = typer.Option(False, "--overwrite-file"),
    delete_source: bool = typer.Option(False, "--delete-source"),
    timeout: int = typer.Option(20, "--timeout"),
    changed_only: bool = typer.Option(False, "--changed-only", help="Skip raw sources already prepared unchanged."),
):
    """Bulk prepare Markdown books into the canonical class folder structure."""
    files = sorted(source_dir.glob("**/*.md"))
    if not files:
        console.print(f"[yellow]No Markdown files found under {source_dir}[/yellow]")
        return

    table_out = Table(title="Prepared books")
    table_out.add_column("Source")
    table_out.add_column("Class")
    table_out.add_column("Title")
    table_out.add_column("Output")

    for file_path in files:
        try:
            result = prepare_one_book(
                source_path=file_path,
                output_root=output_root,
                clean=not no_clean,
                enrich_loc=enrich_loc,
                overwrite_frontmatter=overwrite_frontmatter,
                overwrite_file=overwrite_file,
                delete_source=delete_source,
                timeout=timeout,
                changed_only=changed_only,
            )
            if result.skipped:
                class_text = "SKIP"
                title = "unchanged"
                output = ""
            else:
                class_text = result.primary_class
                title = result.title
                output = result.output_path
        except Exception as exc:
            class_text = "ERROR"
            title = str(exc)
            output = ""
        table_out.add_row(str(file_path.relative_to(source_dir)), class_text, title, output)

    console.print(table_out)



@app.command("route")
def route_command(
    query: str,
    max_aliases: int = typer.Option(3, "--max-aliases", help="Maximum routing aliases to return."),
    compact: bool = typer.Option(False, "--compact", help="Emit compact JSON."),
):
    """Route a natural-language query to likely BMDC aliases and class codes."""
    result = route_query(query, max_aliases=max_aliases)
    console.print(result.to_json(indent=None if compact else 2))


@app.command("ask-search")
def ask_search_command(
    query: str,
    limit: int = typer.Option(5, "--limit", "-n", help="Number of chunk results to show."),
    context: int = typer.Option(1, "--context", "-c", help="Neighbouring chunks to read around each result."),
    mode: str = typer.Option("hybrid", "--mode", help="hybrid, vector, or fts"),
    summaries_first: bool = typer.Option(False, "--summaries-first", help="Show matching summary maps before chunk results."),
    fallback: bool = typer.Option(True, "--fallback/--no-fallback", help="Fall back to a broad search if routed search finds nothing."),
):
    """Route a question, search the selected classes, and read surrounding context."""
    route = route_query(query)
    console.print(
        Panel(
            f"Aliases: {', '.join(route.aliases) or 'none'}\n"
            f"Classes: {', '.join(route.class_codes) or 'none'}\n"
            f"Confidence: {route.confidence:.2f}\n"
            f"Matched terms: {', '.join(route.matched_terms) or 'none'}\n\n"
            f"{route.reason}",
            title="Route",
            expand=False,
        )
    )

    if summaries_first:
        summary_results = search_summary_index(query=query, limit=min(limit, 5), include_chapters=True)
        if summary_results:
            console.print("[bold]Summary matches[/bold]")
            for idx, result in enumerate(summary_results, start=1):
                label = result.title
                if result.chapter_title:
                    label += f" — {result.chapter_title}"
                excerpt = result.text[:500].strip()
                if len(result.text) > 500:
                    excerpt += "..."
                console.print(
                    Panel(
                        f"[bold]{label}[/bold]\n"
                        f"{result.author or 'Unknown author'}\n"
                        f"[dim]{result.level} summary · score {result.score:.3f}[/dim]\n"
                        f"[dim]{result.summary_path}[/dim]\n\n"
                        f"{excerpt}",
                        title=f"Summary {idx}",
                        expand=False,
                    )
                )

    results = search_books(
        query=query,
        limit=limit,
        class_code=route.class_codes or None,
        alias=route.aliases or None,
        mode=mode,
    )

    if not results and fallback and (route.aliases or route.class_codes):
        console.print("[yellow]No routed chunk results found; falling back to broad corpus search.[/yellow]")
        results = search_books(query=query, limit=limit, mode=mode)

    if not results:
        console.print("[yellow]No chunk results found.[/yellow]")
        return

    for idx, row in enumerate(results, start=1):
        chunk_id = row.get("chunk_id")
        title = row.get("title", "Untitled")
        author = row.get("author") or "Unknown author"
        primary_class = row.get("primary_class") or ""
        primary_label = row.get("primary_class_label") or ""
        heading = row.get("heading_path") or ""
        source_location = format_source_location(row)
        citation = format_markdown_citation(row)

        if context > 0 and chunk_id:
            chunks = read_chunk(str(chunk_id), context=context)
            text = "\n\n".join(str(chunk.get("text", "")).strip() for chunk in chunks if chunk.get("text"))
        else:
            text = str(row.get("text", "")).strip()

        excerpt = text[:1800].strip()
        if len(text) > 1800:
            excerpt += "..."

        console.print(
            Panel(
                f"[bold]{title}[/bold]\n"
                f"{author}\n"
                f"[dim]{primary_class} — {primary_label}[/dim]\n"
                f"[dim]{heading}[/dim]\n"
                f"[dim]{source_location}[/dim]\n\n"
                f"{excerpt}\n\n"
                f"[cyan]chunk_id:[/cyan] {chunk_id}\n"
                f"[cyan]citation:[/cyan] {citation}",
                title=f"Routed result {idx}",
                expand=False,
            )
        )

@app.command("summarise-book")
def summarise_book_command(
    path: Path,
    write: bool = typer.Option(True, "--write/--dry-run", help="Write derived summary files. Use --dry-run to preview paths only."),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="Overwrite existing summary files."),
):
    """Generate book-level and chapter-level YAML summaries for one canonical Markdown book."""
    result = summarise_one_book(path, write=write, overwrite=overwrite)
    console.print(
        Panel(
            f"[bold]{result.title}[/bold]\n"
            f"{result.author or 'Unknown author'}\n"
            f"Book ID: {result.book_id}\n\n"
            f"Chapters: {result.chapter_count}\n"
            f"Book summary: {result.book_summary_path}\n"
            f"Chapter summaries: {result.chapter_summary_path}\n"
            f"Written: {'yes' if result.written else 'no'}",
            title="Summary generated",
            expand=False,
        )
    )


@app.command("summarise-books")
def summarise_books_command(
    books_dir: Path,
    write: bool = typer.Option(True, "--write/--dry-run", help="Write derived summary files. Use --dry-run to preview only."),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="Overwrite existing summary files."),
):
    """Generate book-level and chapter-level summaries for all Markdown books under a directory."""
    files = sorted(books_dir.glob("**/*.md"))
    if not files:
        console.print(f"[yellow]No Markdown files found under {books_dir}[/yellow]")
        return

    table_out = Table(title="Book summaries")
    table_out.add_column("Book")
    table_out.add_column("Author")
    table_out.add_column("Chapters", justify="right")
    table_out.add_column("Summary path")

    results = summarise_many_books(books_dir, write=write, overwrite=overwrite)
    for result in results:
        table_out.add_row(
            result.title,
            result.author or "",
            str(result.chapter_count),
            str(result.book_summary_path),
        )

    console.print(table_out)
    console.print(f"[green]{len(results)}[/green] books summarised")


@app.command("search-summaries")
def search_summaries_command(
    query: str,
    limit: int = typer.Option(8, "--limit", "-n"),
    books_only: bool = typer.Option(False, "--books-only", help="Search only book-level summaries, not chapter summaries."),
):
    """Search derived book/chapter summaries before diving into full chunks."""
    results = search_summary_index(query=query, limit=limit, include_chapters=not books_only)
    if not results:
        console.print("[yellow]No summaries found. Run bookmem summarise-books data/books first.[/yellow]")
        return

    for idx, result in enumerate(results, start=1):
        label = result.title
        if result.chapter_title:
            label += f" — {result.chapter_title}"
        excerpt = result.text[:750].strip()
        if len(result.text) > 750:
            excerpt += "..."
        console.print(
            Panel(
                f"[bold]{label}[/bold]\n"
                f"{result.author or 'Unknown author'}\n"
                f"[dim]{result.level} summary · score {result.score:.3f}[/dim]\n"
                f"[dim]{result.summary_path}[/dim]\n\n"
                f"{excerpt}",
                title=f"Summary result {idx}",
                expand=False,
            )
        )


if __name__ == "__main__":
    app()
