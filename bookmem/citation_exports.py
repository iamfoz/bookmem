from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any
import xml.etree.ElementTree as ET

from .chunking import slugify
from .frontmatter import read_markdown_with_frontmatter, normalise_isbn

CITATION_EXPORT_VERSION = "0.1.0"

SUPPORTED_STYLES = {"apa", "harvard", "mla", "chicago"}
SUPPORTED_FORMATS = {"bibtex", "ris", "csl-json", "endnote-xml"}


@dataclass
class BookReference:
    path: str
    book_id: str
    title: str
    author: str | None = None
    subtitle: str | None = None
    year: str | None = None
    publisher: str | None = None
    place: str | None = None
    edition: str | None = None
    isbn: str | None = None
    primary_class: str | None = None
    primary_label: str | None = None
    source_status: str | None = None

    @property
    def display_title(self) -> str:
        if self.subtitle and self.subtitle.lower() not in self.title.lower():
            return f"{self.title}: {self.subtitle}"
        return self.title


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    return None


def _extract_year(frontmatter: dict[str, Any]) -> str | None:
    candidates = [
        frontmatter.get("year"),
        frontmatter.get("published_year"),
        frontmatter.get("publication_year"),
        frontmatter.get("date"),
        frontmatter.get("published"),
    ]
    publication = frontmatter.get("publication")
    if isinstance(publication, dict):
        candidates.extend([
            publication.get("year"),
            publication.get("date"),
            publication.get("published"),
        ])
    source = frontmatter.get("source")
    if isinstance(source, dict):
        candidates.extend([source.get("year"), source.get("published_year")])

    for candidate in candidates:
        if candidate is None:
            continue
        match = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", str(candidate))
        if match:
            return match.group(1)
    return None


def _extract_isbn(frontmatter: dict[str, Any]) -> str | None:
    isbn_data = frontmatter.get("isbn")
    if isinstance(isbn_data, dict):
        preferred_keys = ["ebook", "filename", "detected_in_text", "hardcover", "softcover", "print", "unknown"]
        for key in preferred_keys:
            if key in isbn_data:
                normalised = normalise_isbn(str(isbn_data[key]))
                if normalised:
                    return normalised
        for value in isbn_data.values():
            normalised = normalise_isbn(str(value))
            if normalised:
                return normalised
    if isinstance(isbn_data, str):
        return normalise_isbn(isbn_data)
    return None


def _extract_publication_value(frontmatter: dict[str, Any], key: str) -> str | None:
    direct = frontmatter.get(key)
    publication = frontmatter.get("publication")
    source = frontmatter.get("source")
    return _first_string(
        direct,
        publication.get(key) if isinstance(publication, dict) else None,
        source.get(key) if isinstance(source, dict) else None,
    )


def reference_from_frontmatter(path: Path) -> BookReference:
    frontmatter, _body, _has_frontmatter = read_markdown_with_frontmatter(path)
    title = _first_string(frontmatter.get("title"), path.stem) or path.stem
    author = _first_string(frontmatter.get("author"))
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    bookmem = frontmatter.get("bookmem") if isinstance(frontmatter.get("bookmem"), dict) else {}

    book_id = _first_string(frontmatter.get("book_id"), bookmem.get("book_id"))
    if not book_id:
        book_id = slugify(f"{author or ''}_{title}")

    return BookReference(
        path=str(path),
        book_id=book_id,
        title=title,
        author=author,
        subtitle=_first_string(frontmatter.get("subtitle")),
        year=_extract_year(frontmatter),
        publisher=_extract_publication_value(frontmatter, "publisher"),
        place=_extract_publication_value(frontmatter, "place"),
        edition=_first_string(frontmatter.get("edition"), _extract_publication_value(frontmatter, "edition")),
        isbn=_extract_isbn(frontmatter),
        primary_class=_first_string(classification.get("primary_class")),
        primary_label=_first_string(classification.get("primary_label")),
        source_status=_first_string(bookmem.get("source_status")),
    )


