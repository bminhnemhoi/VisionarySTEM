"""
VisionarySTEM Braille Exporter — Sprint 6.2
=============================================
LaTeX → Unicode Braille (Nemeth-flavored) using built-in mapping.
Avoids dependency on `python-louis` (which needs native liblouis install).

For production: swap to liblouis when deploying on Linux server.
For demo/competition: Unicode braille (U+2800-U+28FF) renders fine in browsers
and pairs with `<bdo>` for screen readers.

Reference: research/findings/05-accessibility-standards.md
"""

from __future__ import annotations

import re

# ============================================================
# Vietnamese → Braille (grade 1 — simple mapping)
# ============================================================

# Standard 6-dot Vietnamese braille (no contractions)
# Letters: a-z mostly same as English. Tones use dot-7/8 for diacritics.
# This is a SIMPLIFIED mapping for demo. Production should use liblouis with vi-VN tables.

VIETNAMESE_BRAILLE_MAP = {
    "a": "⠁", "b": "⠃", "c": "⠉", "d": "⠙", "đ": "⠫",
    "e": "⠑", "f": "⠋", "g": "⠛", "h": "⠓", "i": "⠊",
    "j": "⠚", "k": "⠅", "l": "⠇", "m": "⠍", "n": "⠝",
    "o": "⠕", "p": "⠏", "q": "⠟", "r": "⠗", "s": "⠎",
    "t": "⠞", "u": "⠥", "v": "⠧", "w": "⠺", "x": "⠭",
    "y": "⠽", "z": "⠵",
    # Vietnamese vowels with diacritics (simplified — ignore tones for now)
    "á": "⠁", "à": "⠁", "ả": "⠁", "ã": "⠁", "ạ": "⠁",
    "â": "⠡", "ấ": "⠡", "ầ": "⠡", "ẩ": "⠡", "ẫ": "⠡", "ậ": "⠡",
    "ă": "⠩", "ắ": "⠩", "ằ": "⠩", "ẳ": "⠩", "ẵ": "⠩", "ặ": "⠩",
    "é": "⠑", "è": "⠑", "ẻ": "⠑", "ẽ": "⠑", "ẹ": "⠑",
    "ê": "⠣", "ế": "⠣", "ề": "⠣", "ể": "⠣", "ễ": "⠣", "ệ": "⠣",
    "í": "⠊", "ì": "⠊", "ỉ": "⠊", "ĩ": "⠊", "ị": "⠊",
    "ó": "⠕", "ò": "⠕", "ỏ": "⠕", "õ": "⠕", "ọ": "⠕",
    "ô": "⠹", "ố": "⠹", "ồ": "⠹", "ổ": "⠹", "ỗ": "⠹", "ộ": "⠹",
    "ơ": "⠳", "ớ": "⠳", "ờ": "⠳", "ở": "⠳", "ỡ": "⠳", "ợ": "⠳",
    "ú": "⠥", "ù": "⠥", "ủ": "⠥", "ũ": "⠥", "ụ": "⠥",
    "ư": "⠾", "ứ": "⠾", "ừ": "⠾", "ử": "⠾", "ữ": "⠾", "ự": "⠾",
    "ý": "⠽", "ỳ": "⠽", "ỷ": "⠽", "ỹ": "⠽", "ỵ": "⠽",
    # Numbers (with number indicator ⠼ before digit)
    "0": "⠚", "1": "⠁", "2": "⠃", "3": "⠉", "4": "⠙",
    "5": "⠑", "6": "⠋", "7": "⠛", "8": "⠓", "9": "⠊",
    # Punctuation
    " ": " ",
    ".": "⠲", ",": "⠂", ";": "⠆", ":": "⠒",
    "!": "⠖", "?": "⠦", "(": "⠐⠣", ")": "⠐⠜",
    "+": "⠬", "-": "⠤", "*": "⠐⠔", "/": "⠌",
    "=": "⠨⠅", "<": "⠐⠅", ">": "⠨⠂",
    "[": "⠨⠣", "]": "⠨⠜", "{": "⠸⠣", "}": "⠸⠜",
}

CAPITAL_INDICATOR = "⠠"
NUMBER_INDICATOR = "⠼"


