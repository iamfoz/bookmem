from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .frontmatter import (
    generate_frontmatter,
    normalise_isbn,
    read_markdown_with_frontmatter,
    write_markdown_with_frontmatter,
)
from .taxonomy import get_class_label, normalise_alias

LOC_SRU_ENDPOINT = "https://lx2.loc.gov/sru/lcdb"

NS = {
    "zs": "http://www.loc.gov/zing/srw/",
    "marc": "http://www.loc.gov/MARC21/slim",
}


@dataclass
class LocLookupResult:
    found: bool
    isbn: str | None = None
    title: str | None = None
    author: str | None = None
    class_number: str | None = None
    class_source_field: str | None = None
    raw_classification_number: str | None = None
    lccn: str | None = None
    record_count: int = 0
    source_url: str | None = None
    error: str | None = None


def clean_isbn_for_query(isbn: str | None) -> str | None:
    return normalise_isbn(isbn)


def marc_subfields(record: ET.Element, tag: str, codes: list[str]) -> list[str]:
    values: list[str] = []
    for field in record.findall(f".//marc:datafield[@tag='{tag}']", NS):
        for subfield in field.findall("marc:subfield", NS):
            if subfield.attrib.get("code") in codes and subfield.text:
                values.append(subfield.text.strip())
    return values


def marc_controlfields(record: ET.Element, tag: str) -> list[str]:
    values: list[str] = []
    for field in record.findall(f".//marc:controlfield[@tag='{tag}']", NS):
        if field.text:
            values.append(field.text.strip())
    return values


def first_joined(record: ET.Element, tag: str, codes: list[str]) -> str | None:
    values = marc_subfields(record, tag, codes)
    return " ".join(values).strip(" /:;,.\t\n") if values else None


def normalise_class_number(value: str | None) -> str | None:
    """Extract a routing-friendly decimal class from a catalogue value.

    MARC 082 may contain values such as:
      - 158.1
      - 158.1/092
      - 741.5/6973--dc23

    BMDC stores the leading numeric class so that it can be filtered and routed.
    """
    if not value:
        return None
    match = re.search(r"\d{3}(?:\.\d+)?", value)
    return match.group(0) if match else None


def sru_url_for_isbn(isbn: str, maximum_records: int = 5) -> str:
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "query": f"bath.isbn={isbn}",
        "maximumRecords": str(maximum_records),
        "recordSchema": "marcxml",
    }
    return LOC_SRU_ENDPOINT + "?" + urllib.parse.urlencode(params)