def references_from_directory(books_dir: Path) -> list[BookReference]:
    return [reference_from_frontmatter(path) for path in sorted(books_dir.glob("**/*.md"))]


def _split_author_name(author: str | None) -> tuple[str, str]:
    if not author:
        return ("", "")
    author = author.strip()
    if "," in author:
        family, given = [part.strip() for part in author.split(",", 1)]
        return family, given
    parts = author.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def _initials(given: str) -> str:
    initials = []
    for part in re.split(r"[\s-]+", given.strip()):
        if part:
            initials.append(part[0].upper() + ".")
    return " ".join(initials)


def _author_apa(author: str | None) -> str:
    if not author:
        return "Unknown author"
    family, given = _split_author_name(author)
    if not given:
        return family
    return f"{family}, {_initials(given)}"


def _author_display(author: str | None) -> str:
    if not author:
        return "Unknown author"
    family, given = _split_author_name(author)
    if given:
        return f"{family}, {given}"
    return family


def _sentence(parts: list[str]) -> str:
    text = " ".join(part.strip() for part in parts if part and part.strip())
    return re.sub(r"\s+", " ", text).strip()


def format_reference(reference: BookReference, style: str = "apa") -> str:
    style = style.lower().strip()
    if style not in SUPPORTED_STYLES:
        raise ValueError(f"Unsupported citation style: {style}")

    year = reference.year or "n.d."
    title = reference.display_title
    edition = reference.edition
    publisher = reference.publisher
    place = reference.place
    isbn = reference.isbn

    if style == "apa":
        bits = [f"{_author_apa(reference.author)} ({year}).", f"*{title}*."]
        if edition:
            bits.append(f"({edition}).")
        if publisher:
            bits.append(f"{publisher}.")
        if isbn:
            bits.append(f"ISBN {isbn}.")
        return _sentence(bits)

    if style == "harvard":
        bits = [f"{_author_apa(reference.author)} ({year})", f"*{title}*."]
        if edition:
            bits.append(f"{edition}.")
        if place and publisher:
            bits.append(f"{place}: {publisher}.")
        elif publisher:
            bits.append(f"{publisher}.")
        if isbn:
            bits.append(f"ISBN {isbn}.")
        return _sentence(bits)

    if style == "mla":
        bits = [f"{_author_display(reference.author)}.", f"*{title}*."]
        if edition:
            bits.append(f"{edition},")
        if publisher and year:
            bits.append(f"{publisher}, {year}.")
        elif publisher:
            bits.append(f"{publisher}.")
        elif year:
            bits.append(f"{year}.")
        if isbn:
            bits.append(f"ISBN {isbn}.")
        return _sentence(bits)

    # chicago
    bits = [f"{_author_display(reference.author)}.", f"*{title}*."]
    if edition:
        bits.append(f"{edition}.")
    if place and publisher and year:
        bits.append(f"{place}: {publisher}, {year}.")
    elif publisher and year:
        bits.append(f"{publisher}, {year}.")
    elif publisher:
        bits.append(f"{publisher}.")
    elif year:
        bits.append(f"{year}.")
    if isbn:
        bits.append(f"ISBN {isbn}.")
    return _sentence(bits)


def _bibtex_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _bibtex_key(reference: BookReference) -> str:
    family, _given = _split_author_name(reference.author)
    key = f"{family or 'book'}{reference.year or ''}{reference.title.split()[0] if reference.title.split() else ''}"
    return re.sub(r"[^A-Za-z0-9:_-]", "", key) or reference.book_id


def export_bibtex(references: list[BookReference]) -> str:
    entries = []
    for ref in references:
        fields = {
            "title": ref.display_title,
            "author": ref.author,
            "year": ref.year,
            "publisher": ref.publisher,
            "address": ref.place,
            "edition": ref.edition,
            "isbn": ref.isbn,
            "keywords": ref.primary_class,
        }
        lines = [f"@book{{{_bibtex_key(ref)},"]
        for key, value in fields.items():
            if value:
                lines.append(f"  {key} = {{{_bibtex_escape(str(value))}}},")
        lines.append(f"  note = {{BookMem ID: {_bibtex_escape(ref.book_id)}}}")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + ("\n" if entries else "")


