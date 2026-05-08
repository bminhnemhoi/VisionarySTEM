"""Test src/utils/helpers.py — region classification + filename helpers."""
import pytest


@pytest.mark.parametrize(
    "x,y,w,h,expected",
    [
        # corners
        (0, 0, 10, 10, "top-left"),
        (90, 0, 10, 10, "top-right"),
        (0, 90, 10, 10, "bottom-left"),
        (90, 90, 10, 10, "bottom-right"),
        # edges
        (40, 0, 20, 10, "top-center"),
        (40, 90, 20, 10, "bottom-center"),
        (0, 40, 10, 20, "center-left"),
        (90, 40, 10, 20, "center-right"),
        # center
        (40, 40, 20, 20, "center"),
    ],
)
def test_classify_region(x, y, w, h, expected):
    from src.utils.helpers import classify_region
    assert classify_region(x, y, w, h) == expected


def test_get_file_extension():
    from src.utils.helpers import get_file_extension
    assert get_file_extension("doc.PDF") == ".pdf"
    assert get_file_extension("photo.JPG") == ".jpg"
    assert get_file_extension("noext") == ""


def test_is_supported_file():
    from src.utils.helpers import is_supported_file
    assert is_supported_file("a.pdf")
    assert is_supported_file("a.PNG")
    assert not is_supported_file("a.docx")
    assert not is_supported_file("a.exe")


def test_format_time_ms():
    from src.utils.helpers import format_time_ms
    assert format_time_ms(500) == "500ms"
    assert format_time_ms(2500) == "2.5s"
    assert "m" in format_time_ms(125_000)
