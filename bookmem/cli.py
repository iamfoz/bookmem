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
from .summary_providers import load_summary_providers, validate_summary_providers, summarise_book_with_provider, summarise_books_with_provider
from .router import route_query
from .review import apply_review_queue, load_review_queue, review_file_path, write_review_queues
from .duplicates import find_duplicate_groups, load_book_identities, write_duplicate_review
from .stats import author_counts, class_counts, collection_totals, load_book_stats, stats_payload, topic_counts
from .topic_maps import map_topic as build_topic_map, write_topic_map
from .agent_exports import SUPPORTED_AGENT_EXPORT_FORMATS, export_agent_corpus
from .notes import generate_note, generate_notes_for_directory, load_note_templates
from .clean_check import assess_cleanliness, summarise_clean_check
from .clean import clean_markdown_file, load_cleaning_profiles, validate_cleaning_profiles, report_as_dict
from .doctor import run_doctor
from .backup import create_backup, restore_backup, inspect_backup, result_as_dict
from .importers import import_epub, import_html, import_pdf, import_calibre, result_as_dict as import_result_as_dict
from .calibre import scan_calibre_library, find_calibre_book, enrich_markdown_from_calibre, import_calibre_metadata_stubs, calibre_book_as_dict
from .grimmory import write_grimmory_sidecar, export_grimmory_library, result_as_dict as grimmory_result_as_dict
from .metadata_enrichment import enrich_with_openlibrary, enrich_with_google_books, enrich_metadata
from .editions import list_editions, group_editions, edition_records_as_dict, ensure_work_edition_frontmatter
from .book_graph import build_book_graph, related_books
from .answer_pack import build_answer_pack
from .prompt_packs import list_prompts, show_prompt, prompt_assets_as_dict
from .concepts import extract_concepts_from_book, extract_concepts_from_books, search_concepts, list_concepts, rebuild_concept_index
from .index_versions import index_status, update_manifest_index_metadata
from .embedding_management import current_embedding_info, embedding_profiles, profiles_as_dict, validate_embedding_models, benchmark_embeddings, reindex_with_embedding_model
from .evaluation import evaluate_retrieval, load_eval_queries, eval_queries_as_dict
from .web_ui import run_ui
from .tui import run_tui
from .setup_wizard import load_setup_presets, presets_as_dict, setup_steps_for_preset, setup_status, run_setup_preset
from .migrations import migration_status, apply_migrations, create_migration
from .clean_derived import clean_derived, clean_result_as_dict
from .human_review import machine_drafts, drafts_as_dict, approve_summary, approve_concepts, reject_concept, mark_human_reviewed, set_summary_status, set_concepts_status
from .audit import tail_audit, search_audit, export_audit, append_audit_record
from .restore_points import create_restore_point, list_restore_points, show_restore_point, rollback_restore_point, restore_point_from_audit_id, restore_point_as_dict
from .permissions import check_permission, list_agent_permissions, list_agents, validate_permissions, decision_as_dict
from .workspaces import list_workspaces_as_dict, workspace_search, workspace_answer_pack, validate_workspaces
from .saved_queries import save_query, list_saved_queries, run_saved_query, generate_brief
from .reading_lists import generate_reading_list
from .citation_exports import (
    export_references,
    format_reference,
    load_citation_styles,
    load_reference_export_formats,
    reference_from_frontmatter,
    references_from_directory,
    supported_export_formats,
    supported_styles,
    validate_citation_styles,
    validate_reference_export_formats,
)

app = typer.Typer(help="BookMem: agent-readable Markdown book corpus")
review_app = typer.Typer(help="Generate, inspect and apply review queues")
notes_app = typer.Typer(help="Generate Obsidian-friendly book notes")
import_app = typer.Typer(help="Import source book formats into raw Markdown")
calibre_app = typer.Typer(help="Calibre metadata integration")
grimmory_app = typer.Typer(help="Grimmory sidecar/export integration")
prompts_app = typer.Typer(help="List and show reusable prompt pack assets")
concepts_app = typer.Typer(help="Extract, list and search reusable book concepts")
embeddings_app = typer.Typer(help="Manage embedding model profiles and reindexing")
eval_app = typer.Typer(help="Run retrieval benchmark/evaluation sets")
setup_app = typer.Typer(help="First-run setup wizard and presets")
migrations_app = typer.Typer(help="Explicit schema/data migrations")
audit_app = typer.Typer(help="Inspect and export the durable audit log")
restore_points_app = typer.Typer(help="Create, inspect and roll back restore points")
permissions_app = typer.Typer(help="Check agent permissions and safety policy")
workspace_app = typer.Typer(help="Use named workspace/project corpus views")
query_app = typer.Typer(help="Save and run recurring research queries")
brief_app = typer.Typer(help="Generate research briefs from saved queries")
app.add_typer(review_app, name="review")
app.add_typer(notes_app, name="notes")
app.add_typer(import_app, name="import")
app.add_typer(calibre_app, name="calibre")
app.add_typer(grimmory_app, name="grimmory")
app.add_typer(prompts_app, name="prompts")
app.add_typer(concepts_app, name="concepts")
app.add_typer(embeddings_app, name="embeddings")
app.add_typer(eval_app, name="eval")
app.add_typer(setup_app, name="setup")
app.add_typer(migrations_app, name="migrations")
app.add_typer(audit_app, name="audit")
app.add_typer(restore_points_app, name="restore-points")
app.add_typer(permissions_app, name="permissions")
app.add_typer(workspace_app, name="workspace")
app.add_typer(query_app, name="query")
app.add_typer(brief_app, name="brief")
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


@review_app.command("machine-drafts")
def review_machine_drafts_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List machine-generated summaries/concepts awaiting human review."""
    import json as json_lib

    drafts = machine_drafts()
    payload = drafts_as_dict(drafts)

    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Machine drafts")
    table_out.add_column("Type")
    table_out.add_column("ID")
    table_out.add_column("Title")
    table_out.add_column("Status")
    table_out.add_column("Detail")
    table_out.add_column("Path")
    for item in drafts:
        table_out.add_row(
            item.artefact_type,
            item.id,
            item.title or "",
            item.status,
            item.detail or "",
            item.path,
        )
    console.print(table_out)
    console.print(f"[green]{len(drafts)} machine draft(s) found[/green]")


@review_app.command("approve-summary")
def review_approve_summary_command(
    book_id: str,
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Mark a book summary and chapter summary as human-reviewed."""
    import json as json_lib

    result = approve_summary(book_id, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]Approved summary for {book_id}[/green]")
    for path in result.get("changed", []):
        console.print(f"- {path}")