def fetch_url(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BookMem/0.1 (+https://github.com/forryan/bookmem)",
            "Accept": "application/xml,text/xml,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_loc_sru_response(xml_bytes: bytes, isbn: str, source_url: str) -> LocLookupResult:
    root = ET.fromstring(xml_bytes)

    number_text = root.findtext(".//zs:numberOfRecords", namespaces=NS)
    try:
        record_count = int(number_text or "0")
    except ValueError:
        record_count = 0

    records = root.findall(".//zs:recordData/marc:record", NS)
    if not records:
        return LocLookupResult(found=False, isbn=isbn, record_count=record_count, source_url=source_url)

    # Prefer the first record with a classification number, otherwise fall back to first record.
    chosen = records[0]
    raw_class: str | None = None
    source_field: str | None = None
    for record in records:
        ddc_values = marc_subfields(record, "082", ["a"])
        if ddc_values:
            chosen = record
            raw_class = ddc_values[0]
            source_field = "082$a"
            break

    if raw_class is None:
        additional_values = marc_subfields(chosen, "083", ["a"])
        if additional_values:
            raw_class = additional_values[0]
            source_field = "083$a"

    class_number = normalise_class_number(raw_class)

    title = first_joined(chosen, "245", ["a", "b"])
    author = first_joined(chosen, "100", ["a"]) or first_joined(chosen, "700", ["a"])
    lccn = first_joined(chosen, "010", ["a"]) or (marc_controlfields(chosen, "001") or [None])[0]

    return LocLookupResult(
        found=True,
        isbn=isbn,
        title=title,
        author=author,
        class_number=class_number,
        class_source_field=source_field,
        raw_classification_number=raw_class,
        lccn=lccn,
        record_count=record_count,
        source_url=source_url,
    )


def lookup_loc_by_isbn(isbn: str, timeout: int = 20) -> LocLookupResult:
    clean_isbn = clean_isbn_for_query(isbn)
    if not clean_isbn:
        return LocLookupResult(found=False, error=f"Invalid ISBN: {isbn}")

    url = sru_url_for_isbn(clean_isbn)
    try:
        xml_bytes = fetch_url(url, timeout=timeout)
    except urllib.error.URLError as exc:
        return LocLookupResult(found=False, isbn=clean_isbn, source_url=url, error=str(exc))
    except TimeoutError as exc:
        return LocLookupResult(found=False, isbn=clean_isbn, source_url=url, error=str(exc))

    try:
        return parse_loc_sru_response(xml_bytes, clean_isbn, url)
    except ET.ParseError as exc:
        return LocLookupResult(found=False, isbn=clean_isbn, source_url=url, error=f"XML parse error: {exc}")


def isbn_from_frontmatter(frontmatter: dict[str, Any]) -> str | None:
    isbn = frontmatter.get("isbn")
    if isinstance(isbn, dict):
        for key in ["filename", "ebook", "paperback", "hardcover", "unknown", "detected_in_text"]:
            if isbn.get(key):
                return normalise_isbn(str(isbn[key]))
        for value in isbn.values():
            normalised = normalise_isbn(str(value))
            if normalised:
                return normalised
    if isinstance(isbn, str):
        return normalise_isbn(isbn)
    return None


def ensure_frontmatter_exists(path: Path) -> dict[str, Any]:
    result, frontmatter, _body = generate_frontmatter(path, write=False, overwrite=False)
    return frontmatter


def merge_loc_result_into_frontmatter(
    frontmatter: dict[str, Any],
    result: LocLookupResult,
    overwrite_classification: bool = False,
) -> dict[str, Any]:
    updated = dict(frontmatter)
    classification = updated.get("classification")
    if not isinstance(classification, dict):
        classification = {}

    external = classification.get("external")
    if not isinstance(external, dict):
        external = {}

    external["library_of_congress"] = {
        "source": "library_of_congress_sru",
        "lookup": "isbn",
        "isbn": result.isbn,
        "matched_title": result.title,
        "matched_author": result.author,
        "lccn": result.lccn,
        "record_count": result.record_count,
        "class_source_field": result.class_source_field,
        "raw_classification_number": result.raw_classification_number,
        "normalised_class_number": result.class_number,
        "source_url": result.source_url,
    }

    classification["external"] = external

    current_class = classification.get("primary_class")
    current_source = ""
    if isinstance(updated.get("metadata"), dict):
        current_source = str(updated["metadata"].get("classification_source", ""))

    should_update_class = bool(result.class_number) and (
        overwrite_classification
        or not current_class
        or str(current_class) == "999"
        or current_source in {"unclassified", "filename/content keyword", "folder_path"}
    )

    if should_update_class:
        class_code = str(result.class_number)
        # Keep a decimal code if supplied, but use the three-digit class for labels if needed.
        base_code = class_code[:3]
        classification["primary_class"] = class_code
        classification["primary_label"] = get_class_label(class_code) or get_class_label(base_code)
        aliases = classification.get("routing_aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        # Add a few routing aliases based on the three-digit class, without overwriting user aliases.
        default_aliases = {
            "158": ["personal_development", "productivity"],
            "332": ["finance", "investing"],
            "330": ["finance", "economics"],
            "650": ["business", "productivity"],
            "658": ["business", "management"],
            "510": ["mathematics"],
            "610": ["health"],
            "613": ["health", "wellbeing"],
            "006": ["technology", "ai"],
            "005": ["technology", "software"],
            "808": ["writing", "creativity"],
        }.get(base_code, [])
        merged_aliases = []
        seen: set[str] = set()
        for alias in list(aliases) + default_aliases:
            normalised = normalise_alias(str(alias))
            if normalised not in seen:
                seen.add(normalised)
                merged_aliases.append(normalised)
        classification["routing_aliases"] = merged_aliases

        metadata = updated.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["classification_source"] = "library_of_congress_sru_isbn"
        metadata["classification_review_required"] = True
        updated["metadata"] = metadata

    updated["classification"] = classification
    return updated


def enrich_file_with_loc(
    path: Path,
    write: bool = False,
    overwrite_classification: bool = False,
    timeout: int = 20,
) -> tuple[LocLookupResult, dict[str, Any]]:
    frontmatter = ensure_frontmatter_exists(path)
    _existing, body, _had_existing = read_markdown_with_frontmatter(path)
    isbn = isbn_from_frontmatter(frontmatter)

    if not isbn:
        result = LocLookupResult(found=False, error="No ISBN found in frontmatter or filename metadata")
        return result, frontmatter

    result = lookup_loc_by_isbn(isbn, timeout=timeout)
    if not result.found:
        return result, frontmatter

    updated = merge_loc_result_into_frontmatter(
        frontmatter,
        result,
        overwrite_classification=overwrite_classification,
    )

    if write:
        write_markdown_with_frontmatter(path, updated, body)

    return result, updated
