"""Graph visualisation exports for BookMem."""

from __future__ import annotations

from pathlib import Path
import html
import json
import math
from typing import Any

from .book_graph import load_book_graph
from .audit import append_audit_record


GRAPH_EXPORT_VERSION = "0.1.0"
SUPPORTED_GRAPH_EXPORT_FORMATS = {"graphml", "cytoscape", "mermaid", "obsidian-canvas"}
DEFAULT_EXPORT_DIR = Path("exports/graphs")


def _nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in graph.get("nodes", []) if isinstance(node, dict)]


def _edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]


def _node_label(node: dict[str, Any]) -> str:
    title = str(node.get("title") or node.get("book_id") or "Untitled")
    author = node.get("author")
    return f"{title} — {author}" if author else title


def _edge_label(edge: dict[str, Any]) -> str:
    reasons = edge.get("reasons") or []
    if reasons:
        return "; ".join(str(reason) for reason in reasons[:2])
    types = edge.get("relationship_types") or []
    if types:
        return ", ".join(str(t) for t in types[:3])
    return str(edge.get("score") or "")


def graphml(graph: dict[str, Any]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="title" for="node" attr.name="title" attr.type="string"/>',
        '  <key id="author" for="node" attr.name="author" attr.type="string"/>',
        '  <key id="primary_class" for="node" attr.name="primary_class" attr.type="string"/>',
        '  <key id="topics" for="node" attr.name="topics" attr.type="string"/>',
        '  <key id="score" for="edge" attr.name="score" attr.type="double"/>',
        '  <key id="relationship_types" for="edge" attr.name="relationship_types" attr.type="string"/>',
        '  <key id="reasons" for="edge" attr.name="reasons" attr.type="string"/>',
        '  <graph id="BookMem" edgedefault="undirected">',
    ]

    for node in _nodes(graph):
        node_id = html.escape(str(node.get("book_id") or ""))
        topics = ", ".join(str(t) for t in node.get("topics") or [])
        lines += [
            f'    <node id="{node_id}">',
            f'      <data key="title">{html.escape(str(node.get("title") or ""))}</data>',
            f'      <data key="author">{html.escape(str(node.get("author") or ""))}</data>',
            f'      <data key="primary_class">{html.escape(str(node.get("primary_class") or ""))}</data>',
            f'      <data key="topics">{html.escape(topics)}</data>',
            '    </node>',
        ]

    for idx, edge in enumerate(_edges(graph), start=1):
        source = html.escape(str(edge.get("source") or ""))
        target = html.escape(str(edge.get("target") or ""))
        relationship_types = ", ".join(str(t) for t in edge.get("relationship_types") or [])
        reasons = "; ".join(str(r) for r in edge.get("reasons") or [])
        lines += [
            f'    <edge id="e{idx}" source="{source}" target="{target}">',
            f'      <data key="score">{float(edge.get("score") or 0)}</data>',
            f'      <data key="relationship_types">{html.escape(relationship_types)}</data>',
            f'      <data key="reasons">{html.escape(reasons)}</data>',
            '    </edge>',
        ]

    lines += ['  </graph>', '</graphml>', '']
    return "\n".join(lines)


def cytoscape(graph: dict[str, Any]) -> str:
    elements = []
    for node in _nodes(graph):
        elements.append({
            "data": {
                "id": str(node.get("book_id")),
                "label": _node_label(node),
                "title": node.get("title"),
                "author": node.get("author"),
                "primary_class": node.get("primary_class"),
                "primary_label": node.get("primary_label"),
                "topics": node.get("topics") or [],
                "path": node.get("path"),
            }
        })

    for idx, edge in enumerate(_edges(graph), start=1):
        elements.append({
            "data": {
                "id": f"e{idx}",
                "source": edge.get("source"),
                "target": edge.get("target"),
                "score": edge.get("score"),
                "label": _edge_label(edge),
                "relationship_types": edge.get("relationship_types") or [],
                "reasons": edge.get("reasons") or [],
                "shared_topics": edge.get("shared_topics") or [],
            }
        })

    return json.dumps({
        "format": "cytoscape",
        "graph_export_version": GRAPH_EXPORT_VERSION,
        "generated_from": "BookMem",
        "elements": elements,
    }, indent=2, ensure_ascii=False) + "\n"


def _mermaid_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned or "node"


def mermaid(graph: dict[str, Any], max_edges: int | None = None) -> str:
    nodes = {str(node.get("book_id")): node for node in _nodes(graph)}
    edges = sorted(_edges(graph), key=lambda edge: float(edge.get("score") or 0), reverse=True)
    if max_edges:
        edges = edges[:max_edges]

    lines = [
        "---",
        "title: BookMem Book Graph",
        "---",
        "graph TD",
    ]

    used_nodes = set()
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        used_nodes.add(source)
        used_nodes.add(target)

    for node_id in sorted(used_nodes):
        node = nodes.get(node_id, {"title": node_id})
        label = _node_label(node).replace('"', "'")
        lines.append(f'  {_mermaid_id(node_id)}["{label}"]')

    for edge in edges:
        source = _mermaid_id(str(edge.get("source") or ""))
        target = _mermaid_id(str(edge.get("target") or ""))
        label = _edge_label(edge).replace('"', "'")
        score = edge.get("score")
        edge_text = f"{label} ({score})" if score is not None else label
        lines.append(f'  {source} -- "{edge_text}" --> {target}')

    lines.append("")
    return "\n".join(lines)


