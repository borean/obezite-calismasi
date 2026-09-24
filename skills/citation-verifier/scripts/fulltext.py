#!/usr/bin/env python3
"""Full-text helpers for the citation-verifier skill (Python 3 standard library).

Text is extracted with `pdftotext` (poppler) when it is on PATH, otherwise with
`pypdf` if it can be imported.

  fulltext.py pages PDF [--out FILE] [--layout]
      Page-separated text; each page starts with a line "=== PAGE n ===",
      where n is the 1-based PDF page index (not the printed journal page).
      Reading-order extraction; --layout gives the physical layout instead
      (useful for tables).

  fulltext.py quote PDF "QUOTE"            (QUOTE "-" reads it from stdin)
      Prints "FOUND pages=[..]" and exits 0, or "NOT_FOUND" and exits 1.
      Tolerated: line breaks, end-of-line hyphenation, ligatures and other
      NFKC compatibility forms, dash and quote variants, case, whitespace.
      Nothing else: the quote must really be in the text, starting and ending
      on word boundaries. Both the reading-order and the -layout extraction
      are searched.

  fulltext.py identify PDF --doi DOI --title TITLE
      Prints "MATCH" (exit 0) if the DOI appears on the first two pages or the
      title is >= 0.85 similar to text on the first page, else "NO_MATCH"
      (exit 1). The evidence goes to stderr.

Exit status 2: the PDF could not be read or the arguments are unusable.
"""

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import unicodedata

TITLE_THRESHOLD = 0.85
DOI_PAGES = 2
QUOTE_MAX_WORDS = 40


class ExtractError(Exception):
    pass


# ---------------------------------------------------------------- extraction

