"""
VisionarySTEM EPUB3 Exporter — Sprint 6.1
===========================================
Generate EPUB3 file with MathML for accessibility.

EPUB3 = ZIP container with HTML5 + MathML + media + nav.
Schema follows EPUB 3.3 spec (https://www.w3.org/TR/epub-33/).

Reference: research/findings/05-accessibility-standards.md
"""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import datetime, timezone
from html import escape

from src.api.schemas import DocumentAnalysisResponse


# ============================================================
# Static EPUB3 boilerplate
# ============================================================

MIMETYPE = "application/epub+zip"

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str, max_len: int = 50) -> str:
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len] or "doc"


# ============================================================
# Naive LaTeX → MathML for the most common patterns
# ============================================================

LATEX_TO_MATHML_MACROS = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
    r"\iota": "ι", r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ",
    r"\nu": "ν", r"\xi": "ξ", r"\pi": "π", r"\rho": "ρ",
    r"\sigma": "σ", r"\tau": "τ", r"\phi": "φ", r"\chi": "χ",
    r"\psi": "ψ", r"\omega": "ω",
    r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
    r"\times": "×", r"\div": "÷", r"\cdot": "·",
    r"\leq": "≤", r"\geq": "≥", r"\neq": "≠", r"\approx": "≈",
    r"\sum": "∑", r"\prod": "∏", r"\int": "∫",
    r"\sqrt": "√", r"\to": "→", r"\Rightarrow": "⇒", r"\Leftrightarrow": "⇔",
}


def latex_to_mathml(latex: str) -> str:
    """
    Convert LaTeX to a basic MathML representation.

    NOT a full converter — handles only frequent patterns. For production accuracy,
    use server-side MathJax or KaTeX with MathML output, or Mathpix API.

    For demo: enough to validate accessibility output.
    """
    if not latex:
        return ""

    s = latex.strip()
    # Strip surrounding $...$ if present
    s = re.sub(r"^\$+|\$+$", "", s).strip()
    s = re.sub(r"^\\\(|\\\)$|^\\\[|\\\]$", "", s).strip()

    # Replace macros
    for macro, sym in LATEX_TO_MATHML_MACROS.items():
        s = s.replace(macro, sym)

    # Handle \frac{a}{b}
    s = re.sub(
        r"\\frac\{([^{}]+)\}\{([^{}]+)\}",
        r'<mfrac><mrow>\1</mrow><mrow>\2</mrow></mfrac>',
        s,
    )

    # Subscript / superscript (single char)
    s = re.sub(r"\^(\w)", r"<msup><mi></mi><mn>\1</mn></msup>", s)
    s = re.sub(r"_(\w)", r"<msub><mi></mi><mn>\1</mn></msub>", s)

    # Wrap variables and operators in MathML elements (very rough)
    parts: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "<":
            # Already MathML element — find closing >
            close = s.find(">", i)
            if close == -1:
                parts.append(escape(ch))
                i += 1
            else:
                parts.append(s[i : close + 1])
                i = close + 1
        elif ch.isalpha():
            parts.append(f"<mi>{escape(ch)}</mi>")
            i += 1
        elif ch.isdigit():
            # Group consecutive digits
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            parts.append(f"<mn>{escape(s[i:j])}</mn>")
            i = j
        elif ch in "+-=()[]<>·×÷":
            parts.append(f"<mo>{escape(ch)}</mo>")
            i += 1
        elif ch.isspace():
            parts.append(" ")
            i += 1
        else:
            parts.append(f"<mo>{escape(ch)}</mo>")
            i += 1

    body = "".join(parts)
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML">{body}</math>'


# ============================================================
# HTML chapter generation
# ============================================================

def _block_to_html(block) -> str:
    """Render one ContentBlock as accessible HTML."""
    btype = block.type
    spoken = escape(block.spoken_text)
    raw = escape(block.raw_content or "")
    block_id = escape(block.id)

    if btype == "math":
        mathml = latex_to_mathml(block.latex or block.raw_content or "")
        return f"""
    <section id="{block_id}" role="math" aria-label="Công thức">
      <p class="spoken">{spoken}</p>
      {mathml}
      <p class="raw"><code>{raw}</code></p>
    </section>"""
    elif btype == "chart":
        alt = escape(block.alt_text_long or block.spoken_text)
        return f"""
    <figure id="{block_id}" role="img" aria-label="Biểu đồ">
      <figcaption>{spoken}</figcaption>
      <p class="alt-text">{alt}</p>
    </figure>"""
    elif btype == "figure":
        alt = escape(block.alt_text_long or block.spoken_text)
        return f"""
    <figure id="{block_id}">
      <figcaption>{spoken}</figcaption>
      <p class="alt-text">{alt}</p>
    </figure>"""
    elif btype == "table":
        return f"""
    <section id="{block_id}" role="region" aria-label="Bảng">
      <p class="spoken">{spoken}</p>
      <pre class="table-raw">{raw}</pre>
    </section>"""
    else:  # text
        return f'    <p id="{block_id}">{spoken}</p>'