def obsidian_canvas(graph: dict[str, Any]) -> str:
    nodes = _nodes(graph)
    edges = _edges(graph)
    canvas_nodes = []
    canvas_edges = []

    # Deterministic radial layout.
    radius = max(600, len(nodes) * 35)
    for idx, node in enumerate(nodes):
        angle = (2 * math.pi * idx) / max(len(nodes), 1)
        x = int(math.cos(angle) * radius)
        y = int(math.sin(angle) * radius)
        label = _node_label(node)
        body = [
            f"# {node.get('title') or 'Untitled'}",
            "",
            f"Author: {node.get('author') or 'Unknown'}",
            f"Class: {node.get('primary_class') or ''} {node.get('primary_label') or ''}".strip(),
        ]
        topics = node.get("topics") or []
        if topics:
            body.append("Topics: " + ", ".join(str(t) for t in topics[:8]))

        path = node.get("path")
        canvas_node = {
            "id": str(node.get("book_id")),
            "type": "file" if path else "text",
            "x": x,
            "y": y,
            "width": 420,
            "height": 220,
        }
        if path:
            canvas_node["file"] = str(path)
        else:
            canvas_node["text"] = "\n".join(body)
        canvas_nodes.append(canvas_node)

    for idx, edge in enumerate(edges, start=1):
        canvas_edges.append({
            "id": f"edge-{idx}",
            "fromNode": str(edge.get("source")),
            "toNode": str(edge.get("target")),
            "label": _edge_label(edge)[:120],
        })

    return json.dumps({
        "nodes": canvas_nodes,
        "edges": canvas_edges,
    }, indent=2, ensure_ascii=False) + "\n"


def default_output_path(format: str) -> Path:
    fmt = format.lower()
    suffix = {
        "graphml": ".graphml",
        "cytoscape": ".cyjs",
        "mermaid": ".mmd",
        "obsidian-canvas": ".canvas",
    }.get(fmt)
    if not suffix:
        raise ValueError(f"Unsupported graph export format: {format}")
    return DEFAULT_EXPORT_DIR / f"book_graph{suffix}"


def export_graph(
    format: str,
    graph_path: Path | None = None,
    output: Path | None = None,
    rebuild: bool = False,
    max_edges: int | None = None,
) -> dict[str, Any]:
    from .book_graph import build_book_graph

    fmt = format.lower()
    if fmt not in SUPPORTED_GRAPH_EXPORT_FORMATS:
        raise ValueError(f"Unsupported graph export format: {format}. Supported: {', '.join(sorted(SUPPORTED_GRAPH_EXPORT_FORMATS))}")

    graph_path = graph_path or Path("data/graphs/book_graph.json")
    if rebuild or not graph_path.exists():
        build_book_graph(output_path=graph_path)

    graph = load_book_graph(graph_path)
    output = output or default_output_path(fmt)
    output.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "graphml":
        text = graphml(graph)
    elif fmt == "cytoscape":
        text = cytoscape(graph)
    elif fmt == "mermaid":
        text = mermaid(graph, max_edges=max_edges)
    elif fmt == "obsidian-canvas":
        text = obsidian_canvas(graph)
    else:
        raise ValueError(f"Unsupported graph export format: {format}")

    output.write_text(text, encoding="utf-8")
    append_audit_record(
        action="graph.export",
        status="ok",
        changed_files=[output],
        target=fmt,
        message=f"Exported book graph as {fmt}",
        details={
            "graph_path": str(graph_path),
            "output": str(output),
            "node_count": graph.get("node_count", len(_nodes(graph))),
            "edge_count": graph.get("edge_count", len(_edges(graph))),
            "max_edges": max_edges,
        },
    )
    return {
        "format": fmt,
        "output": str(output),
        "graph_path": str(graph_path),
        "node_count": graph.get("node_count", len(_nodes(graph))),
        "edge_count": graph.get("edge_count", len(_edges(graph))),
        "graph_export_version": GRAPH_EXPORT_VERSION,
    }


def export_all_graph_formats(graph_path: Path | None = None, output_dir: Path | None = None, rebuild: bool = False, max_edges: int | None = None) -> list[dict[str, Any]]:
    output_dir = output_dir or DEFAULT_EXPORT_DIR
    results = []
    for fmt in ("graphml", "cytoscape", "mermaid", "obsidian-canvas"):
        output = output_dir / default_output_path(fmt).name
        results.append(export_graph(fmt, graph_path=graph_path, output=output, rebuild=rebuild, max_edges=max_edges))
        rebuild = False
    return results