def export_ris(references: list[BookReference]) -> str:
    records = []
    for ref in references:
        lines = ["TY  - BOOK"]
        if ref.title:
            lines.append(f"TI  - {ref.display_title}")
        if ref.author:
            lines.append(f"AU  - {ref.author}")
        if ref.year:
            lines.append(f"PY  - {ref.year}")
        if ref.publisher:
            lines.append(f"PB  - {ref.publisher}")
        if ref.place:
            lines.append(f"CY  - {ref.place}")
        if ref.edition:
            lines.append(f"ET  - {ref.edition}")
        if ref.isbn:
            lines.append(f"SN  - {ref.isbn}")
        if ref.primary_class:
            lines.append(f"KW  - BMDC {ref.primary_class}")
        lines.append(f"N1  - BookMem ID: {ref.book_id}")
        lines.append("ER  -")
        records.append("\n".join(lines))
    return "\n\n".join(records) + ("\n" if records else "")


def _csl_author(author: str | None) -> list[dict[str, str]]:
    if not author:
        return []
    family, given = _split_author_name(author)
    result = {"family": family}
    if given:
        result["given"] = given
    return [result]


def export_csl_json(references: list[BookReference]) -> str:
    items = []
    for ref in references:
        item: dict[str, Any] = {
            "id": ref.book_id,
            "type": "book",
            "title": ref.display_title,
        }
        authors = _csl_author(ref.author)
        if authors:
            item["author"] = authors
        if ref.year:
            item["issued"] = {"date-parts": [[int(ref.year)]]}
        if ref.publisher:
            item["publisher"] = ref.publisher
        if ref.place:
            item["publisher-place"] = ref.place
        if ref.edition:
            item["edition"] = ref.edition
        if ref.isbn:
            item["ISBN"] = ref.isbn
        if ref.primary_class:
            item["categories"] = [f"BMDC {ref.primary_class}"]
        items.append(item)
    return json.dumps(items, indent=2, ensure_ascii=False) + "\n"


def export_endnote_xml(references: list[BookReference]) -> str:
    root = ET.Element("xml")
    records = ET.SubElement(root, "records")
    for ref in references:
        record = ET.SubElement(records, "record")
        ET.SubElement(record, "ref-type", name="Book").text = "6"
        contributors = ET.SubElement(record, "contributors")
        authors = ET.SubElement(contributors, "authors")
        if ref.author:
            ET.SubElement(authors, "author").text = ref.author
        titles = ET.SubElement(record, "titles")
        ET.SubElement(titles, "title").text = ref.display_title
        if ref.year:
            dates = ET.SubElement(record, "dates")
            ET.SubElement(dates, "year").text = ref.year
        if ref.publisher:
            ET.SubElement(record, "publisher").text = ref.publisher
        if ref.place:
            ET.SubElement(record, "pub-location").text = ref.place
        if ref.edition:
            ET.SubElement(record, "edition").text = ref.edition
        if ref.isbn:
            ET.SubElement(record, "isbn").text = ref.isbn
        if ref.primary_class:
            keywords = ET.SubElement(record, "keywords")
            ET.SubElement(keywords, "keyword").text = f"BMDC {ref.primary_class}"
        notes = ET.SubElement(record, "notes")
        ET.SubElement(notes, "style", face="normal", font="default", size="100%").text = f"BookMem ID: {ref.book_id}"
    return ET.tostring(root, encoding="unicode") + "\n"


def export_references(references: list[BookReference], export_format: str) -> str:
    export_format = export_format.lower().strip()
    if export_format == "bibtex":
        return export_bibtex(references)
    if export_format == "ris":
        return export_ris(references)
    if export_format == "csl-json":
        return export_csl_json(references)
    if export_format == "endnote-xml":
        return export_endnote_xml(references)
    raise ValueError(f"Unsupported reference export format: {export_format}")