def _chapter_html(doc: DocumentAnalysisResponse, page_num: int, blocks: list) -> str:
    title = f"Trang {page_num}"
    body_parts = [_block_to_html(b) for b in blocks]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="vi" xml:lang="vi">
<head>
  <meta charset="UTF-8"/>
  <title>{escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <p class="meta">{len(blocks)} khối nội dung từ {escape(doc.document_metadata.filename)}</p>
  </header>
  <main role="main">
{chr(10).join(body_parts)}
  </main>
</body>
</html>
"""


def _stylesheet() -> str:
    return """body {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  font-size: 1.1em;
  line-height: 1.7;
  max-width: 720px;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
}
h1 { color: #4F46E5; font-size: 1.8em; }
h2 { color: #6D28D9; }
.meta { color: #6b7280; font-size: 0.9em; }
.spoken { font-style: italic; color: #374151; margin: 0.5em 0; }
.raw, code { font-family: 'JetBrains Mono', monospace; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
.alt-text { color: #4b5563; font-size: 0.95em; }
section, figure { margin: 1.5em 0; padding: 1em; border-left: 4px solid #6366F1; background: #f9fafb; border-radius: 8px; }
figure[role="img"] { border-left-color: #10B981; }
section[role="math"] { border-left-color: #ef4444; }
section[role="region"] { border-left-color: #f59e0b; }
math { font-size: 1.3em; }
"""


def _toc_xhtml(doc: DocumentAnalysisResponse, n_chapters: int) -> str:
    items = "\n".join(
        f'      <li><a href="chap{i+1}.xhtml">Trang {i+1}</a></li>'
        for i in range(n_chapters)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="vi">
<head>
  <meta charset="UTF-8"/>
  <title>Mục lục</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Mục lục</h1>
    <ol>
{items}
    </ol>
  </nav>
</body>
</html>
"""


def _content_opf(doc: DocumentAnalysisResponse, n_chapters: int, book_id: str) -> str:
    title = doc.document_metadata.filename or "VisionarySTEM Document"
    manifest_items = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                      '<item id="css" href="style.css" media-type="text/css"/>']
    spine_items = []
    for i in range(n_chapters):
        manifest_items.append(
            f'<item id="chap{i+1}" href="chap{i+1}.xhtml" media-type="application/xhtml+xml" properties="mathml"/>'
        )
        spine_items.append(f'<itemref idref="chap{i+1}"/>')

    manifest = "\n    ".join(manifest_items)
    spine = "\n    ".join(spine_items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" unique-identifier="bookid"
         xmlns="http://www.idpf.org/2007/opf"
         xml:lang="vi">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:creator>VisionarySTEM</dc:creator>
    <dc:language>vi</dc:language>
    <dc:date>{_now_iso()[:10]}</dc:date>
    <meta property="dcterms:modified">{_now_iso()}</meta>
    <meta property="schema:accessibilityFeature">MathML</meta>
    <meta property="schema:accessibilityFeature">structuralNavigation</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityFeature">alternativeText</meta>
    <meta property="schema:accessibilityHazard">none</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessMode">visual</meta>
    <meta property="schema:accessibilitySummary">Tài liệu STEM với MathML cho công thức, alt text cho hình/biểu đồ. Phù hợp screen reader và bảng Braille.</meta>
  </metadata>
  <manifest>
    {manifest}
  </manifest>
  <spine>
    <itemref idref="nav"/>
    {spine}
  </spine>
</package>
"""


# ============================================================
# Main builder
# ============================================================

def build_epub3(doc: DocumentAnalysisResponse) -> bytes:
    """
    Build an EPUB3 file from analyzed document. Returns raw bytes (zip).
    Pages are split: one chapter per `coordinates.page`.
    """
    # Group blocks by page
    by_page: dict[int, list] = {}
    for b in doc.content_blocks:
        by_page.setdefault(b.coordinates.page, []).append(b)

    # Sort blocks within each page by reading_order if available, else (y, x)
    for page in by_page.values():
        page.sort(
            key=lambda b: (
                b.reading_order if b.reading_order is not None else 1_000_000,
                b.coordinates.y,
                b.coordinates.x,
            )
        )

    pages = sorted(by_page.keys())
    n_chapters = len(pages)
    book_id = uuid.uuid4().hex

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be FIRST and uncompressed (EPUB spec)
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, MIMETYPE)
        # Container
        zf.writestr("META-INF/container.xml", CONTAINER_XML)
        # Manifest
        zf.writestr("OEBPS/content.opf", _content_opf(doc, n_chapters, book_id))
        # Stylesheet
        zf.writestr("OEBPS/style.css", _stylesheet())
        # Nav
        zf.writestr("OEBPS/nav.xhtml", _toc_xhtml(doc, n_chapters))
        # Chapters
        for i, page_num in enumerate(pages, start=1):
            zf.writestr(f"OEBPS/chap{i}.xhtml", _chapter_html(doc, page_num, by_page[page_num]))

    return buffer.getvalue()