def text_to_braille_unicode(text: str) -> str:
    """
    Convert Vietnamese text to Unicode Braille.
    Simple grade 1 — no contractions, no tone marks.
    """
    if not text:
        return ""
    result: list[str] = []
    in_number = False
    for ch in text:
        lower = ch.lower()
        if ch.isdigit():
            if not in_number:
                result.append(NUMBER_INDICATOR)
                in_number = True
            result.append(VIETNAMESE_BRAILLE_MAP.get(lower, "⠿"))
            continue
        else:
            in_number = False

        if ch.isupper() and lower in VIETNAMESE_BRAILLE_MAP:
            result.append(CAPITAL_INDICATOR)
            result.append(VIETNAMESE_BRAILLE_MAP[lower])
        elif lower in VIETNAMESE_BRAILLE_MAP:
            result.append(VIETNAMESE_BRAILLE_MAP[lower])
        elif ch == "\n" or ch == "\t":
            result.append(ch)
        else:
            # Unknown char — emit blank cell
            result.append("⠿")
    return "".join(result)


# ============================================================
# LaTeX → Nemeth-flavored Unicode braille
# ============================================================

# Common math symbols — partial Nemeth mapping
MATH_BRAILLE_MAP = {
    "+": "⠬",
    "-": "⠤",
    "*": "⠐⠔",
    "/": "⠌",
    "=": "⠨⠅",
    "<": "⠐⠅",
    ">": "⠨⠂",
    "(": "⠐⠣",
    ")": "⠐⠜",
    "[": "⠨⠣",
    "]": "⠨⠜",
    "^": "⠘",  # superscript indicator
    "_": "⠰",  # subscript indicator
    "\\frac": "⠹",  # numerator-denominator opener
    "\\sqrt": "⠜",  # radical
    "\\sum": "⠨⠠⠎",  # sigma
    "\\int": "⠮",  # integral
    "\\infty": "⠼⠳",
    "\\pi": "⠨⠏",
    "\\alpha": "⠨⠁",
    "\\beta": "⠨⠃",
    "\\gamma": "⠨⠛",
    "\\delta": "⠨⠙",
    "\\theta": "⠨⠹",
    "\\lambda": "⠨⠇",
    "\\mu": "⠨⠍",
    "\\sigma": "⠨⠎",
    "\\partial": "⠈⠙",
    "\\cdot": "⠐⠔",
    "\\times": "⠐⠭",
}


def latex_to_braille(latex: str) -> str:
    """
    LaTeX → Unicode Braille (Nemeth-flavored, simplified).

    NOT a full Nemeth conversion — production needs liblouis with `nemeth.dis` table.
    For demo, this is enough to show "we can do braille output" to judges.
    """
    if not latex:
        return ""

    # Strip $...$ delimiters
    latex = latex.strip()
    latex = re.sub(r"^\$+|\$+$", "", latex)
    latex = re.sub(r"\\\(|\\\)|\\\[|\\\]", "", latex)

    result: list[str] = []
    i = 0
    while i < len(latex):
        # Try multi-char macros first (longest match)
        matched = False
        for macro in sorted(MATH_BRAILLE_MAP.keys(), key=len, reverse=True):
            if macro.startswith("\\") and latex[i:].startswith(macro):
                result.append(MATH_BRAILLE_MAP[macro])
                i += len(macro)
                matched = True
                break
        if matched:
            continue

        ch = latex[i]
        if ch in MATH_BRAILLE_MAP:
            result.append(MATH_BRAILLE_MAP[ch])
        elif ch == "{" or ch == "}":
            # Group delimiter — skip in basic braille
            pass
        elif ch.isdigit():
            result.append(NUMBER_INDICATOR + VIETNAMESE_BRAILLE_MAP.get(ch, "⠿"))
        elif ch.isalpha():
            lower = ch.lower()
            if ch.isupper():
                result.append(CAPITAL_INDICATOR + VIETNAMESE_BRAILLE_MAP.get(lower, "⠿"))
            else:
                result.append(VIETNAMESE_BRAILLE_MAP.get(lower, "⠿"))
        elif ch.isspace():
            result.append(" ")
        elif ch == "\\":
            # Unknown macro — skip
            i += 1
            while i < len(latex) and latex[i].isalpha():
                i += 1
            continue
        else:
            result.append("⠿")
        i += 1
    return "".join(result)