def _pdftotext(pdf, layout):
    cmd = ["pdftotext", "-enc", "UTF-8"] + (["-layout"] if layout else []) + [pdf, "-"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        msg = res.stderr.decode("utf-8", "replace").strip()
        raise ExtractError(f"pdftotext failed on {pdf}: {msg or 'exit ' + str(res.returncode)}")
    pages = res.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():  # every page ends with \f
        pages.pop()
    return pages


def _pypdf(pdf, layout):
    try:
        import pypdf
    except ImportError:
        raise ExtractError("neither pdftotext (poppler) nor pypdf is available: "
                           "install one (brew install poppler / pip install pypdf)")
    try:
        reader = pypdf.PdfReader(pdf)
        if reader.is_encrypted:
            reader.decrypt("")
        pages = []
        for page in reader.pages:
            text = None
            if layout:
                try:
                    text = page.extract_text(extraction_mode="layout")
                except TypeError:  # older pypdf without layout mode
                    text = None
            if text is None:
                text = page.extract_text()
            pages.append(text or "")
        return pages
    except Exception as exc:  # pypdf raises many exception types
        raise ExtractError(f"pypdf failed on {pdf}: {exc}")


def extract(pdf, layout=False, engine="auto"):
    """Return the text of each page (index 0 = PDF page 1)."""
    if engine in ("auto", "pdftotext") and shutil.which("pdftotext"):
        return _pdftotext(pdf, layout)
    if engine == "pdftotext":
        raise ExtractError("pdftotext not found on PATH")
    return _pypdf(pdf, layout)


# ------------------------------------------------------------- normalisation

_DASHES = "\u00ad\u2010\u2011\u2012\u2013\u2014\u2015\u2043\u2212\u2e3a\u2e3b\ufe58\ufe63\uff0d"
_SQUOTES = "\u2018\u2019\u201a\u201b\u2032\u2035\u2039\u203a\u0060\u00b4\uff07"
_DQUOTES = "\u201c\u201d\u201e\u201f\u2033\u2036\u00ab\u00bb\u301d\u301e\uff02"
_INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
_VARIANTS = {ord(c): "-" for c in _DASHES}
_VARIANTS.update({ord(c): "'" for c in _SQUOTES})
_VARIANTS.update({ord(c): '"' for c in _DQUOTES})
_VARIANTS.update({ord(c): None for c in _INVISIBLE})


def _chars(s):
    """Context-free part: dash/quote variants, NFKC (ligatures), case."""
    s = s.translate(_VARIANTS)  # before NFKC, which would split e.g. U+2033
    s = unicodedata.normalize("NFKC", s).translate(_VARIANTS)
    return s.casefold()


def _mark(ch):
    return unicodedata.category(ch).startswith("M")


def _is_word(ch):
    return ch.isalnum() or _mark(ch)


def _dehyphenate(chars, tags):
    """Drop a hyphen that is attached to the preceding word character and
    followed, directly or after a line break, by another word character
    ("e-mail", "hyphen-<newline>ation"), unless both neighbours are digits.

    poppler's reading-order mode already removes end-of-line hyphens ("IL-6"
    broken at the hyphen comes out as "IL6") while -layout keeps them, so both
    spellings must compare equal: "e-mail" = "email", "IL-6" = "IL6".
    Ranges keep their hyphen ("10-20" != "1020"), and so does a minus sign or
    dash with a space before it ("r = -0.5", "negatively -0.2"): a dropped
    minus sign never matches.
    """
    out_c, out_t = [], []
    i, n = 0, len(chars)
    while i < n:
        if chars[i] == "-" and out_c and _is_word(out_c[-1]):
            j = i + 1
            while j < n and chars[j].isspace():
                j += 1
            if j < n and _is_word(chars[j]) and not (out_c[-1].isdigit() and chars[j].isdigit()):
                i = j
                continue
        out_c.append(chars[i])
        out_t.append(tags[i])
        i += 1
    return out_c, out_t


def _squash(chars, tags):
    """Context-dependent part, keeping a source tag (page index) per char.

    After dehyphenation, whitespace runs (line breaks included) become one
    space, kept only between two word characters, so spacing around
    punctuation does not matter.
    """
    chars, tags = _dehyphenate(chars, tags)
    out_c, out_t = [], []
    i, n = 0, len(chars)
    while i < n:
        if chars[i].isspace():
            j = i
            while j < n and chars[j].isspace():
                j += 1
            if out_c and j < n and _is_word(out_c[-1]) and _is_word(chars[j]):
                out_c.append(" ")
                out_t.append(tags[i])
            i = j
        else:
            out_c.append(chars[i])
            out_t.append(tags[i])
            i += 1
    return "".join(out_c), out_t


def canonical(s):
    t = _chars(s)
    return _squash(t, [0] * len(t))[0]


def canonical_pages(pages):
    """Canonical text of the whole document plus the page index of each char."""
    chars, tags = [], []
    for idx, page in enumerate(pages):
        t = _chars(page)
        chars.extend(t)
        tags.extend([idx] * len(t))
        chars.append("\n")  # a page break is just whitespace
        tags.append(idx)
    return _squash(chars, tags)


# ------------------------------------------------------------------- quote

def find_quote(pages, quote):
    """Set of 0-based page indices covered by occurrences of `quote`."""
    doc, tags = canonical_pages(pages)
    q = canonical(quote)
    hits = set()
    if not q:
        return hits
    start = doc.find(q)
    while start != -1:
        end = start + len(q)
        ok_start = not _is_word(q[0]) or start == 0 or not _is_word(doc[start - 1])
        ok_end = not _is_word(q[-1]) or end == len(doc) or not _is_word(doc[end])
        if ok_start and ok_end:
            hits.update(tags[start:end])
        start = doc.find(q, start + 1)
    return hits


def cmd_quote(args):
    quote = sys.stdin.read() if args.quote == "-" else args.quote
    if not canonical(quote):
        print("ERROR: empty quote", file=sys.stderr)
        return 2
    words = len(quote.split())
    if words > QUOTE_MAX_WORDS:
        print(f"WARNING: quote has {words} words (limit {QUOTE_MAX_WORDS})", file=sys.stderr)
    hits = set()
    for layout in (False, True):
        hits |= find_quote(extract(args.pdf, layout, args.engine), quote)
    if hits:
        print(f"FOUND pages={sorted(i + 1 for i in hits)}")
        return 0
    print("NOT_FOUND")
    return 1


# ---------------------------------------------------------------- identify

def _doi_regex(doi):
    d = _chars(doi).strip()
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", d.replace("\\", ""))
    d = re.sub(r"\s+", "", d)
    if not d:
        return None
    # a DOI may be broken across lines, with or without a hyphen at the break
    body = r"(?:-?\s+)?".join(re.escape(c) for c in d)
    tail = r"(?![0-9])" if d[-1].isdigit() else r"(?![0-9a-z])"
    return re.compile(r"(?<![0-9])" + body + tail)


def _plain_title(title):
    t = re.sub(r"\\[A-Za-z]+\*?", " ", title)  # LaTeX commands: \emph, \textit ...
    t = re.sub(r"\\.", " ", t)                  # escapes: \& \% \'
    return re.sub(r"[{}$]", "", t)


def _words(s):
    return re.sub(r"\W+", " ", canonical(s)).split()


def title_similarity(title, page_text):
    """Best difflib ratio between the title and any similar-length word window."""
    tw, pw = _words(_plain_title(title)), _words(page_text)
    if not tw or not pw:
        return 0.0
    target, tset, n = " ".join(tw), set(tw), len(tw)
    prefix = [0]
    for w in pw:
        prefix.append(prefix[-1] + (w in tset))
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(target)
    best = 0.0
    for size in range(max(1, n - 3), n + 4):
        for i in range(max(1, len(pw) - size + 1)):
            j = min(len(pw), i + size)
            if prefix[j] - prefix[i] < n / 2:  # shares too few title words
                continue
            sm.set_seq1(" ".join(pw[i:j]))
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            best = max(best, sm.ratio())
    return best


def cmd_identify(args):
    if not (args.doi or args.title):
        print("ERROR: give --doi and/or --title", file=sys.stderr)
        return 2
    doi_re = _doi_regex(args.doi) if args.doi else None
    doi_page, best = None, 0.0
    for layout in (False, True):
        pages = extract(args.pdf, layout, args.engine)
        if doi_re and doi_page is None:
            for idx, page in enumerate(pages[:DOI_PAGES]):
                if doi_re.search(_chars(page)):
                    doi_page = idx + 1
                    break
        if args.title and pages:
            best = max(best, title_similarity(args.title, pages[0]))
    evidence = []
    if args.doi:
        evidence.append(f"doi: {'page ' + str(doi_page) if doi_page else 'not on pages 1-' + str(DOI_PAGES)}")
    if args.title:
        evidence.append(f"title similarity on page 1: {best:.2f} (threshold {TITLE_THRESHOLD})")
    print("; ".join(evidence), file=sys.stderr)
    if doi_page or best >= TITLE_THRESHOLD:
        print("MATCH")
        return 0
    print("NO_MATCH")
    return 1


# ------------------------------------------------------------------- pages

def cmd_pages(args):
    pages = extract(args.pdf, args.layout, args.engine)
    text = "".join(f"=== PAGE {i} ===\n{p.rstrip()}\n\n" for i, p in enumerate(pages, 1))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"{len(pages)} pages written to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    empty = [str(i) for i, p in enumerate(pages, 1) if len(p.strip()) < 20]
    if pages and len(empty) == len(pages):
        print("WARNING: no text layer (scanned PDF?)", file=sys.stderr)
    elif empty:
        print(f"WARNING: pages with (almost) no text: {', '.join(empty)}", file=sys.stderr)
    return 0


# -------------------------------------------------------------------- main

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--engine", choices=["auto", "pdftotext", "pypdf"], default="auto",
                        help="text extractor (default: pdftotext if present, else pypdf)")
    ap = argparse.ArgumentParser(prog="fulltext.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pages", parents=[common], help="page-separated text")
    p.add_argument("pdf")
    p.add_argument("--out", help="write to FILE instead of stdout")
    p.add_argument("--layout", action="store_true", help="physical layout instead of reading order")
    p.set_defaults(func=cmd_pages)
    p = sub.add_parser("quote", parents=[common], help="is QUOTE verbatim in the PDF?")
    p.add_argument("pdf")
    p.add_argument("quote", help='the quote, or "-" to read it from stdin')
    p.set_defaults(func=cmd_quote)
    p = sub.add_parser("identify", parents=[common], help="is PDF the cited paper?")
    p.add_argument("pdf")
    p.add_argument("--doi", default="")
    p.add_argument("--title", default="")
    p.set_defaults(func=cmd_identify)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (ExtractError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
