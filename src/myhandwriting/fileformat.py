"""MHW file format v2 - save and load documents with page format and styling.

The .mhw format stores:
- Page format settings (size, margins, texture, style, line thickness, etc.)
- Multiple pages, each with styled lines
- Per-span font style and size within each line

JSON structure:
{
    "version": "2.0",
    "page_format": {
        "paper_size": "a4",
        "margin_horizontal": 40,
        "margin_vertical": 30,
        "page_texture": "Texture",
        "page_style": "Lined",
        "line_thickness": 1,
        "red_line_position": 100
    },
    "pages": [
        {
            "lines": [
                {
                    "alignment": "left",
                    "spans": [
                        {"text": "Hello", "style": "MyFont", "size": 14}
                    ]
                }
            ]
        }
    ]
}
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StyledSpan:
    """A span of text with consistent styling within a line."""
    text: str
    font_style: str = "system_default"
    font_size: int = 14


@dataclass
class StyledLine:
    """A line containing one or more styled spans."""
    spans: list[StyledSpan] = field(default_factory=list)
    alignment: str = "left"  # left, center, right


@dataclass
class PageData:
    """Data for a single page."""
    lines: list[StyledLine] = field(default_factory=list)


@dataclass
class PageFormat:
    """Page format settings."""
    paper_size: str = "a4"
    margin_horizontal: int = 40
    margin_vertical: int = 30
    page_texture: str = "Texture"
    page_style: str = "Plain"
    line_thickness: int = 1
    red_line_position: int = 100


@dataclass
class Document:
    """Full document with page format and pages."""
    page_format: PageFormat = field(default_factory=PageFormat)
    pages: list[PageData] = field(default_factory=list)


def serialize_document(pages: list[PageData], page_format: PageFormat) -> str:
    """Serialize multi-page document with page format into .mhw JSON."""
    doc = {
        "version": "2.0",
        "page_format": {
            "paper_size": page_format.paper_size,
            "margin_horizontal": page_format.margin_horizontal,
            "margin_vertical": page_format.margin_vertical,
            "page_texture": page_format.page_texture,
            "page_style": page_format.page_style,
            "line_thickness": page_format.line_thickness,
            "red_line_position": page_format.red_line_position,
        },
        "pages": [],
    }

    for page in pages:
        page_data = {"lines": []}
        for line in page.lines:
            line_data = {
                "alignment": line.alignment,
                "spans": [],
            }
            for span in line.spans:
                line_data["spans"].append({
                    "text": span.text,
                    "style": span.font_style,
                    "size": span.font_size,
                })
            page_data["lines"].append(line_data)
        doc["pages"].append(page_data)

    return json.dumps(doc, indent=2, ensure_ascii=False)


def parse_document(content: str) -> Document:
    """Parse .mhw format string into a Document with page format and pages."""
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: legacy format (v1.0 or plain text)
        return _parse_legacy(content)

    version = raw.get("version", "1.0")

    if version == "2.0":
        return _parse_v2(raw)
    else:
        return _parse_v1(raw)


def _parse_v2(raw: dict) -> Document:
    """Parse v2.0 format with page_format and pages."""
    # Page format
    pf_data = raw.get("page_format", {})
    page_format = PageFormat(
        paper_size=pf_data.get("paper_size", "a4"),
        margin_horizontal=pf_data.get("margin_horizontal", 40),
        margin_vertical=pf_data.get("margin_vertical", 30),
        page_texture=pf_data.get("page_texture", "Texture"),
        page_style=pf_data.get("page_style", "Plain"),
        line_thickness=pf_data.get("line_thickness", 1),
        red_line_position=pf_data.get("red_line_position", 100),
    )

    # Pages
    pages = []
    for page_raw in raw.get("pages", []):
        page = PageData(lines=[])
        for line_data in page_raw.get("lines", []):
            line = StyledLine(
                alignment=line_data.get("alignment", "left"),
                spans=[],
            )
            for span_data in line_data.get("spans", []):
                line.spans.append(StyledSpan(
                    text=span_data.get("text", ""),
                    font_style=span_data.get("style", "system_default"),
                    font_size=span_data.get("size", 14),
                ))
            page.lines.append(line)
        pages.append(page)

    return Document(page_format=page_format, pages=pages)


def _parse_v1(raw: dict) -> Document:
    """Parse v1.0 format (single page with lines array)."""
    page = PageData(lines=[])
    for line_data in raw.get("lines", []):
        line = StyledLine(
            alignment=line_data.get("alignment", "left"),
            spans=[],
        )
        for span_data in line_data.get("spans", []):
            line.spans.append(StyledSpan(
                text=span_data.get("text", ""),
                font_style=span_data.get("style", "system_default"),
                font_size=span_data.get("size", 14),
            ))
        page.lines.append(line)

    return Document(page_format=PageFormat(), pages=[page])


def _parse_legacy(content: str) -> Document:
    """Fallback parser for legacy XML-style format or plain text."""
    pattern = re.compile(
        r"<alignment:(\w+)><style:([^>]+)><size:(\d+)>(.*?)</size:\d+></style:[^>]+></alignment:\w+>"
    )

    page = PageData(lines=[])
    for raw_line in content.split("\n"):
        raw_line = raw_line.strip()
        if not raw_line:
            page.lines.append(StyledLine(alignment="left", spans=[StyledSpan(text="")]))
            continue

        match = pattern.match(raw_line)
        if match:
            alignment = match.group(1)
            font_style = match.group(2)
            font_size = int(match.group(3))
            text = match.group(4)
            text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            page.lines.append(StyledLine(
                alignment=alignment,
                spans=[StyledSpan(text=text, font_style=font_style, font_size=font_size)],
            ))
        else:
            page.lines.append(StyledLine(
                alignment="left",
                spans=[StyledSpan(text=raw_line, font_style="system_default", font_size=14)],
            ))

    return Document(page_format=PageFormat(), pages=[page])