@review_app.command("approve-concepts")
def review_approve_concepts_command(
    book_id: str,
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Mark all extracted concepts for a book as human-reviewed."""
    import json as json_lib

    result = approve_concepts(book_id, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]Approved concepts for {book_id}[/green]")
    console.print(f"Concepts changed: {len(result.get('changed_concepts', []))}")


@review_app.command("reject-concept")
def review_reject_concept_command(
    concept_id: str,
    reason: str | None = typer.Option(None, "--reason", help="Reason for rejection."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Mark one extracted concept as rejected."""
    import json as json_lib

    result = reject_concept(concept_id, reason=reason, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[yellow]Rejected concept {concept_id}[/yellow]")
    if reason:
        console.print(f"Reason: {reason}")


@review_app.command("mark-human-reviewed")
def review_mark_human_reviewed_command(
    path: Path,
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Mark a YAML or Markdown artefact as human-reviewed."""
    import json as json_lib

    result = mark_human_reviewed(path, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]Marked human-reviewed:[/green] {result['path']}")


@review_app.command("set-summary-status")
def review_set_summary_status_command(
    book_id: str,
    status: str = typer.Argument(..., help="machine_draft, needs_human_review, human_reviewed, rejected or superseded."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Set review status for a summary."""
    import json as json_lib

    result = set_summary_status(book_id, status=status, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]Summary status updated:[/green] {book_id} -> {status}")


@review_app.command("set-concepts-status")
def review_set_concepts_status_command(
    book_id: str,
    status: str = typer.Argument(..., help="machine_draft, needs_human_review, human_reviewed, rejected or superseded."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name/identifier."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Set review status for all concepts in a book."""
    import json as json_lib

    result = set_concepts_status(book_id, status=status, reviewer=reviewer)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]Concept status updated:[/green] {book_id} -> {status}")


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


@review_app.command("duplicates")
def review_duplicates_command(
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate possible duplicate review file before displaying."),
    books_dir: Path | None = typer.Option(None, "--books-dir"),
    raw_dir: Path | None = typer.Option(Path("data/raw-books"), "--raw-dir"),
    threshold: float = typer.Option(0.88, "--threshold"),
):
    """Show duplicate review candidates from data/review/possible_duplicates.yaml."""
    import yaml
    output_path = Path("data/review/possible_duplicates.yaml")
    if regenerate or not output_path.exists():
        books = load_book_identities(books_dir=books_dir, raw_dir=raw_dir, include_raw=True)
        groups = find_duplicate_groups(books, by="all", similarity_threshold=threshold)
        write_duplicate_review(groups, output=output_path)

    if not output_path.exists():
        console.print("[yellow]No duplicate review file found. Run: bookmem duplicates --write-review[/yellow]")
        return

    data = yaml.safe_load(output_path.read_text(encoding="utf-8")) or {}
    groups = data.get("groups", [])
    if not groups:
        console.print("[green]No possible duplicates in review file[/green]")
        return

    table_out = Table(title="Duplicate review candidates")
    table_out.add_column("Reason")
    table_out.add_column("Score")
    table_out.add_column("Books")
    table_out.add_column("Review")
    for group in groups:
        paths = [str(book.get("path", "")) for book in group.get("books", [])]
        table_out.add_row(
            str(group.get("reason", "")),
            f"{float(group.get('score', 0.0)):.0%}",
            "\n".join(paths),
            str((group.get("review") or {}).get("status", "pending")),
        )
    console.print(table_out)


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
    profile: str = typer.Option("epub_pandoc", "--profile", help="Cleaning profile to use when cleaning."),
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
        cleaning_profile=profile,
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
    profile: str = typer.Option("epub_pandoc", "--profile", help="Cleaning profile to use when cleaning."),
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
                cleaning_profile=profile,
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

@app.command("summary-providers")
def summary_providers_command():
    """List configured summary providers."""
    providers = load_summary_providers()
    table_out = Table(title="Summary providers")
    table_out.add_column("Provider")
    table_out.add_column("Enabled")
    table_out.add_column("Generator")
    table_out.add_column("Model")
    table_out.add_column("Description")
    for name, cfg in sorted(providers.items()):
        table_out.add_row(
            str(name),
            "yes" if cfg.get("enabled") else "no",
            str(cfg.get("generator") or ""),
            str(cfg.get("model") or ""),
            str(cfg.get("description") or ""),
        )
    console.print(table_out)


@app.command("validate-summary-providers")
def validate_summary_providers_command():
    """Validate configured summary providers."""
    issues = validate_summary_providers()
    if not issues:
        console.print("[green]Summary providers validated successfully[/green]")
        return
    table_out = Table(title="Summary provider validation issues")
    table_out.add_column("Provider")
    table_out.add_column("Issue")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(str(issue.get("provider", "")), str(issue.get("issue", "")), str(issue.get("message", "")))
    console.print(table_out)
    raise typer.Exit(code=1)


@app.command("summarise-book")
def summarise_book_command(
    path: Path,
    write: bool = typer.Option(True, "--write/--dry-run", help="Write derived summary files. Use --dry-run to preview paths only."),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="Overwrite existing summary files."),
    provider: str = typer.Option("deterministic", "--provider", help="Summary provider: deterministic, openai or local_ollama."),
):
    """Generate book-level and chapter-level YAML summaries for one canonical Markdown book."""
    result = summarise_book_with_provider(path, provider=provider, write=write, overwrite=overwrite)
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
    provider: str = typer.Option("deterministic", "--provider", help="Summary provider: deterministic, openai or local_ollama."),
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

    results = summarise_books_with_provider(books_dir, provider=provider, write=write, overwrite=overwrite)
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



@app.command("map-topic")
def map_topic_command(
    query: str,
    book_limit: int = typer.Option(8, "--book-limit", help="Maximum number of strongest books to display."),
    summary_limit: int = typer.Option(12, "--summary-limit", help="Maximum summary hits to inspect."),
    chunk_limit: int = typer.Option(12, "--chunk-limit", help="Maximum chunk hits to inspect."),
    themes_limit: int = typer.Option(12, "--themes-limit", help="Maximum common themes to display."),
    include_chunks: bool = typer.Option(True, "--chunks/--no-chunks", help="Include indexed chunk retrieval as well as summaries."),
    fallback: bool = typer.Option(True, "--fallback/--no-fallback", help="Fall back to broad chunk search if routed chunk search finds nothing."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write the topic map as YAML, or JSON if the path ends in .json."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
):
    """Map a topic across the library using summaries and indexed chunks."""
    topic_map = build_topic_map(
        query=query,
        book_limit=book_limit,
        summary_limit=summary_limit,
        chunk_limit=chunk_limit,
        themes_limit=themes_limit,
        include_chunks=include_chunks,
        fallback=fallback,
    )

    if output:
        write_topic_map(topic_map, output)

    if json_output:
        console.print(topic_map.to_json(indent=2))
        if output:
            console.print(f"[green]Wrote topic map:[/green] {output}")
        return

    route = topic_map.route
    console.print(
        Panel(
            f"Aliases: {', '.join(route.get('aliases', [])) or 'none'}\n"
            f"Classes: {', '.join(route.get('class_codes', [])) or 'none'}\n"
            f"Confidence: {float(route.get('confidence', 0.0)):.2f}\n"
            f"Matched terms: {', '.join(route.get('matched_terms', [])) or 'none'}\n\n"
            f"{route.get('reason', '')}",
            title="Topic route",
            expand=False,
        )
    )

    if topic_map.strongest_books:
        table_out = Table(title="Strongest books")
        table_out.add_column("Rank", justify="right")
        table_out.add_column("Book")
        table_out.add_column("Author")
        table_out.add_column("Score", justify="right")
        table_out.add_column("Why matched")
        for idx, book in enumerate(topic_map.strongest_books, start=1):
            table_out.add_row(
                str(idx),
                book.title,
                book.author or "",
                f"{book.score:.2f}",
                "; ".join(book.reasons[:4]),
            )
        console.print(table_out)
    else:
        console.print("[yellow]No matching books found. Run bookmem summarise-books and bookmem ingest first.[/yellow]")

    if topic_map.common_themes:
        console.print("[bold]Common themes[/bold]")
        for theme in topic_map.common_themes:
            console.print(f"- {theme}")

    for idx, book in enumerate(topic_map.strongest_books[:3], start=1):
        evidence_lines: list[str] = []
        for hit in book.summary_hits[:2]:
            label = hit.get("chapter_title") or hit.get("level")
            evidence_lines.append(f"Summary: {label} · score {hit.get('score')}\n{hit.get('excerpt', '')}")
        for hit in book.chunk_hits[:2]:
            citation = hit.get("citation") or hit.get("chunk_id")
            evidence_lines.append(f"Chunk: {citation}\n{hit.get('excerpt', '')}")
        if evidence_lines:
            console.print(
                Panel(
                    "\n\n".join(evidence_lines),
                    title=f"Evidence for {idx}. {book.title}",
                    expand=False,
                )
            )

    if output:
        console.print(f"[green]Wrote topic map:[/green] {output}")



@app.command("export")
def agent_export_command(
    format: str = typer.Option("jsonl", "--format", help="Agent export format: jsonl, llamaindex, langchain, markdown-index, or all"),
    output_dir: Path = typer.Option(Path("exports"), "--output-dir", "-o", help="Directory to write export files into"),
    books_dir: Path | None = typer.Option(None, "--books-dir", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
):
    """Export the BookMem corpus for other agents and retrieval frameworks."""
    export_format = format.lower().strip()
    supported = set(SUPPORTED_AGENT_EXPORT_FORMATS) | {"all"}
    if export_format not in supported:
        console.print(f"[red]Unsupported format: {export_format}. Supported: {', '.join(sorted(supported))}[/red]")
        raise typer.Exit(code=1)

    result = export_agent_corpus(export_format=export_format, output_dir=output_dir, books_dir=books_dir)

    table_out = Table(title="Agent export files")
    table_out.add_column("File")
    table_out.add_column("Size", justify="right")
    for path in result.files:
        size = path.stat().st_size if path.exists() else 0
        table_out.add_row(str(path), f"{size:,} bytes")
    console.print(table_out)
    console.print(
        f"[green]Exported {result.book_count} books and {result.chunk_count} chunks "
        f"for format '{result.format}' to {result.output_dir}[/green]"
    )

@app.command("cite")
def cite_command(
    path: Path,
    style: str = typer.Option("apa", "--style", help="Citation style: apa, harvard, mla, chicago"),
):
    """Generate a formatted citation for one canonical Markdown book."""
    style = style.lower().strip()
    styles = supported_styles()
    if style not in styles:
        console.print(f"[red]Unsupported style: {style}. Supported: {', '.join(sorted(styles))}[/red]")
        raise typer.Exit(code=1)
    reference = reference_from_frontmatter(path)
    console.print(format_reference(reference, style=style))


@app.command("cite-books")
def cite_books_command(
    books_dir: Path,
    style: str = typer.Option("apa", "--style", help="Citation style: apa, harvard, mla, chicago"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional file to write citations to"),
):
    """Generate formatted citations for all canonical Markdown books in a directory."""
    style = style.lower().strip()
    styles = supported_styles()
    if style not in styles:
        console.print(f"[red]Unsupported style: {style}. Supported: {', '.join(sorted(styles))}[/red]")
        raise typer.Exit(code=1)
    references = references_from_directory(books_dir)
    if not references:
        console.print(f"[yellow]No Markdown files found under {books_dir}[/yellow]")
        return
    lines = [format_reference(reference, style=style) for reference in references]
    text = "\n\n".join(lines) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote {len(references)} citations to {output}[/green]")
        return
    console.print(text)


@app.command("export-references")
def export_references_command(
    books_dir: Path,
    format: str = typer.Option("bibtex", "--format", help="Reference export format, such as bibtex, ris, csl-json or endnote-xml"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file. Prints to stdout when omitted."),
):
    """Export book references for Zotero, EndNote, Mendeley and other reference managers."""
    export_format = format.lower().strip()
    formats = supported_export_formats()
    if export_format not in formats:
        console.print(f"[red]Unsupported format: {export_format}. Supported: {', '.join(sorted(formats))}[/red]")
        raise typer.Exit(code=1)
    references = references_from_directory(books_dir)
    if not references:
        console.print(f"[yellow]No Markdown files found under {books_dir}[/yellow]")
        return
    text = export_references(references, export_format=export_format)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Exported {len(references)} references to {output}[/green]")
        return
    console.print(text)


@app.command("stats")
def stats_command(
    by_class: bool = typer.Option(False, "--by-class", help="Show class distribution."),
    by_author: bool = typer.Option(False, "--by-author", help="Show author distribution."),
    by_topic: bool = typer.Option(False, "--by-topic", help="Show topic distribution."),
    books_dir: Path | None = typer.Option(None, "--books-dir", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum rows to display in each breakdown."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show collection-level statistics for the canonical book corpus."""
    import json

    stats = load_book_stats(books_dir=books_dir)
    if not stats:
        console.print("[yellow]No canonical Markdown books found[/yellow]")
        return

    payload = stats_payload(stats, limit=limit)
    if json_output:
        console.print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    totals = collection_totals(stats)
    console.print(
        Panel(
            f"Total books: {totals['books']}\n"
            f"Indexed books: {totals['indexed_books']}\n"
            f"Indexed chunks: {totals['indexed_chunks']}\n"
            f"Books needing index: {totals['books_needing_index']}\n"
            f"Unclassified books: {totals['unclassified_books']}\n"
            f"Books without author: {totals['books_without_author']}\n"
            f"Books without topics: {totals['books_without_topics']}\n"
            f"Books with ISBN: {totals['books_with_isbn']}",
            title="Collection statistics",
            expand=False,
        )
    )

    show_all = not (by_class or by_author or by_topic)

    if show_all or by_class:
        table_out = Table(title="Books by BMDC class")
        table_out.add_column("Class")
        table_out.add_column("Label")
        table_out.add_column("Books", justify="right")
        table_out.add_column("Chunks", justify="right")
        table_out.add_column("Authors", justify="right")
        for row in class_counts(stats)[:limit]:
            table_out.add_row(
                str(row["class_code"]),
                str(row["label"]),
                str(row["books"]),
                str(row["chunks"]),
                str(row["authors"]),
            )
        console.print(table_out)

    if show_all or by_author:
        table_out = Table(title="Books by author")
        table_out.add_column("Author")
        table_out.add_column("Books", justify="right")
        table_out.add_column("Chunks", justify="right")
        table_out.add_column("Classes")
        for row in author_counts(stats)[:limit]:
            table_out.add_row(
                str(row["author"]),
                str(row["books"]),
                str(row["chunks"]),
                str(row["classes"]),
            )
        console.print(table_out)

    if show_all or by_topic:
        rows = topic_counts(stats)[:limit]
        if not rows:
            console.print("[yellow]No topics found in frontmatter[/yellow]")
            return
        table_out = Table(title="Books by topic")
        table_out.add_column("Topic")
        table_out.add_column("Books", justify="right")
        table_out.add_column("Chunks", justify="right")
        table_out.add_column("Classes")
        for row in rows:
            table_out.add_row(
                str(row["topic"]),
                str(row["books"]),
                str(row["chunks"]),
                str(row["classes"]),
            )
        console.print(table_out)


@app.command("duplicates")
def duplicates_command(
    by: str = typer.Option(
        "all",
        "--by",
        help="Duplicate method: all, isbn, title-author, content, or near",
    ),
    books_dir: Path | None = typer.Option(None, "--books-dir", help="Canonical books directory. Defaults to BOOKMEM_BOOKS_DIR."),
    raw_dir: Path | None = typer.Option(Path("data/raw-books"), "--raw-dir", help="Optional raw-books directory to include."),
    include_raw: bool = typer.Option(True, "--include-raw/--canonical-only", help="Include raw Markdown exports as well as canonical books."),
    threshold: float = typer.Option(0.88, "--threshold", help="Near-duplicate similarity threshold from 0.0 to 1.0."),
    write_review: bool = typer.Option(False, "--write-review", help="Write data/review/possible_duplicates.yaml."),
):
    """Find duplicate or near-duplicate books by ISBN, title/author, content hash or similarity."""
    valid_methods = {"all", "isbn", "title-author", "content", "near"}
    if by not in valid_methods:
        console.print(f"[red]Unsupported duplicate method: {by}. Supported: {', '.join(sorted(valid_methods))}[/red]")
        raise typer.Exit(code=1)

    books = load_book_identities(books_dir=books_dir, raw_dir=raw_dir, include_raw=include_raw)
    if not books:
        console.print("[yellow]No Markdown files found to compare[/yellow]")
        return

    groups = find_duplicate_groups(books, by=by, similarity_threshold=threshold)
    if not groups:
        console.print(f"[green]No duplicates found across {len(books)} files[/green]")
        if write_review:
            output_path = write_duplicate_review(groups)
            console.print(f"[green]Wrote empty duplicate review file to {output_path}[/green]")
        return

    console.print(f"[yellow]Found {len(groups)} possible duplicate group(s) across {len(books)} files[/yellow]")
    for idx, group in enumerate(groups, start=1):
        lines = [
            f"[bold]Reason:[/bold] {group.reason}",
            f"[bold]Score:[/bold] {group.score:.0%}",
        ]
        if group.details:
            lines.append("[bold]Details:[/bold] " + "; ".join(group.details))
        lines.append("")
        for book in group.books:
            isbn_text = ", ".join(book.isbns) if book.isbns else "no ISBN"
            lines.append(f"- {book.path}")
            lines.append(f"  {book.title or 'Unknown title'} — {book.author or 'Unknown author'}")
            lines.append(f"  {book.collection}; {isbn_text}")
        console.print(Panel("\n".join(lines), title=f"Possible duplicate {idx}", expand=False))

    if write_review:
        output_path = write_duplicate_review(groups)
        console.print(f"[green]Wrote duplicate review file to {output_path}[/green]")


@app.command("reference-formats")
def reference_formats_command():
    """List available YAML-defined reference export formats."""
    formats = load_reference_export_formats().get("formats", {})
    if not formats:
        console.print("[yellow]No reference export formats loaded[/yellow]")
        return

    table_out = Table(title="Reference export formats")
    table_out.add_column("Format")
    table_out.add_column("Label")
    table_out.add_column("Engine")
    table_out.add_column("Extension")
    table_out.add_column("Description")

    for key, format_def in sorted(formats.items()):
        if str(key).startswith("_"):
            continue
        table_out.add_row(
            str(key),
            str(format_def.get("label", "")) if isinstance(format_def, dict) else "",
            str(format_def.get("engine", "")) if isinstance(format_def, dict) else "",
            str(format_def.get("extension", "")) if isinstance(format_def, dict) else "",
            str(format_def.get("description", "")) if isinstance(format_def, dict) else "",
        )
    console.print(table_out)


@app.command("validate-reference-formats")
def validate_reference_formats_command():
    """Validate YAML-defined reference export formats by rendering a sample reference."""
    issues = validate_reference_export_formats()
    if not issues:
        console.print("[green]Reference export formats validated successfully[/green]")
        return

    table_out = Table(title="Reference export format validation issues")
    table_out.add_column("Format")
    table_out.add_column("Issue")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(
            str(issue.get("format", "")),
            str(issue.get("issue", "")),
            str(issue.get("message", "")),
        )
    console.print(table_out)
    raise typer.Exit(code=1)


@app.command("citation-styles")
def citation_styles_command():
    """List available YAML-defined citation styles."""
    styles = load_citation_styles().get("styles", {})
    if not styles:
        console.print("[yellow]No citation styles loaded[/yellow]")
        return

    table_out = Table(title="Citation styles")
    table_out.add_column("Style")
    table_out.add_column("Label")
    table_out.add_column("Description")

    for key, style_def in sorted(styles.items()):
        if key.startswith("_"):
            continue
        table_out.add_row(
            str(key),
            str(style_def.get("label", "")) if isinstance(style_def, dict) else "",
            str(style_def.get("description", "")) if isinstance(style_def, dict) else "",
        )
    console.print(table_out)


@app.command("validate-citation-styles")
def validate_citation_styles_command():
    """Validate YAML-defined citation styles by rendering a sample reference."""
    issues = validate_citation_styles()
    if not issues:
        console.print("[green]Citation styles validated successfully[/green]")
        return

    table_out = Table(title="Citation style validation issues")
    table_out.add_column("Style")
    table_out.add_column("Issue")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(
            str(issue.get("style", "")),
            str(issue.get("issue", "")),
            str(issue.get("message", "")),
        )
    console.print(table_out)
    raise typer.Exit(code=1)




@calibre_app.command("scan")
def calibre_scan_command(
    library_path: Path,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum rows to display."),
):
    """Scan a Calibre library metadata.db."""
    import json as json_lib

    books = scan_calibre_library(library_path)
    if json_output:
        console.print(json_lib.dumps([calibre_book_as_dict(book) for book in books], indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Calibre library: {library_path}")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("ISBN")
    table_out.add_column("Formats")
    for book in books[:limit]:
        table_out.add_row(
            book.title,
            ", ".join(book.authors),
            book.isbn or "",
            ", ".join(book.formats),
        )
    console.print(table_out)
    console.print(f"[green]{len(books)} book(s) found[/green]")


@calibre_app.command("metadata")
def calibre_metadata_command(
    library_path: Path,
    query: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Find Calibre metadata by title, author, ISBN or tag."""
    import json as json_lib

    matches = find_calibre_book(library_path, query)
    if json_output:
        console.print(json_lib.dumps([calibre_book_as_dict(book) for book in matches], indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Calibre metadata matches: {query}")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("ISBN")
    table_out.add_column("Publisher")
    table_out.add_column("Tags")
    for book in matches:
        table_out.add_row(
            book.title,
            ", ".join(book.authors),
            book.isbn or "",
            book.publisher or "",
            ", ".join(book.tags[:8]),
        )
    console.print(table_out)


@calibre_app.command("import")
def calibre_import_command(
    library_path: Path,
    output_dir: Path = typer.Option(Path("data/raw-books"), "--output-dir", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing metadata stubs."),
):
    """Import Calibre metadata as raw Markdown stubs."""
    paths = import_calibre_metadata_stubs(library_path, output_dir=output_dir, overwrite=overwrite)
    console.print(f"[green]{len(paths)} Calibre metadata stub(s) written to {output_dir}[/green]")


@calibre_app.command("enrich")
def calibre_enrich_command(
    book: Path,
    library_path: Path,
    query: str | None = typer.Option(None, "--query", help="Override the lookup query."),
    write: bool = typer.Option(False, "--write", help="Write Calibre metadata into BookMem frontmatter."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing frontmatter fields."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Enrich one canonical Markdown book from Calibre metadata."""
    import json as json_lib

    frontmatter, match = enrich_markdown_from_calibre(
        book_path=book,
        calibre_library=library_path,
        query=query,
        write=write,
        overwrite=overwrite,
    )
    payload = {
        "book": str(book),
        "matched": calibre_book_as_dict(match) if match else None,
        "wrote": write,
        "frontmatter": frontmatter,
    }
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return
    if not match:
        console.print("[yellow]No Calibre match found[/yellow]")
        return
    console.print(
        Panel(
            f"Matched: {match.title}\n"
            f"Authors: {', '.join(match.authors)}\n"
            f"ISBN: {match.isbn or ''}\n"
            f"Publisher: {match.publisher or ''}\n"
            f"Wrote: {'yes' if write else 'no'}",
            title="Calibre enrichment",
            expand=False,
        )
    )


@import_app.command("epub")
def import_epub_command(
    source: Path,
    output_dir: Path = typer.Option(Path("data/raw-books"), "--output-dir", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing raw Markdown file."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Import an EPUB file into raw Markdown."""
    import json as json_lib

    result = import_epub(source, output_dir=output_dir, overwrite=overwrite)
    if json_output:
        console.print(json_lib.dumps(import_result_as_dict(result), indent=2, ensure_ascii=False))
        return
    console.print(
        Panel(
            f"Source: {result.source_path}\n"
            f"Output: {result.output_path}\n"
            f"Title: {result.title or ''}\n"
            f"Author: {result.author or ''}\n"
            f"Sections: {result.item_count}",
            title="EPUB imported",
            expand=False,
        )
    )


@import_app.command("html")
def import_html_command(
    source: Path,
    output_dir: Path = typer.Option(Path("data/raw-books"), "--output-dir", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing raw Markdown file."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Import an HTML file into raw Markdown."""
    import json as json_lib

    result = import_html(source, output_dir=output_dir, overwrite=overwrite)
    if json_output:
        console.print(json_lib.dumps(import_result_as_dict(result), indent=2, ensure_ascii=False))
        return
    console.print(
        Panel(
            f"Source: {result.source_path}\n"
            f"Output: {result.output_path}\n"
            f"Sections: {result.item_count}",
            title="HTML imported",
            expand=False,
        )
    )


@import_app.command("pdf")
def import_pdf_command(
    source: Path,
    output_dir: Path = typer.Option(Path("data/raw-books"), "--output-dir", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing raw Markdown file."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Import a PDF file into raw Markdown using best-effort text extraction."""
    import json as json_lib

    result = import_pdf(source, output_dir=output_dir, overwrite=overwrite)
    if json_output:
        console.print(json_lib.dumps(import_result_as_dict(result), indent=2, ensure_ascii=False))
        return
    console.print(
        Panel(
            f"Source: {result.source_path}\n"
            f"Output: {result.output_path}\n"
            f"Title: {result.title or ''}\n"
            f"Author: {result.author or ''}\n"
            f"Pages with text: {result.item_count}\n"
            f"Warning: {result.warning or ''}",
            title="PDF imported",
            expand=False,
        )
    )


@import_app.command("calibre")
def import_calibre_command(
    library_path: Path,
    output_dir: Path = typer.Option(Path("data/raw-books"), "--output-dir", "-o"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing raw Markdown stubs."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Import Calibre metadata into raw Markdown stubs."""
    import json as json_lib

    results = import_calibre(library_path, output_dir=output_dir, overwrite=overwrite)
    if json_output:
        console.print(json_lib.dumps([import_result_as_dict(item) for item in results], indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Calibre metadata imported")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Output")
    for result in results:
        table_out.add_row(result.title or "", result.author or "", result.output_path)
    console.print(table_out)
    console.print(f"[green]{len(results)} metadata stub(s) written[/green]")


@grimmory_app.command("sidecar")
def grimmory_sidecar_command(
    book: Path,
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Directory for sidecar. Defaults to book folder."),
    overwrite: bool = typer.Option(False, "--overwrite"),
):
    """Write a Grimmory-style metadata JSON sidecar for one BookMem book."""
    sidecar = write_grimmory_sidecar(book, output_dir=output_dir, overwrite=overwrite)
    console.print(f"[green]Wrote sidecar:[/green] {sidecar}")


@grimmory_app.command("export")
def grimmory_export_command(
    books_dir: Path = typer.Argument(Path("data/books")),
    output_dir: Path = typer.Option(Path("exports/grimmory"), "--output-dir", "-o"),
    copy_markdown: bool = typer.Option(False, "--copy-markdown", help="Copy BookMem Markdown into the Grimmory export folder."),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Export BookMem metadata as Grimmory-ready sidecar files."""
    import json as json_lib

    results = export_grimmory_library(
        books_dir=books_dir,
        output_dir=output_dir,
        copy_markdown=copy_markdown,
        overwrite=overwrite,
    )
    if json_output:
        console.print(json_lib.dumps([grimmory_result_as_dict(result) for result in results], indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Grimmory export")
    table_out.add_column("Title")
    table_out.add_column("Authors")
    table_out.add_column("Sidecar")
    for result in results:
        table_out.add_row(result.title, ", ".join(result.authors), result.sidecar_path)
    console.print(table_out)
    console.print(f"[green]{len(results)} sidecar file(s) written[/green]")


def _print_audit_table(records, title: str = "Audit log"):
    table_out = Table(title=title)
    table_out.add_column("Timestamp")
    table_out.add_column("Action")
    table_out.add_column("Status")
    table_out.add_column("Provider")
    table_out.add_column("Target")
    table_out.add_column("Changed")
    table_out.add_column("Command")
    for record in records:
        changed = record.get("changed_files") or []
        table_out.add_row(
            str(record.get("timestamp") or ""),
            str(record.get("action") or ""),
            str(record.get("status") or ""),
            str(record.get("provider") or ""),
            str(record.get("target") or ""),
            str(len(changed)),
            str(record.get("command") or "")[:80],
        )
    console.print(table_out)


@app.command("reading-list")
def reading_list_command(
    query: str | None = typer.Argument(None, help="Reading-list query, e.g. 'I want to understand habit design'."),
    topic: str | None = typer.Option(None, "--topic", help="Topic to build a reading list for."),
    goal: str | None = typer.Option(None, "--goal", help="Goal to build a reading list for."),
    limit: int = typer.Option(8, "--limit", "-n", help="Number of books to recommend."),
    save: bool = typer.Option(False, "--save", help="Save JSON and Markdown outputs under data/reading-lists/."),
    name: str | None = typer.Option(None, "--name", help="Name for saved output."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Generate an ordered reading list from summaries, concepts, topic maps, graph and search."""
    import json as json_lib

    result = generate_reading_list(
        query=query,
        topic=topic,
        goal=goal,
        limit=limit,
        save=save,
        name=name,
    )

    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    console.print(
        Panel(
            f"Intent: {result['intent']}\n"
            f"Items: {len(result.get('items', []))}\n"
            f"Saved: {result.get('saved_path') or '(not saved)'}",
            title="Reading list",
            expand=False,
        )
    )

    for item in result.get("items", []):
        console.print(f"[bold]{item['rank']}. {item['suggested_posture']}: {item['title']}[/bold]")
        if item.get("author"):
            console.print(f"   Author: {item['author']}")
        if item.get("primary_class"):
            console.print(f"   Class: {item.get('primary_class')} {item.get('primary_label') or ''}")
        console.print(f"   Why: {item['why']}")
        evidence = item.get("evidence") or []
        for ev in evidence[:3]:
            console.print(f"   Evidence: {ev}")
        console.print("")

    if result.get("warnings"):
        console.print("[yellow]Warnings[/yellow]")
        for warning in result["warnings"]:
            console.print(f"- {warning}")


@query_app.command("save")
def query_save_command(
    query: str,
    name: str | None = typer.Option(None, "--name", "-n", help="Saved query name."),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Optional workspace scope."),
    description: str | None = typer.Option(None, "--description", "-d"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Tag. Can be used multiple times."),
    limit: int = typer.Option(8, "--limit"),
    context: int = typer.Option(1, "--context"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Save a reusable research query."""
    import json as json_lib

    result = save_query(
        query=query,
        name=name,
        workspace=workspace,
        description=description,
        tags=tag or [],
        limit=limit,
        context=context,
        overwrite=overwrite,
    )
    payload = result.__dict__
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return
    console.print(
        Panel(
            f"Name: {result.name}\n"
            f"Query: {result.query}\n"
            f"Workspace: {result.workspace or '(none)'}\n"
            f"Tags: {', '.join(result.tags)}",
            title="Saved query",
            expand=False,
        )
    )


@query_app.command("list")
def query_list_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List saved queries."""
    import json as json_lib

    queries = list_saved_queries()
    if json_output:
        console.print(json_lib.dumps(queries, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Saved queries")
    table_out.add_column("Name")
    table_out.add_column("Query")
    table_out.add_column("Workspace")
    table_out.add_column("Last run")
    table_out.add_column("Path")
    for item in queries:
        table_out.add_row(
            str(item.get("name") or ""),
            str(item.get("query") or ""),
            str(item.get("workspace") or ""),
            str(item.get("last_run_at") or ""),
            str(item.get("path") or ""),
        )
    console.print(table_out)


@query_app.command("run")
def query_run_command(
    name: str,
    update_last_run: bool = typer.Option(False, "--update-last-run", help="Update the saved query last_run_at timestamp."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Run a saved query and return its answer pack."""
    import json as json_lib

    result = run_saved_query(name, update_last_run=update_last_run)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    sq = result["saved_query"]
    pack = result["answer_pack"]
    console.print(
        Panel(
            f"Name: {sq['name']}\n"
            f"Query: {sq['query']}\n"
            f"Workspace: {sq.get('workspace') or '(none)'}\n"
            f"Relevant books: {len(pack.get('relevant_books', []))}\n"
            f"Top passages: {len(pack.get('top_passages', []))}",
            title="Saved query run",
            expand=False,
        )
    )

    table_out = Table(title="Relevant books")
    table_out.add_column("#", justify="right")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Class")
    for index, book in enumerate(pack.get("relevant_books", []), start=1):
        table_out.add_row(
            str(index),
            str(book.get("title") or ""),
            str(book.get("author") or ""),
            str(book.get("primary_class") or ""),
        )
    console.print(table_out)


@brief_app.command("generate")
def brief_generate_command(
    name: str,
    no_update_last_run: bool = typer.Option(False, "--no-update-last-run", help="Do not update saved query last_run_at."),
    no_markdown: bool = typer.Option(False, "--no-markdown", help="Only generate JSON brief."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Generate a research brief from a saved query."""
    import json as json_lib

    result = generate_brief(
        name,
        update_last_run=not no_update_last_run,
        markdown=not no_markdown,
    )
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    brief = result["brief"]
    sq = brief["saved_query"]
    console.print(
        Panel(
            f"Name: {sq['name']}\n"
            f"Query: {sq['query']}\n"
            f"Workspace: {sq.get('workspace') or '(none)'}\n"
            f"JSON: {result['json_path']}\n"
            f"Markdown: {result.get('markdown_path') or '(not generated)'}\n"
            f"Best books: {len(brief.get('best_books', []))}\n"
            f"Top passages: {len(brief.get('top_passages', []))}\n"
            f"Concepts: {len(brief.get('related_concepts', []))}\n"
            f"Citations: {len(brief.get('citations', []))}",
            title="Research brief generated",
            expand=False,
        )
    )


@workspace_app.command("list")
def workspace_list_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List configured workspaces."""
    import json as json_lib

    workspaces = list_workspaces_as_dict()
    if json_output:
        console.print(json_lib.dumps(workspaces, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Workspaces")
    table_out.add_column("Name")
    table_out.add_column("Label")
    table_out.add_column("Classes")
    table_out.add_column("Topics")
    table_out.add_column("Aliases")

    for ws in workspaces:
        table_out.add_row(
            ws["name"],
            ws["label"],
            ", ".join(ws.get("classes", [])),
            ", ".join(ws.get("topics", [])[:8]),
            ", ".join(ws.get("aliases", [])),
        )
    console.print(table_out)


@workspace_app.command("validate")
def workspace_validate_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Validate workspace configuration."""
    import json as json_lib

    issues = validate_workspaces()
    if json_output:
        console.print(json_lib.dumps({"issues": issues}, indent=2, ensure_ascii=False))
        return

    if not issues:
        console.print("[green]Workspace configuration is valid.[/green]")
        return

    table_out = Table(title="Workspace validation issues")
    table_out.add_column("Workspace")
    table_out.add_column("Level")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(issue.get("workspace", ""), issue.get("level", ""), issue.get("message", ""))
    console.print(table_out)


@workspace_app.command("search")
def workspace_search_command(
    workspace: str,
    query: str,
    limit: int = typer.Option(10, "--limit", "-n"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Search within a named workspace/project view."""
    import json as json_lib

    result = workspace_search(workspace, query, limit=limit)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    ws = result["workspace"]
    console.print(
        Panel(
            f"Workspace: {ws['name']}\n"
            f"Label: {ws['label']}\n"
            f"Query: {query}\n"
            f"Results: {result['count']}",
            title="Workspace search",
            expand=False,
        )
    )

    table_out = Table(title=f"Workspace search results: {workspace}")
    table_out.add_column("#", justify="right")
    table_out.add_column("Book")
    table_out.add_column("Author")
    table_out.add_column("Class")
    table_out.add_column("Location")
    table_out.add_column("Citation")

    for index, row in enumerate(result["results"], start=1):
        table_out.add_row(
            str(index),
            str(row.get("title") or ""),
            str(row.get("author") or ""),
            str(row.get("primary_class") or ""),
            str(row.get("heading_path") or ""),
            str(row.get("citation") or ""),
        )
    console.print(table_out)


@workspace_app.command("answer-pack")
def workspace_answer_pack_command(
    workspace: str,
    query: str,
    limit: int = typer.Option(6, "--limit", "-n"),
    context: int = typer.Option(1, "--context", "-c"),
    no_text: bool = typer.Option(False, "--no-text", help="Return metadata/excerpts rather than full passage text."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Build an answer pack scoped to a named workspace/project view."""
    import json as json_lib

    pack = workspace_answer_pack(
        workspace,
        query,
        limit=limit,
        context=context,
        include_text=not no_text,
    )

    if json_output:
        console.print(json_lib.dumps(pack, indent=2, ensure_ascii=False, default=str))
        return

    ws = pack["workspace"]
    console.print(
        Panel(
            f"Workspace: {ws['name']}\n"
            f"Label: {ws['label']}\n"
            f"Query: {query}\n"
            f"Top passages: {len(pack.get('top_passages', []))}\n"
            f"Citations: {len(pack.get('citations', []))}",
            title="Workspace answer pack",
            expand=False,
        )
    )

    table_out = Table(title="Relevant books")
    table_out.add_column("#", justify="right")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Class")
    for index, book in enumerate(pack.get("relevant_books", []), start=1):
        table_out.add_row(
            str(index),
            str(book.get("title") or ""),
            str(book.get("author") or ""),
            str(book.get("primary_class") or ""),
        )
    console.print(table_out)


@permissions_app.command("check")
def permissions_check_command(
    agent: str,
    action: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Check whether an agent may perform an action."""
    import json as json_lib

    decision = check_permission(agent, action)
    payload = decision_as_dict(decision)

    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    colour = {
        "allow": "green",
        "require_confirmation": "yellow",
        "deny": "red",
        "unknown": "red",
    }.get(decision.decision, "white")

    console.print(
        Panel(
            f"Agent: {decision.agent}\n"
            f"Action: {decision.action}\n"
            f"Decision: [{colour}]{decision.decision}[/{colour}]\n"
            f"Matched rule: {decision.matched_rule or '(none)'}\n"
            f"Reason: {decision.reason}",
            title="Permission check",
            expand=False,
        )
    )

    if decision.decision in {"deny", "unknown"}:
        raise typer.Exit(code=2)
    if decision.decision == "require_confirmation":
        raise typer.Exit(code=3)


@permissions_app.command("list")
def permissions_list_command(
    agent: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List effective permissions for an agent."""
    import json as json_lib

    payload = list_agent_permissions(agent)
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Agent: {payload['agent']}\n"
            f"Exists: {'yes' if payload['agent_exists'] else 'no'}\n"
            f"Description: {payload.get('description') or ''}",
            title="Agent permissions",
            expand=False,
        )
    )

    for section in ("allow", "require_confirmation", "deny"):
        table_out = Table(title=section)
        table_out.add_column("Rule")
        for rule in payload[section]:
            table_out.add_row(rule)
        console.print(table_out)


@permissions_app.command("agents")
def permissions_agents_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List configured agent permission profiles."""
    import json as json_lib

    payload = list_agents()
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Permission agents")
    table_out.add_column("Agent")
    table_out.add_column("Description")
    table_out.add_column("Allow")
    table_out.add_column("Confirm")
    table_out.add_column("Deny")
    for item in payload:
        table_out.add_row(
            item["agent"],
            item.get("description", ""),
            str(item.get("allow_count", 0)),
            str(item.get("require_confirmation_count", 0)),
            str(item.get("deny_count", 0)),
        )
    console.print(table_out)


@permissions_app.command("validate")
def permissions_validate_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Validate agent permissions policy."""
    import json as json_lib

    issues = validate_permissions()
    if json_output:
        console.print(json_lib.dumps({"issues": issues}, indent=2, ensure_ascii=False))
        return

    if not issues:
        console.print("[green]Agent permissions policy is valid.[/green]")
        return

    table_out = Table(title="Permission policy issues")
    table_out.add_column("Level")
    table_out.add_column("Issue")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(issue.get("level", ""), issue.get("issue", ""), issue.get("message", ""))
    console.print(table_out)

    if any(issue.get("level") == "error" for issue in issues):
        raise typer.Exit(code=1)


@restore_points_app.command("list")
def restore_points_list_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List restore points."""
    import json as json_lib

    points = list_restore_points()
    if json_output:
        console.print(json_lib.dumps(points, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Restore points")
    table_out.add_column("ID")
    table_out.add_column("Created")
    table_out.add_column("Label")
    table_out.add_column("Canonical")
    table_out.add_column("Archive")
    for point in points:
        table_out.add_row(
            point.get("restore_point_id", ""),
            point.get("created_at", ""),
            point.get("label", ""),
            "yes" if point.get("include_canonical_books") else "no",
            point.get("archive_path", ""),
        )
    console.print(table_out)


@restore_points_app.command("create")
def restore_points_create_command(
    label: str,
    include_canonical_books: bool = typer.Option(False, "--include-canonical-books", help="Also include data/books and data/raw-books."),
    path: list[Path] | None = typer.Option(None, "--path", "-p", help="Specific path to include. Can be used multiple times."),
    reason: str | None = typer.Option(None, "--reason", help="Reason for the restore point."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Create a restore point."""
    import json as json_lib

    point = create_restore_point(
        label=label,
        paths=path,
        include_canonical_books=include_canonical_books,
        reason=reason,
    )
    payload = restore_point_as_dict(point)
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"ID: {point.restore_point_id}\n"
            f"Archive: {point.archive_path}\n"
            f"Included paths: {len(point.included_paths)}\n"
            f"Canonical books: {'yes' if point.include_canonical_books else 'no'}",
            title="Restore point created",
            expand=False,
        )
    )


@restore_points_app.command("show")
def restore_points_show_command(
    restore_point_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show restore point details."""
    import json as json_lib

    point = show_restore_point(restore_point_id)
    if json_output:
        console.print(json_lib.dumps(point, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"ID: {point['restore_point_id']}\n"
            f"Label: {point['label']}\n"
            f"Created: {point['created_at']}\n"
            f"Archive exists: {'yes' if point['archive_exists'] else 'no'}\n"
            f"Members: {len(point['archive_members'])}",
            title="Restore point",
            expand=False,
        )
    )
    for member in point["archive_members"][:200]:
        console.print(f"- {member}")


@app.command("rollback")
def rollback_command(
    restore_point_id: str | None = typer.Argument(None, help="Restore point ID."),
    last: bool = typer.Option(False, "--last", help="Roll back to the most recent restore point."),
    audit_id: str | None = typer.Option(None, "--audit-id", help="Find restore point from matching audit record text/id."),
    include_canonical_books: bool = typer.Option(False, "--include-canonical-books", help="Allow restoring data/books and data/raw-books."),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview by default. Use --execute to restore files."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Roll back to a restore point."""
    import json as json_lib

    if audit_id:
        point = restore_point_from_audit_id(audit_id)
        restore_point_id = point["restore_point_id"]
    if not last and not restore_point_id:
        console.print("[red]Provide a restore point ID, --last, or --audit-id.[/red]")
        raise typer.Exit(code=1)

    result = rollback_restore_point(
        restore_point_id=restore_point_id,
        last=last,
        dry_run=dry_run,
        include_canonical_books=include_canonical_books,
    )

    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Restore point: {result['restore_point_id']}\n"
            f"Mode: {'dry-run' if result['dry_run'] else 'execute'}\n"
            f"Status: {result['status']}\n"
            f"Archive: {result['archive_path']}",
            title="Rollback",
            expand=False,
        )
    )
    if result.get("blocked"):
        console.print("[yellow]Blocked paths[/yellow]")
        for item in result["blocked"]:
            console.print(f"- {item}")
    for item in (result.get("would_restore") or result.get("restored") or [])[:200]:
        console.print(f"- {item}")
    if dry_run:
        console.print("\n[yellow]Dry run only. Re-run with --execute to restore files.[/yellow]")


@audit_app.command("tail")
def audit_tail_command(
    limit: int = typer.Option(50, "--limit", "-n", help="Number of records to show."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show recent audit log entries."""
    import json as json_lib

    records = tail_audit(limit=limit)
    if json_output:
        console.print(json_lib.dumps(records, indent=2, ensure_ascii=False))
        return
    _print_audit_table(records, title=f"Last {len(records)} audit record(s)")


@audit_app.command("search")
def audit_search_command(
    query: str,
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum records to show."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Search audit log entries."""
    import json as json_lib

    records = search_audit(query, limit=limit)
    if json_output:
        console.print(json_lib.dumps(records, indent=2, ensure_ascii=False))
        return
    _print_audit_table(records, title=f"Audit search: {query}")


@audit_app.command("export")
def audit_export_command(
    format: str = typer.Option("jsonl", "--format", "-f", help="Export format: jsonl or json."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional output file."),
):
    """Export the audit log."""
    text = export_audit(format=format)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Exported audit log:[/green] {output}")
        return
    console.print(text)


@app.command("clean-derived")
def clean_derived_command(
    summaries: bool = typer.Option(False, "--summaries", help="Clean generated book/chapter summaries."),
    concepts: bool = typer.Option(False, "--concepts", help="Clean generated concept files and concept index."),
    graphs: bool = typer.Option(False, "--graphs", help="Clean generated graph files."),
    index: bool = typer.Option(False, "--index", help="Clean generated LanceDB index."),
    notes: bool = typer.Option(False, "--notes", help="Clean generated Obsidian-friendly notes."),
    exports: bool = typer.Option(False, "--exports", help="Clean generated exports."),
    review: bool = typer.Option(False, "--review", help="Also clean review queues. Never included by --all."),
    all_targets: bool = typer.Option(False, "--all", help="Clean all generated artefacts except review queues unless --review is also supplied."),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview by default. Use --execute to delete selected derived artefacts."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Safely clean generated/derived BookMem artefacts."""
    import json as json_lib

    result = clean_derived(
        summaries=summaries,
        concepts=concepts,
        graphs=graphs,
        index=index,
        notes=notes,
        exports=exports,
        review=review,
        all_targets=all_targets,
        dry_run=dry_run,
    )
    payload = clean_result_as_dict(result)

    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    mode = "DRY RUN" if result.dry_run else "EXECUTE"
    console.print(
        Panel(
            f"Mode: {mode}\n"
            f"Candidates: {len(result.candidates)}\n"
            f"Deleted: {len(result.deleted)}\n"
            f"Skipped: {len(result.skipped)}",
            title="Clean derived artefacts",
            expand=False,
        )
    )

    table_out = Table(title="Derived clean candidates")
    table_out.add_column("Target")
    table_out.add_column("Path")
    table_out.add_column("Exists")
    table_out.add_column("Protected")
    table_out.add_column("Type")
    table_out.add_column("Size")

    for candidate in result.candidates:
        table_out.add_row(
            candidate.target,
            candidate.path,
            "yes" if candidate.exists else "no",
            "yes" if candidate.protected else "no",
            candidate.type,
            str(candidate.size_bytes),
        )
    console.print(table_out)

    if result.warnings:
        console.print("\n[yellow]Warnings[/yellow]")
        for warning in result.warnings:
            console.print(f"- {warning}")

    if result.dry_run:
        console.print("\n[yellow]Dry run only. Re-run with --execute to delete selected derived artefacts.[/yellow]")
    elif result.deleted:
        console.print("\n[green]Deleted derived artefacts.[/green]")


@migrations_app.command("status")
def migrations_status_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show migration status."""
    import json as json_lib

    status = migration_status()
    if json_output:
        console.print(json_lib.dumps(status, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Total: {status['total']}\n"
            f"Applied: {status['applied']}\n"
            f"Pending: {status['pending']}\n"
            f"State: {status['state_path']}",
            title="Migration status",
            expand=False,
        )
    )

    table_out = Table(title="Migrations")
    table_out.add_column("ID")
    table_out.add_column("Applied")
    table_out.add_column("Applied at")
    table_out.add_column("Description")
    table_out.add_column("Path")
    for item in status["migrations"]:
        table_out.add_row(
            item["id"],
            "yes" if item["applied"] else "no",
            str(item.get("applied_at") or ""),
            item.get("description") or "",
            item.get("path") or "",
        )
    console.print(table_out)


@migrations_app.command("apply")
def migrations_apply_command(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show pending migrations without applying them."),
    target: str | None = typer.Option(None, "--target", help="Apply migrations up to and including this migration ID."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Apply pending migrations."""
    import json as json_lib
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

    if json_output:
        result = apply_migrations(dry_run=dry_run, target=target)
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    plan = apply_migrations(dry_run=True, target=target)
    pending = plan.get("pending_to_apply", [])

    if not pending:
        console.print("[green]No pending migrations.[/green]")
        return

    if dry_run:
        table_out = Table(title="Pending migrations")
        table_out.add_column("ID")
        table_out.add_column("Description")
        table_out.add_column("Path")
        for item in pending:
            table_out.add_row(item["id"], item.get("description", ""), item.get("path", ""))
        console.print(table_out)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Applying migrations", total=len(pending))
        result = apply_migrations(dry_run=False, target=target)
        for item in result.get("applied", []):
            progress.update(task, description=f"Applied {item['id']}")
            progress.advance(task)

    console.print(f"[green]Applied {len(result.get('applied', []))} migration(s).[/green]")


@migrations_app.command("create")
def migrations_create_command(
    name: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Create a new migration file stub."""
    import json as json_lib

    result = create_migration(name)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"ID: {result['id']}\n"
            f"Path: {result['path']}\n"
            f"Description: {result['description']}",
            title="Migration created",
            expand=False,
        )
    )


@setup_app.command("presets")
def setup_presets_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List first-run setup presets."""
    import json as json_lib

    presets = presets_as_dict()
    if json_output:
        console.print(json_lib.dumps(presets, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Setup presets")
    table_out.add_column("Name")
    table_out.add_column("Label")
    table_out.add_column("Description")
    for preset in presets:
        table_out.add_row(preset["name"], preset["label"], preset["description"])
    console.print(table_out)


@setup_app.command("status")
def setup_status_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show first-run setup status."""
    import json as json_lib

    status = setup_status()
    if json_output:
        console.print(json_lib.dumps(status, indent=2, ensure_ascii=False))
        return

    doctor = status["doctor"]
    idx = status["index_status"]
    console.print(
        Panel(
            f"Doctor: {doctor['status']}\n"
            f"Index stale: {'yes' if idx['stale'] else 'no'}\n"
            f"Books: {doctor['counts'].get('books', 0)}\n"
            f"Chunks: {doctor['counts'].get('indexed_chunks', 0)}\n"
            f"Review items: {doctor['counts'].get('review_items', 0)}",
            title="Setup status",
            expand=False,
        )
    )


@setup_app.command("plan")
def setup_plan_command(
    preset: str = typer.Argument("balanced", help="Preset name."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show the setup steps for a preset."""
    import json as json_lib

    presets = load_setup_presets()
    if preset not in presets:
        console.print(f"[red]Unknown preset: {preset}[/red]")
        raise typer.Exit(code=1)

    steps = setup_steps_for_preset(presets[preset])
    payload = [step.__dict__ for step in steps]
    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Setup plan: {preset}")
    table_out.add_column("Step")
    table_out.add_column("Enabled")
    table_out.add_column("Long")
    table_out.add_column("Command")
    table_out.add_column("Description")
    for step in steps:
        table_out.add_row(
            step.label,
            "yes" if step.enabled else "no",
            "yes" if step.long_running else "no",
            " ".join(step.command or []),
            step.description or "",
        )
    console.print(table_out)


@setup_app.command("run")
def setup_run_command(
    preset: str = typer.Argument("balanced", help="Preset name."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned work without running."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Run a setup preset from the command line."""
    import json as json_lib
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

    messages = []

    def callback(step_id: str, message: str):
        messages.append({"step": step_id, "message": message})

    if json_output:
        result = run_setup_preset(preset, dry_run=dry_run, status_callback=callback)
        result["messages"] = messages
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    presets = load_setup_presets()
    if preset not in presets:
        console.print(f"[red]Unknown preset: {preset}[/red]")
        raise typer.Exit(code=1)
    steps = [s for s in setup_steps_for_preset(presets[preset]) if s.enabled]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task(f"Setup preset: {preset}", total=len(steps))

        def rich_callback(step_id: str, message: str):
            progress.update(overall, description=message)

        result = run_setup_preset(preset, dry_run=dry_run, status_callback=rich_callback)
        for _ in steps:
            progress.advance(overall)

    console.print(Panel(f"Preset: {preset}\nDry run: {'yes' if dry_run else 'no'}\nSteps: {len(result['steps'])}", title="Setup complete", expand=False))

    failed = [step for step in result["steps"] if step["status"] == "failed"]
    if failed:
        console.print("[red]Some setup steps failed.[/red]")
        for item in failed:
            console.print(f"- {item['step']['label']}: {item['result']}")
        raise typer.Exit(code=1)


@eval_app.command("queries")
def eval_queries_command(
    query_file: Path = typer.Option(Path("eval/queries.yaml"), "--query-file", "-q"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List configured retrieval evaluation queries."""
    import json as json_lib

    queries = load_eval_queries(query_file)
    if json_output:
        console.print(json_lib.dumps(eval_queries_as_dict(queries), indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Evaluation queries: {query_file}")
    table_out.add_column("ID")
    table_out.add_column("Query")
    table_out.add_column("Expected books")
    table_out.add_column("Expected topics")
    for item in queries:
        table_out.add_row(
            item.id,
            item.query,
            ", ".join(item.expected_books),
            ", ".join(item.expected_topics),
        )
    console.print(table_out)


@eval_app.command("retrieval")
def eval_retrieval_command(
    query_file: Path = typer.Option(Path("eval/queries.yaml"), "--query-file", "-q"),
    k: int = typer.Option(5, "--k", help="Recall@K cutoff."),
    limit: int | None = typer.Option(None, "--limit", help="Search result limit. Defaults to max(k, 10)."),
    no_route: bool = typer.Option(False, "--no-route", help="Disable routed search during evaluation."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Evaluate retrieval quality against expected books/topics."""
    import json as json_lib

    report = evaluate_retrieval(
        query_file=query_file,
        k=k,
        limit=limit,
        use_route=not no_route,
    )

    if json_output:
        console.print(json_lib.dumps(report, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Queries: {report['query_count']}\n"
            f"Recall@{report['k']}: {report['recall_at_k']}\n"
            f"MRR: {report['mrr']}\n"
            f"Failed queries: {report['failed_count']}",
            title="Retrieval evaluation",
            expand=False,
        )
    )

    table_out = Table(title="Per-query retrieval results")
    table_out.add_column("ID")
    table_out.add_column("Query")
    table_out.add_column(f"Recall@{report['k']}", justify="right")
    table_out.add_column("RR", justify="right")
    table_out.add_column("Top result")
    table_out.add_column("Errors")

    for item in report["results"]:
        top = item.get("top_results", [{}])[0] if item.get("top_results") else {}
        table_out.add_row(
            str(item.get("id")),
            str(item.get("query")),
            str(item.get("recall_at_k")),
            str(round(item.get("reciprocal_rank", 0), 4)),
            str(top.get("title") or ""),
            "; ".join(item.get("errors") or []),
        )

    console.print(table_out)

    if report["failed_queries"]:
        console.print("\n[bold]Failed queries[/bold]")
        for failed in report["failed_queries"]:
            console.print(f"- {failed['id']}: {failed['query']}")


@embeddings_app.command("info")
def embeddings_info_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show current runtime and stored index embedding configuration."""
    import json as json_lib

    info = current_embedding_info()
    if json_output:
        console.print(json_lib.dumps(info, indent=2, ensure_ascii=False))
        return

    runtime = info["current_runtime"]
    stored = info["stored_index"]
    manifest_embedding = info.get("manifest_embedding") or {}

    table_out = Table(title="Embedding info")
    table_out.add_column("Field")
    table_out.add_column("Runtime")
    table_out.add_column("Stored index")
    table_out.add_column("Manifest embedding")

    for key in ("provider", "model", "dimensions", "normalised"):
        table_out.add_row(
            key,
            str(runtime.get(key)),
            str(stored.get(key)),
            str(manifest_embedding.get(key)),
        )

    console.print(table_out)


@embeddings_app.command("models")
def embeddings_models_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    validate: bool = typer.Option(False, "--validate", help="Validate configured embedding profiles."),
):
    """List configured embedding model profiles."""
    import json as json_lib

    if validate:
        issues = validate_embedding_models()
        if issues:
            if json_output:
                console.print(json_lib.dumps({"issues": issues}, indent=2, ensure_ascii=False))
            else:
                table_out = Table(title="Embedding model validation issues")
                table_out.add_column("Model")
                table_out.add_column("Issue")
                table_out.add_column("Message")
                for issue in issues:
                    table_out.add_row(str(issue.get("model", "")), str(issue.get("issue", "")), str(issue.get("message", "")))
                console.print(table_out)
            raise typer.Exit(code=1)
        if not json_output:
            console.print("[green]Embedding model profiles validated successfully[/green]")

    profiles = embedding_profiles()
    if json_output:
        console.print(json_lib.dumps(profiles_as_dict(profiles), indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Embedding model profiles")
    table_out.add_column("Name")
    table_out.add_column("Provider")
    table_out.add_column("Model")
    table_out.add_column("Dimensions")
    table_out.add_column("Normalised")
    table_out.add_column("Notes")

    for profile in profiles:
        table_out.add_row(
            profile.name,
            profile.provider,
            profile.model,
            str(profile.dimensions or ""),
            "yes" if profile.normalised else "no",
            profile.notes or "",
        )

    console.print(table_out)


@embeddings_app.command("benchmark")
def embeddings_benchmark_command(
    model: str | None = typer.Option(None, "--model", "-m", help="Profile name or raw sentence-transformers model name."),
    runs: int = typer.Option(3, "--runs", "-r", help="Number of benchmark runs."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Benchmark embedding generation for a configured model."""
    import json as json_lib

    result = benchmark_embeddings(profile_name=model, runs=runs)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    profile = result["profile"]
    console.print(
        Panel(
            f"Model: {profile['model']}\n"
            f"Provider: {profile['provider']}\n"
            f"Dimensions: {result['dimensions']}\n"
            f"Runs: {result['runs']}\n"
            f"Texts: {result['texts']}\n"
            f"Mean seconds: {result['seconds_mean']}\n"
            f"Texts/sec mean: {result['texts_per_second_mean']}",
            title="Embedding benchmark",
            expand=False,
        )
    )


@embeddings_app.command("reindex")
def embeddings_reindex_command(
    model: str = typer.Option(..., "--model", "-m", help="Profile name or raw sentence-transformers model name."),
    changed_only: bool = typer.Option(False, "--changed-only", help="Run changed-only ingest instead of reset."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned reindex without running."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Reindex using a selected embedding model."""
    import json as json_lib

    result = reindex_with_embedding_model(
        profile_name=model,
        reset=not changed_only,
        changed_only=changed_only,
        dry_run=dry_run,
    )

    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    profile = result["profile"]
    console.print(
        Panel(
            f"Model: {profile['model']}\n"
            f"Provider: {profile['provider']}\n"
            f"Dimensions: {profile.get('dimensions')}\n"
            f"Normalised: {'yes' if profile.get('normalised') else 'no'}\n"
            f"Dry run: {'yes' if dry_run else 'no'}\n"
            f"Mode: {'changed-only' if changed_only else 'reset'}",
            title="Embedding reindex",
            expand=False,
        )
    )


@app.command("index-status")
def index_status_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    update_manifest: bool = typer.Option(False, "--update-manifest", help="Record the current index fingerprint in the manifest."),
):
    """Check whether the LanceDB index is stale compared with current code/config."""
    import json as json_lib

    if update_manifest:
        update_manifest_index_metadata()

    report = index_status()

    if json_output:
        console.print(json_lib.dumps(report, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Index stale: {'yes' if report['stale'] else 'no'}\n"
            f"Rows: {report['table'].get('row_count', 0)}\n"
            f"LanceDB readable: {'yes' if report['table'].get('lancedb_readable') else 'no'}\n"
            f"Table exists: {'yes' if report['table'].get('table_exists') else 'no'}",
            title="Index status",
            expand=False,
        )
    )

    current = report.get("current", {})
    stored = report.get("stored", {})

    table_out = Table(title="Index fingerprint")
    table_out.add_column("Field")
    table_out.add_column("Stored")
    table_out.add_column("Current")

    for key in (
        "index_schema_version",
        "chunker_version",
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "cleaner_version",
        "cleaning_profile",
        "taxonomy_version",
    ):
        table_out.add_row(key, str(stored.get(key)), str(current.get(key)))

    console.print(table_out)

    if report.get("reasons"):
        console.print("\n[bold]Reason[/bold]")
        for reason in report["reasons"]:
            console.print(f"- {reason}")
    else:
        console.print("\n[green]Index fingerprint matches current code/config.[/green]")


@app.command("extract-concepts")
def extract_concepts_command(
    book: Path,
    limit: int = typer.Option(30, "--limit", "-n", help="Maximum concepts to extract from the book."),
    write: bool = typer.Option(True, "--write/--dry-run", help="Write concept files. Use --dry-run to preview only."),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Extract reusable models, frameworks and concepts from one book."""
    import json as json_lib

    result = extract_concepts_from_book(book, limit=limit, write=write, overwrite=overwrite)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Concepts extracted: {result['title']}")
    table_out.add_column("Name")
    table_out.add_column("Type")
    table_out.add_column("Confidence", justify="right")
    table_out.add_column("Source chunks", justify="right")
    for concept in result.get("concepts", []):
        table_out.add_row(
            str(concept.get("name") or ""),
            str(concept.get("type") or ""),
            str(concept.get("confidence") or ""),
            str(len(concept.get("source_chunks") or [])),
        )
    console.print(table_out)
    console.print(f"[green]{len(result.get('concepts', []))} concept(s) extracted[/green]")


@concepts_app.command("extract-books")
def concepts_extract_books_command(
    books_dir: Path = typer.Argument(Path("data/books")),
    limit_per_book: int = typer.Option(30, "--limit-per-book", "-n"),
    write: bool = typer.Option(True, "--write/--dry-run"),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite"),
):
    """Extract concepts for all books under a directory."""
    results = extract_concepts_from_books(
        books_dir,
        limit_per_book=limit_per_book,
        write=write,
        overwrite=overwrite,
    )
    console.print(f"[green]{len(results)} book(s) processed[/green]")


@concepts_app.command("rebuild-index")
def concepts_rebuild_index_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Rebuild the concept search index from concept YAML files."""
    import json as json_lib

    result = rebuild_concept_index()
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print(f"[green]{result['concept_count']} concept(s) indexed[/green]")


@concepts_app.command("search")
def concepts_search_command(
    query: str,
    class_code: str | None = typer.Option(None, "--class", "class_filter", help="Filter by BMDC class."),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Search extracted concepts."""
    import json as json_lib

    results = search_concepts(query, class_code=class_filter, limit=limit)
    if json_output:
        console.print(json_lib.dumps(results, indent=2, ensure_ascii=False))
        return

    table_out = Table(title=f"Concept search: {query}")
    table_out.add_column("Name")
    table_out.add_column("Type")
    table_out.add_column("Book")
    table_out.add_column("Class")
    table_out.add_column("Score", justify="right")
    table_out.add_column("Description")
    for concept in results:
        table_out.add_row(
            str(concept.get("name") or ""),
            str(concept.get("type") or ""),
            str(concept.get("title") or ""),
            str(concept.get("primary_class") or ""),
            str(concept.get("score") or ""),
            str(concept.get("description") or "")[:120],
        )
    console.print(table_out)


@concepts_app.command("list")
def concepts_list_command(
    class_code: str | None = typer.Option(None, "--class", "class_filter", help="Filter by BMDC class."),
    concept_type: str | None = typer.Option(None, "--type", help="Filter by concept type."),
    limit: int = typer.Option(100, "--limit", "-n"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List extracted concepts."""
    import json as json_lib

    results = list_concepts(class_code=class_filter, concept_type=concept_type, limit=limit)
    if json_output:
        console.print(json_lib.dumps(results, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Concepts")
    table_out.add_column("Name")
    table_out.add_column("Type")
    table_out.add_column("Book")
    table_out.add_column("Class")
    table_out.add_column("Useful for")
    for concept in results:
        table_out.add_row(
            str(concept.get("name") or ""),
            str(concept.get("type") or ""),
            str(concept.get("title") or ""),
            str(concept.get("primary_class") or ""),
            ", ".join(concept.get("useful_for") or [])[:80],
        )
    console.print(table_out)


@prompts_app.command("list")
def prompts_list_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List available prompt pack assets."""
    import json as json_lib

    prompts = list_prompts()
    if json_output:
        console.print(json_lib.dumps(prompt_assets_as_dict(prompts), indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Prompt packs")
    table_out.add_column("Name")
    table_out.add_column("Title")
    table_out.add_column("Description")
    table_out.add_column("Path")

    for prompt in prompts:
        table_out.add_row(prompt.name, prompt.title, prompt.description, prompt.path)

    console.print(table_out)


@prompts_app.command("show")
def prompts_show_command(
    name: str,
):
    """Show a prompt pack asset."""
    console.print(show_prompt(name))


@app.command("answer-pack")
def answer_pack_command(
    query: str,
    limit: int = typer.Option(6, "--limit", "-n", help="Number of top passages/books to collect."),
    context: int = typer.Option(1, "--context", "-c", help="Neighbouring chunks to include around top passages."),
    no_summaries: bool = typer.Option(False, "--no-summaries", help="Skip summary search."),
    no_text: bool = typer.Option(False, "--no-text", help="Return excerpts/metadata rather than full text."),
    rebuild_graph: bool = typer.Option(False, "--rebuild-graph", help="Rebuild book relationship graph before lookup."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Build a structured evidence bundle for answering from the corpus."""
    import json as json_lib

    pack = build_answer_pack(
        query=query,
        limit=limit,
        context=context,
        summaries_first=not no_summaries,
        include_text=not no_text,
        rebuild_graph=rebuild_graph,
    )

    if json_output:
        console.print(json_lib.dumps(pack, indent=2, ensure_ascii=False))
        return

    console.print(Panel(
        f"[bold]Query:[/bold] {pack['query']}\n"
        f"[bold]Route:[/bold] {pack['route'].get('reason', '')}\n"
        f"[bold]Confidence:[/bold] {pack['route'].get('confidence', '')}\n"
        f"[bold]Aliases:[/bold] {', '.join(pack['route'].get('aliases', []) or [])}\n"
        f"[bold]Classes:[/bold] {', '.join(str(x) for x in (pack['route'].get('class_codes', []) or []))}",
        title="Answer pack",
        expand=False,
    ))

    books_table = Table(title="Relevant books")
    books_table.add_column("#", justify="right")
    books_table.add_column("Title")
    books_table.add_column("Author")
    books_table.add_column("Class")
    for index, book in enumerate(pack.get("relevant_books", []), start=1):
        books_table.add_row(
            str(index),
            str(book.get("title") or ""),
            str(book.get("author") or ""),
            str(book.get("primary_class") or ""),
        )
    console.print(books_table)

    passages_table = Table(title="Top passages")
    passages_table.add_column("#", justify="right")
    passages_table.add_column("Book")
    passages_table.add_column("Location")
    passages_table.add_column("Citation")
    for index, passage in enumerate(pack.get("top_passages", []), start=1):
        passages_table.add_row(
            str(index),
            str(passage.get("title") or ""),
            str(passage.get("heading_path") or passage.get("chapter_title") or ""),
            str(passage.get("citation") or ""),
        )
    console.print(passages_table)

    synthesis = pack.get("suggested_synthesis", {})
    console.print("\n[bold]Suggested synthesis approach[/bold]")
    for point in synthesis.get("possible_synthesis_points", []):
        console.print(f"- {point}")

    if synthesis.get("recurring_themes"):
        console.print("\n[bold]Recurring themes[/bold]")
        for theme in synthesis.get("recurring_themes", [])[:10]:
            console.print(f"- {theme}")

    if pack.get("citations"):
        console.print("\n[bold]Citations[/bold]")
        for citation in pack["citations"][:15]:
            console.print(f"- {citation}")

    if pack.get("errors"):
        console.print("\n[yellow]Warnings[/yellow]")
        for error in pack["errors"]:
            console.print(f"- {error}")


@app.command("build-graph")
def build_graph_command(
    books_dir: Path = typer.Option(Path("data/books"), "--books-dir", help="Canonical books directory."),
    output: Path = typer.Option(Path("data/graphs/book_graph.json"), "--output", "-o"),
    min_score: float = typer.Option(0.2, "--min-score", help="Minimum relationship score to include."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Build the derived book-to-book relationship graph."""
    import json as json_lib

    graph = build_book_graph(books_dir=books_dir, output_path=output, min_score=min_score)

    if json_output:
        console.print(json_lib.dumps(graph, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Output: {output}\n"
            f"Books: {graph['node_count']}\n"
            f"Relationships: {graph['edge_count']}\n"
            f"Minimum score: {min_score}",
            title="Book graph built",
            expand=False,
        )
    )


@app.command("related")
def related_command(
    query: str | None = typer.Argument(None, help="Book title, author, ISBN, work id or broad topic."),
    topic: str | None = typer.Option(None, "--topic", help="Find books related to a topic."),
    limit: int = typer.Option(10, "--limit", "-n"),
    graph_path: Path = typer.Option(Path("data/graphs/book_graph.json"), "--graph"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild graph before querying."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Find books related to a book or topic."""
    import json as json_lib

    if rebuild or not graph_path.exists():
        build_book_graph(output_path=graph_path)

    result = related_books(query=query, topic=topic, limit=limit, graph_path=graph_path)

    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    label = topic or query or "(none)"
    table_out = Table(title=f"Related books: {label}")
    table_out.add_column("#", justify="right")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Score", justify="right")
    table_out.add_column("Reason")

    for index, item in enumerate(result.get("related", []), start=1):
        node = item["node"]
        table_out.add_row(
            str(index),
            str(node.get("title") or ""),
            str(node.get("author") or ""),
            str(item.get("score") or ""),
            "; ".join(item.get("reasons") or []),
        )

    console.print(table_out)
    console.print(f"[green]{result.get('count', 0)} related book(s)[/green]")


@app.command("editions")
def editions_command(
    query: str | None = typer.Argument(None, help="Optional title, author, ISBN or work query."),
    books_dir: Path = typer.Option(Path("data/books"), "--books-dir", help="Canonical books directory."),
    ensure: bool = typer.Option(False, "--ensure", help="Infer work/edition fields before listing."),
    write: bool = typer.Option(False, "--write", help="Write inferred work/edition fields to matching books."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing work/edition fields when writing."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List works and editions in the BookMem library."""
    import json as json_lib

    records = list_editions(books_dir, query=query, ensure=ensure or write)
    if write:
        for record in records:
            ensure_work_edition_frontmatter(Path(record.path), write=True, overwrite=overwrite)
        records = list_editions(books_dir, query=query, ensure=True)

    if json_output:
        console.print(json_lib.dumps(edition_records_as_dict(records), indent=2, ensure_ascii=False))
        return

    grouped = group_editions(records)
    table_out = Table(title="BookMem editions")
    table_out.add_column("Work")
    table_out.add_column("Title")
    table_out.add_column("Author")
    table_out.add_column("Edition")
    table_out.add_column("Year")
    table_out.add_column("ISBN")
    table_out.add_column("Path")

    for work_id, work_records in sorted(grouped.items()):
        for record in work_records:
            table_out.add_row(
                record.canonical_title,
                record.title,
                record.author or "",
                record.edition_label or (str(record.edition_number) if record.edition_number else ""),
                str(record.edition_year or ""),
                record.isbn or "",
                record.path,
            )

    console.print(table_out)
    console.print(f"[green]{len(records)} edition record(s), {len(grouped)} work(s)[/green]")


@app.command("enrich-openlibrary")
def enrich_openlibrary_command(
    book: Path,
    write: bool = typer.Option(False, "--write", help="Write metadata updates to frontmatter."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing unreviewed fields."),
    timeout: int = typer.Option(20, "--timeout"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Enrich one book from Open Library metadata."""
    import json as json_lib

    result = enrich_with_openlibrary(book, write=write, overwrite=overwrite, timeout=timeout)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Provider: Open Library\n"
            f"Matched: {'yes' if result.get('matched') else 'no'}\n"
            f"Changed fields: {', '.join(result.get('changed', [])) or '(none)'}\n"
            f"Wrote: {'yes' if write else 'no'}",
            title="Metadata enrichment",
            expand=False,
        )
    )


@app.command("enrich-google-books")
def enrich_google_books_command(
    book: Path,
    write: bool = typer.Option(False, "--write", help="Write metadata updates to frontmatter."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing unreviewed fields."),
    timeout: int = typer.Option(20, "--timeout"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Enrich one book from Google Books metadata."""
    import json as json_lib

    result = enrich_with_google_books(book, write=write, overwrite=overwrite, timeout=timeout)
    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Provider: Google Books\n"
            f"Matched: {'yes' if result.get('matched') else 'no'}\n"
            f"Changed fields: {', '.join(result.get('changed', [])) or '(none)'}\n"
            f"Wrote: {'yes' if write else 'no'}",
            title="Metadata enrichment",
            expand=False,
        )
    )


@app.command("enrich-metadata")
def enrich_metadata_command(
    book: Path,
    providers: str = typer.Option("loc,openlibrary,google", "--providers", help="Comma-separated providers: loc,openlibrary,google"),
    write: bool = typer.Option(False, "--write", help="Write metadata updates to frontmatter."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing unreviewed fields."),
    overwrite_classification: bool = typer.Option(False, "--overwrite-classification", help="Allow LoC enrichment to replace classification."),
    timeout: int = typer.Option(20, "--timeout"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Run metadata enrichment providers in priority order."""
    import json as json_lib

    provider_list = [item.strip() for item in providers.split(",") if item.strip()]
    result = enrich_metadata(
        book,
        providers=provider_list,
        write=write,
        overwrite=overwrite,
        overwrite_classification=overwrite_classification,
        timeout=timeout,
    )

    if json_output:
        console.print(json_lib.dumps(result, indent=2, ensure_ascii=False))
        return

    table_out = Table(title="Metadata enrichment")
    table_out.add_column("Provider")
    table_out.add_column("Matched")
    table_out.add_column("Changed / Result")
    for item in result["results"]:
        provider = str(item.get("provider", ""))
        if "error" in item:
            table_out.add_row(provider, "error", str(item["error"]))
            continue
        if provider == "library_of_congress":
            table_out.add_row(provider, "", str(item.get("result", "")))
            continue
        table_out.add_row(
            provider,
            "yes" if item.get("matched") else "no",
            ", ".join(item.get("changed", [])) or "(none)",
        )
    console.print(table_out)
    console.print(f"[green]Wrote: {'yes' if write else 'no'}[/green]")


@app.command("tui")
def tui_command():
    """Run the interactive BookMem terminal UI."""
    run_tui()


@app.command("ui")
def ui_command(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind"),
    port: int = typer.Option(8787, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable Uvicorn reload mode"),
):
    """Run the local BookMem web UI."""
    run_ui(host=host, port=port, reload=reload)


@app.command("backup")
def backup_command(
    output: Path = typer.Option(..., "--output", "-o", help="Output .tar.gz backup path."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing backup file."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Create a BookMem backup archive."""
    import json as json_lib

    result = create_backup(output_path=output, overwrite=overwrite)
    payload = result_as_dict(result)

    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"Output: {result.output_path}\n"
            f"Files: {result.file_count}\n\n"
            f"Included roots:\n"
            f"- data/books\n"
            f"- data/summaries\n"
            f"- data/notes\n"
            f"- data/manifests\n"
            f"- data/review\n"
            f"- config\n"
            f"- project metadata/docs\n\n"
            f"Excluded: data/lancedb, exports, backups, .venv, caches",
            title="Backup created",
            expand=False,
        )
    )


@app.command("restore")
def restore_command(
    archive: Path,
    target_root: Path = typer.Option(Path("."), "--target-root", help="Directory to restore into."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be restored without writing files."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Restore a BookMem backup archive."""
    import json as json_lib

    manifest = inspect_backup(archive)
    result = restore_backup(
        archive_path=archive,
        target_root=target_root,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    payload = result_as_dict(result)
    payload["manifest"] = manifest

    if json_output:
        console.print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return

    title = "Restore dry run" if dry_run else "Restore complete"
    console.print(
        Panel(
            f"Archive: {result.archive_path}\n"
            f"Target root: {target_root}\n"
            f"Restored/would restore: {result.restored_count}\n"
            f"Skipped existing files: {len(result.skipped_paths)}",
            title=title,
            expand=False,
        )
    )

    if result.skipped_paths:
        console.print("\n[yellow]Skipped existing files. Use --overwrite to replace them.[/yellow]")
        for path in result.skipped_paths[:20]:
            console.print(f"- {path}")
        if len(result.skipped_paths) > 20:
            console.print(f"... and {len(result.skipped_paths) - 20} more")


@app.command("doctor")
def doctor_command(
    fix: bool = typer.Option(False, "--fix", help="Apply safe automatic fixes for missing folders/placeholders."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Run a BookMem health check."""
    import json as json_lib

    report = run_doctor(fix=fix)

    if json_output:
        console.print(json_lib.dumps(report, indent=2, ensure_ascii=False))
        if report["status"] == "FAIL":
            raise typer.Exit(code=1)
        return

    console.print(f"[bold]BookMem {report['bookmem_version']}[/bold]")
    console.print(f"Python: {report['python_version']}\n")

    table_out = Table(title="Doctor")
    table_out.add_column("Check")
    table_out.add_column("Status")
    table_out.add_column("Message")
    table_out.add_column("Fixed")

    for check in report["checks"]:
        table_out.add_row(
            str(check["name"]),
            str(check["status"]),
            str(check["message"]),
            "yes" if check.get("fixed") else "",
        )

    console.print(table_out)

    counts = report["counts"]
    console.print(
        "\n"
        f"Books: {counts['books']}\n"
        f"Indexed chunks: {counts['indexed_chunks']}\n"
        f"Needs review: {counts['review_items']}\n"
        f"Unclassified: {counts['unclassified']}\n"
        f"Books without author: {counts['books_without_author']}"
    )

    console.print(f"\n[bold]Status:[/bold] {report['status']}")
    if report["reasons"]:
        console.print("[bold]Reason:[/bold]")
        for reason in report["reasons"]:
            console.print(f"- {reason}")

    if report["status"] == "FAIL":
        raise typer.Exit(code=1)


@app.command("clean")
def clean_command(
    source_path: Path,
    output: Path | None = typer.Option(None, "--output", "-o", help="Output path for cleaned Markdown."),
    in_place: bool = typer.Option(False, "--in-place", help="Overwrite the source file."),
    profile: str = typer.Option("epub_pandoc", "--profile", help="Cleaning profile to use."),
    keep_pre_content: bool = typer.Option(False, "--keep-pre-content", help="Do not drop cover/copyright/catalogue material before the first real content heading."),
):
    """Clean one Markdown book using a named cleaning profile."""
    report = clean_markdown_file(
        source_path=source_path,
        output_path=output,
        in_place=in_place,
        drop_front_matter=not keep_pre_content,
        profile=profile,
    )

    console.print(
        Panel(
            f"Profile: {report.profile}\n"
            f"Source: {report.source_path}\n"
            f"Output: {report.output_path or '(preview only)'}\n\n"
            f"Original chars: {report.original_chars}\n"
            f"Cleaned chars: {report.cleaned_chars}\n"
            f"Removed chars: {report.removed_chars}\n\n"
            f"Images removed: {report.removed_images}\n"
            f"Anchors removed: {report.removed_anchors}\n"
            f"Div fences removed: {report.removed_div_fences}\n"
            f"Raw HTML blocks removed: {report.removed_raw_html_blocks}\n"
            f"Span attributes removed: {report.removed_span_attributes}\n"
            f"Headings normalised: {report.normalised_headings}\n"
            f"Dropped pre-content matter: {'yes' if report.dropped_front_matter else 'no'}",
            title="Clean report",
            expand=False,
        )
    )


@app.command("clean-books")
def clean_books_command(
    source_dir: Path,
    output_dir: Path,
    profile: str = typer.Option("epub_pandoc", "--profile", help="Cleaning profile to use."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files in the output directory."),
    keep_pre_content: bool = typer.Option(False, "--keep-pre-content", help="Do not drop cover/copyright/catalogue material before the first real content heading."),
):
    """Clean all Markdown books from one directory into another."""
    files = sorted(source_dir.glob("**/*.md"))
    if not files:
        console.print(f"[yellow]No Markdown files found under {source_dir}[/yellow]")
        return

    table_out = Table(title="Cleaned books")
    table_out.add_column("Source")
    table_out.add_column("Output")
    table_out.add_column("Profile")
    table_out.add_column("Removed chars", justify="right")

    for source in files:
        rel = source.relative_to(source_dir)
        target = output_dir / rel
        if target.exists() and not overwrite:
            table_out.add_row(str(rel), "SKIP exists", profile, "")
            continue

        report = clean_markdown_file(
            source_path=source,
            output_path=target,
            profile=profile,
            drop_front_matter=not keep_pre_content,
        )
        table_out.add_row(str(rel), str(target), report.profile, str(report.removed_chars))

    console.print(table_out)


@app.command("cleaning-profiles")
def cleaning_profiles_command():
    """List configured cleaning profiles."""
    profiles = load_cleaning_profiles()
    table_out = Table(title="Cleaning profiles")
    table_out.add_column("Profile")
    table_out.add_column("Label")
    table_out.add_column("Description")

    for name, profile_def in sorted(profiles.items()):
        table_out.add_row(
            str(name),
            str(profile_def.get("label", "")) if isinstance(profile_def, dict) else "",
            str(profile_def.get("description", "")) if isinstance(profile_def, dict) else "",
        )

    console.print(table_out)


@app.command("validate-cleaning-profiles")
def validate_cleaning_profiles_command():
    """Validate configured cleaning profile YAML."""
    issues = validate_cleaning_profiles()
    if not issues:
        console.print("[green]Cleaning profiles validated successfully[/green]")
        return

    table_out = Table(title="Cleaning profile validation issues")
    table_out.add_column("Profile")
    table_out.add_column("Issue")
    table_out.add_column("Message")
    for issue in issues:
        table_out.add_row(str(issue.get("profile", "")), str(issue.get("issue", "")), str(issue.get("message", "")))
    console.print(table_out)
    raise typer.Exit(code=1)


@app.command("clean-check")
def clean_check_command(
    book: Path,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    fail_on_warning: bool = typer.Option(False, "--fail-on-warning", help="Exit non-zero on WARN or FAIL"),
    fail_on_fail: bool = typer.Option(False, "--fail-on-fail", help="Exit non-zero only on FAIL"),
):
    """Audit a cleaned Markdown book for remaining conversion clutter."""
    import json as json_lib

    report = assess_cleanliness(book)

    if json_output:
        console.print(json_lib.dumps(report, indent=2, ensure_ascii=False))
    else:
        summary = summarise_clean_check(report)
        table_out = Table(title=f"Clean check: {book}")
        table_out.add_column("Check")
        table_out.add_column("Value")
        table_out.add_column("Status")

        def add_count(label: str, key: str):
            table_out.add_row(label, str(report["checks"][key]), report["statuses"].get(key, ""))

        table_out.add_row("Overall", report["status"], report["status"])
        add_count("Images remaining", "images_remaining")
        add_count("HTML tags remaining", "html_tags_remaining")
        add_count("SVG/raw image tags remaining", "svg_or_raw_image_tags_remaining")
        add_count("Pandoc spans remaining", "pandoc_spans_remaining")
        add_count("Pandoc attributes remaining", "pandoc_attributes_remaining")
        add_count("Pandoc div fences remaining", "pandoc_div_fences_remaining")
        add_count("Empty anchors remaining", "empty_anchors_remaining")
        add_count("Raw HTML fences remaining", "raw_html_fences_remaining")
        add_count("EPUB artefact markers", "epub_artifact_markers")
        add_count("Footnote backlink artefacts", "footnote_backlink_artifacts")
        add_count("Non-breaking spaces", "non_breaking_spaces")
        add_count("Hard-wrap splits", "hard_wrap_splits")

        table_out.add_row(
            "Average paragraph length",
            str(report["paragraphs"]["average_paragraph_length"]),
            report["paragraphs"]["status"],
        )
        table_out.add_row(
            "Heading structure",
            f'{report["headings"]["heading_count"]} headings',
            report["headings"]["status"],
        )
        table_out.add_row(
            "ISBNs found",
            str(report["isbn"]["count"]),
            "OK" if report["isbn"]["count"] else "WARN",
        )
        table_out.add_row(
            "Frontmatter",
            "present" if report["frontmatter"]["present"] else "missing",
            report["frontmatter"]["status"],
        )

        console.print(table_out)

        if report["isbn"]["values"]:
            console.print("[cyan]ISBNs:[/cyan] " + ", ".join(report["isbn"]["values"]))

        if report["recommendations"]:
            console.print("\n[bold]Recommendations[/bold]")
            for recommendation in report["recommendations"]:
                console.print(f"- {recommendation}")

    if fail_on_warning and report["status"] in {"WARN", "FAIL"}:
        raise typer.Exit(code=1)
    if fail_on_fail and report["status"] == "FAIL":
        raise typer.Exit(code=1)


@notes_app.command("templates")
def notes_templates():
    """List available Obsidian note templates."""
    templates = load_note_templates()
    if not templates:
        console.print("[yellow]No note templates found[/yellow]")
        return

    table_out = Table(title="Obsidian note templates")
    table_out.add_column("Template")
    table_out.add_column("Label")
    table_out.add_column("Description")

    for key, template in sorted(templates.items()):
        table_out.add_row(
            str(key),
            str(template.get("label", "")) if isinstance(template, dict) else "",
            str(template.get("description", "")) if isinstance(template, dict) else "",
        )

    console.print(table_out)


@notes_app.command("generate")
def notes_generate(
    book: Path,
    note_type: str = typer.Option("book-note", "--type", "-t", help="book-note, summary or implementation-notes"),
    output_dir: Path = typer.Option(Path("data/notes"), "--output-dir", "-o"),
    write: bool = typer.Option(False, "--write", help="Write the generated note to disk"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing note"),
):
    """Generate an Obsidian-friendly note for one book."""
    target, content = generate_note(
        book_path=book,
        note_type=note_type,
        output_dir=output_dir,
        write=write,
        overwrite=overwrite,
    )

    if write:
        console.print(f"[green]Wrote note:[/green] {target}")
        return

    console.print(f"[cyan]Target:[/cyan] {target}\n")
    console.print(content)


@notes_app.command("generate-books")
def notes_generate_books(
    books_dir: Path = typer.Argument(Path("data/books")),
    note_type: str = typer.Option("book-note", "--type", "-t", help="book-note, summary or implementation-notes"),
    output_dir: Path = typer.Option(Path("data/notes"), "--output-dir", "-o"),
    write: bool = typer.Option(False, "--write", help="Write generated notes to disk"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing notes"),
):
    """Generate Obsidian-friendly notes for all books in a directory."""
    generated = generate_notes_for_directory(
        books_dir=books_dir,
        note_type=note_type,
        output_dir=output_dir,
        write=write,
        overwrite=overwrite,
    )

    table_out = Table(title="Generated Obsidian notes")
    table_out.add_column("Book")
    table_out.add_column("Note")
    for source, target in generated:
        table_out.add_row(str(source), str(target))
    console.print(table_out)
    console.print(f"[green]{len(generated)} note(s) generated[/green]")


@app.command("serve-mcp")
def serve_mcp():
    """Run the BookMem MCP server over stdio."""
    from .mcp_server import main as run_mcp_server

    run_mcp_server()




@app.command("serve")
def serve_api(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable Uvicorn reload mode"),
    require_api_key: bool = typer.Option(False, "--require-api-key", help="Require Authorization: Bearer <token> for API requests."),
    api_key: str | None = typer.Option(None, "--api-key", help="API key to require. Prefer BOOKMEM_API_KEY in production."),
):
    """Run the local BookMem FastAPI service."""
    import os
    import uvicorn

    if require_api_key:
        os.environ["BOOKMEM_API_REQUIRE_KEY"] = "true"
    if api_key:
        os.environ["BOOKMEM_API_KEY"] = api_key

    if os.getenv("BOOKMEM_API_REQUIRE_KEY", "").lower() in {"1", "true", "yes", "y", "on"} and not os.getenv("BOOKMEM_API_KEY"):
        console.print("[red]BOOKMEM_API_REQUIRE_KEY is enabled but BOOKMEM_API_KEY is not set.[/red]")
        raise typer.Exit(code=1)

    uvicorn.run("bookmem.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
