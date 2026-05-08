"""Tests for src.export — Sprint 6.1 EPUB3 + 6.2 Braille."""
import io
import zipfile
import pytest


# ============ Braille ============

def test_text_to_braille_unicode_basic():
    from src.export.braille import text_to_braille_unicode
    out = text_to_braille_unicode("a")
    assert out == "⠁"


def test_text_to_braille_capital_indicator():
    from src.export.braille import text_to_braille_unicode, CAPITAL_INDICATOR
    out = text_to_braille_unicode("A")
    assert out.startswith(CAPITAL_INDICATOR)


def test_text_to_braille_number_indicator():
    from src.export.braille import text_to_braille_unicode, NUMBER_INDICATOR
    out = text_to_braille_unicode("123")
    assert out.startswith(NUMBER_INDICATOR)


def test_text_to_braille_vietnamese():
    from src.export.braille import text_to_braille_unicode
    out = text_to_braille_unicode("Lực bằng khối lượng")
    # Each Vietnamese char with diacritic maps to Braille (no errors)
    assert len(out) > 0
    assert "⠿" not in out or out.count("⠿") < 3  # mostly mapped


def test_text_to_braille_empty():
    from src.export.braille import text_to_braille_unicode
    assert text_to_braille_unicode("") == ""


def test_latex_to_braille_simple_eq():
    from src.export.braille import latex_to_braille
    out = latex_to_braille("F = ma")
    assert "⠠⠋" in out  # capital F
    assert "⠨⠅" in out  # equals


def test_latex_to_braille_strips_dollar():
    from src.export.braille import latex_to_braille
    a = latex_to_braille("$F = ma$")
    b = latex_to_braille("F = ma")
    assert a == b


def test_latex_to_braille_handles_unknown_macro():
    from src.export.braille import latex_to_braille
    # \unknown{x} should not crash
    out = latex_to_braille("\\unknownmacro x")
    assert isinstance(out, str)


# ============ EPUB3 ============

def _make_doc(sample_blocks):
    from src.api.schemas import DocumentAnalysisResponse, DocumentMetadata, SpatialIndex
    return DocumentAnalysisResponse(
        document_metadata=DocumentMetadata(
            filename="newton_law.pdf", total_pages=1, processing_time_ms=1500,
            model_used="gemini-2.5-flash",
        ),
        content_blocks=sample_blocks,
        spatial_index=SpatialIndex(regions={"center": ["block_002", "block_003"]}),
    )


def test_build_epub3_returns_valid_zip(sample_blocks):
    from src.export import build_epub3
    epub_bytes = build_epub3(_make_doc(sample_blocks))
    assert epub_bytes[:4] == b"PK\x03\x04"  # ZIP magic
    # Valid zip
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    names = zf.namelist()
    assert "mimetype" in names
    assert "META-INF/container.xml" in names
    assert "OEBPS/content.opf" in names
    assert "OEBPS/nav.xhtml" in names
    assert "OEBPS/style.css" in names


def test_epub3_mimetype_is_first_and_uncompressed(sample_blocks):
    """EPUB spec: mimetype must be FIRST entry, ZIP_STORED (no compression)."""
    from src.export import build_epub3
    epub_bytes = build_epub3(_make_doc(sample_blocks))
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    first = zf.infolist()[0]
    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED


def test_epub3_mimetype_content(sample_blocks):
    from src.export import build_epub3
    epub_bytes = build_epub3(_make_doc(sample_blocks))
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    assert zf.read("mimetype") == b"application/epub+zip"


def test_epub3_chapter_per_page(sample_blocks):
    """Multi-page doc → multiple chapXX.xhtml entries."""
    from src.export import build_epub3
    # Modify some blocks to be on page 2
    sample_blocks[3].coordinates.page = 2
    sample_blocks[4].coordinates.page = 2
    doc = _make_doc(sample_blocks)
    doc.document_metadata.total_pages = 2

    epub_bytes = build_epub3(doc)
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    chapters = [n for n in zf.namelist() if n.startswith("OEBPS/chap")]
    assert len(chapters) == 2


def test_epub3_includes_mathml_for_math_blocks(sample_blocks):
    from src.export import build_epub3
    epub_bytes = build_epub3(_make_doc(sample_blocks))
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    chap_html = zf.read("OEBPS/chap1.xhtml").decode("utf-8")
    assert "<math" in chap_html
    assert "MathML" in zf.read("OEBPS/content.opf").decode("utf-8")


def test_epub3_accessibility_metadata(sample_blocks):
    from src.export import build_epub3
    epub_bytes = build_epub3(_make_doc(sample_blocks))
    zf = zipfile.ZipFile(io.BytesIO(epub_bytes))
    opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert "schema:accessibilityFeature" in opf
    assert "schema:accessibilitySummary" in opf


# ============ MathML conversion ============

def test_latex_to_mathml_basic():
    from src.export.epub3 import latex_to_mathml
    out = latex_to_mathml("F = ma")
    assert "<math" in out
    assert "<mi>F</mi>" in out
    assert "<mo>=</mo>" in out


def test_latex_to_mathml_strips_dollar():
    from src.export.epub3 import latex_to_mathml
    a = latex_to_mathml("$F = ma$")
    b = latex_to_mathml("F = ma")
    assert a == b


def test_latex_to_mathml_handles_frac():
    from src.export.epub3 import latex_to_mathml
    out = latex_to_mathml(r"\frac{a}{b}")
    assert "mfrac" in out


def test_latex_to_mathml_handles_greek():
    from src.export.epub3 import latex_to_mathml
    out = latex_to_mathml(r"\alpha + \beta")
    assert "α" in out
    assert "β" in out
