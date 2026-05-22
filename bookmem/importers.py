"""Import adapters for converting source book formats to raw Markdown.

Importers deliberately write to data/raw-books. The canonical BookMem
workflow remains:

    import -> raw Markdown -> clean -> frontmatter -> prepare -> ingest
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import html
import re
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from typing import Any


IMPORTER_VERSION = "0.1.0"


@dataclass
class ImportResult:
    source_path: str
    output_path: str
    importer: str
    title: str | None
    author: str | None
    item_count: int
    warning: str | None = None


INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]')
MULTI_SPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
BLOCK_TAG_RE = re.compile(r"</?(?:p|div|section|article|chapter|h[1-6]|li|br|blockquote|tr|table|ul|ol)\b[^>]*>", re.IGNORECASE)
HEADING_OPEN_RE = re.compile(r"<h([1-6])\b[^>]*>", re.IGNORECASE)
HEADING_CLOSE_RE = re.compile(r"</h[1-6]>", re.IGNORECASE)


def safe_filename_part(value: str | None, fallback: str = "Untitled") -> str:
    value = (value or fallback).strip()
    value = INVALID_FILENAME_CHARS_RE.sub(" ", value)
    value = value.replace("\n", " ").replace("\r", " ")
    value = MULTI_SPACE_RE.sub(" ", value).strip(" .")
    return value or fallback


def unique_path(path: Path, overwrite: bool = False) -> Path:
    if overwrite or not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def output_path_for_source(source_path: Path, output_dir: Path, title: str | None = None, author: str | None = None, overwrite: bool = False) -> Path:
    if title:
        parts = [safe_filename_part(title)]
        if author:
            parts.append(safe_filename_part(author))
        filename = " - ".join(parts) + ".md"
    else:
        filename = safe_filename_part(source_path.stem) + ".md"
    return unique_path(output_dir / filename, overwrite=overwrite)


def html_to_markdownish(raw_html: str) -> str:
    """Convert HTML/XHTML to simple Markdown-ish text using stdlib only."""
    text = SCRIPT_STYLE_RE.sub("", raw_html)

    def heading_open(match: re.Match[str]) -> str:
        level = int(match.group(1))
        return "\n\n" + ("#" * min(level, 6)) + " "

    text = HEADING_OPEN_RE.sub(heading_open, text)
    text = HEADING_CLOSE_RE.sub("\n\n", text)
    text = BLOCK_TAG_RE.sub("\n\n", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _epub_container_path(zf: zipfile.ZipFile) -> str:
    container_xml = zf.read("META-INF/container.xml")
    root = ET.fromstring(container_xml)
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile = root.find(".//c:rootfile", ns)
    if rootfile is None:
        raise ValueError("EPUB container does not declare a rootfile.")
    return rootfile.attrib["full-path"]


def _xml_text(root: ET.Element, tag_names: tuple[str, ...]) -> str | None:
    for element in root.iter():
        local = element.tag.split("}")[-1].lower()
        if local in tag_names and element.text:
            return element.text.strip()
    return None


def _epub_metadata(zf: zipfile.ZipFile, opf_path: str) -> tuple[str | None, str | None]:
    root = ET.fromstring(zf.read(opf_path))
    title = _xml_text(root, ("title",))
    creator = _xml_text(root, ("creator",))
    return title, creator


def _epub_spine_items(zf: zipfile.ZipFile, opf_path: str) -> list[str]:
    root = ET.fromstring(zf.read(opf_path))
    id_to_href: dict[str, str] = {}

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        media_type = item.attrib.get("media-type", "")
        if item_id and href and ("html" in media_type or href.lower().endswith((".xhtml", ".html", ".htm"))):
            id_to_href[item_id] = href

    spine_ids = []
    for itemref in root.iter():
        if itemref.tag.split("}")[-1].lower() == "itemref":
            idref = itemref.attrib.get("idref")
            if idref:
                spine_ids.append(idref)

    base = Path(opf_path).parent
    paths = []
    for idref in spine_ids:
        href = id_to_href.get(idref)
        if href:
            paths.append((base / href).as_posix())
    return paths


def import_epub(source_path: Path, output_dir: Path, overwrite: bool = False) -> ImportResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_path, "r") as zf:
        opf_path = _epub_container_path(zf)
        title, author = _epub_metadata(zf, opf_path)
        spine_paths = _epub_spine_items(zf, opf_path)

        sections: list[str] = []
        for spine_path in spine_paths:
            try:
                raw = zf.read(spine_path).decode("utf-8", errors="replace")
            except KeyError:
                continue
            converted = html_to_markdownish(raw)
            if converted:
                sections.append(converted)

    output_path = output_path_for_source(source_path, output_dir, title=title, author=author, overwrite=overwrite)
    frontmatter = {
        "bookmem_import": {
            "source_format": "epub",
            "source_path": str(source_path),
            "importer_version": IMPORTER_VERSION,
            "status": "raw_import",
        }
    }
    body = "\n\n".join(sections).strip() + "\n"
    output_path.write_text(_frontmatter_block(frontmatter) + "\n" + body, encoding="utf-8")

    return ImportResult(str(source_path), str(output_path), "epub", title, author, len(sections))


def import_html(source_path: Path, output_dir: Path, overwrite: bool = False) -> ImportResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    body = html_to_markdownish(raw)
    output_path = output_path_for_source(source_path, output_dir, overwrite=overwrite)
    frontmatter = {
        "bookmem_import": {
            "source_format": "html",
            "source_path": str(source_path),
            "importer_version": IMPORTER_VERSION,
            "status": "raw_import",
        }
    }
    output_path.write_text(_frontmatter_block(frontmatter) + "\n" + body.strip() + "\n", encoding="utf-8")
    return ImportResult(str(source_path), str(output_path), "html", None, None, 1)


def import_pdf(source_path: Path, output_dir: Path, overwrite: bool = False) -> ImportResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("PDF import requires pypdf. Install BookMem dependencies with `pip install -e .`.") from exc

    reader = PdfReader(str(source_path))
    parts = []
    title = None
    author = None
    try:
        metadata = reader.metadata
        title = getattr(metadata, "title", None)
        author = getattr(metadata, "author", None)
    except Exception:
        pass

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(f"## Page {index}\n\n{text.strip()}")

    output_path = output_path_for_source(source_path, output_dir, title=title, author=author, overwrite=overwrite)
    frontmatter = {
        "bookmem_import": {
            "source_format": "pdf",
            "source_path": str(source_path),
            "importer_version": IMPORTER_VERSION,
            "status": "raw_import",
            "warning": "PDF text extraction is best-effort. Review the Markdown before preparing.",
        }
    }
    output_path.write_text(_frontmatter_block(frontmatter) + "\n" + "\n\n".join(parts).strip() + "\n", encoding="utf-8")
    return ImportResult(str(source_path), str(output_path), "pdf", title, author, len(parts), warning="PDF text extraction is best-effort.")


def import_calibre(calibre_library: Path, output_dir: Path, overwrite: bool = False) -> list[ImportResult]:
    """Import Markdown-ish stubs from a Calibre metadata.db.

    This does not convert book files. It creates raw Markdown metadata stubs
    that can later be paired with actual EPUB/PDF imports or used for audit.
    """
    metadata_db = calibre_library / "metadata.db"
    if not metadata_db.exists():
        raise FileNotFoundError(f"Calibre metadata.db not found: {metadata_db}")

    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(metadata_db)
    conn.row_factory = sqlite3.Row
    results: list[ImportResult] = []

    try:
        rows = conn.execute(
            """
            SELECT b.id, b.title, b.path, group_concat(a.name, ', ') AS authors
            FROM books b
            LEFT JOIN books_authors_link bal ON bal.book = b.id
            LEFT JOIN authors a ON a.id = bal.author
            GROUP BY b.id, b.title, b.path
            ORDER BY b.title
            """
        ).fetchall()

        for row in rows:
            title = row["title"]
            author = row["authors"]
            rel_path = row["path"]
            output_path = output_path_for_source(Path(str(title) + ".md"), output_dir, title=title, author=author, overwrite=overwrite)
            frontmatter = {
                "bookmem_import": {
                    "source_format": "calibre",
                    "source_path": str(calibre_library / rel_path) if rel_path else str(calibre_library),
                    "importer_version": IMPORTER_VERSION,
                    "status": "metadata_stub",
                },
                "title": title,
                "author": author,
            }
            body = f"# {title}\n\nImported from Calibre metadata. Attach or import the source ebook file before preparing this as a canonical BookMem book.\n"
            output_path.write_text(_frontmatter_block(frontmatter) + "\n" + body, encoding="utf-8")
            results.append(ImportResult(str(calibre_library), str(output_path), "calibre", title, author, 1, warning="Metadata stub only."))
    finally:
        conn.close()

    return results


def _frontmatter_block(data: dict[str, Any]) -> str:
    import yaml

    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n---\n"


def result_as_dict(result: ImportResult) -> dict[str, Any]:
    return asdict(result)
