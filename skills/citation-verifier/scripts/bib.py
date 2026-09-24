#!/usr/bin/env python3
r"""BibTeX reader for the citation-verifier skill (Python 3 standard library).

  bib.py FILE.bib [FILE.bib ...]
      Prints a JSON list, one object per entry in file order: "citekey",
      "type" (the entry type, lower case) and every field under its lower-case
      name. A field that is itself named "citekey" or "type" is kept as
      "citekey_field" or "type_field".

Values: {braced}, "quoted" or bare (a number, an @string macro, jan..dec),
joined with #. Braces are counted as BibTeX counts them, so a value may contain
braces and an entry may close on the line of its last value. Entries may also
be delimited by ( ).

Decoding (every field except doi, url, eprint and file):
  - LaTeX accents to Unicode, braced or not: \" \' \` \^ \~ \= \. \u \v \H \c
    \k \r \d \b \t, as in {\c{S}}, \c S, \.{I}, \.I, {\"o}, \u{g}, \'{\i};
  - special letters \i \j \o \O \l \L \ss \aa \AA \ae \AE \oe \OE \dh \DH \dj
    \DJ \ng \NG \th \TH;
  - escaped characters \& \% \$ \# \_ \{ \}; Greek letters; a few text and
    math symbols (\textendash, \textquoteright, \pm, ...);
  - formatting commands keep their argument: \emph{x} and {\em x} give x;
  - protective braces are dropped ({ROHHAD} gives ROHHAD), $ ^ _ are dropped,
    ~ is a space, whitespace is collapsed, the result is NFC-normalised;
  - any other command is kept as written, with its braced argument.
doi, url, eprint and file are verbatim: only braces and the backslash of an
escaped character are removed.

Skipped: @comment, @preamble, and %-comment lines between entries and fields.

stderr: the number of entries, and a WARNING line for every entry that cannot
be parsed (with its line number; it is left out of the JSON), every duplicate
citekey and every repeated field (the first value is kept).
Exit status: 0 = no warnings; 1 = warnings; 2 = a file could not be read.
"""

import argparse
import json
import re
import sys
import unicodedata

# ------------------------------------------------------------------- LaTeX

# accent command -> combining character (control symbols and one-letter words)
ACCENTS = {
    '"': "̈", "'": "́", "`": "̀", "^": "̂", "~": "̃",
    "=": "̄", ".": "̇", "u": "̆", "v": "̌", "H": "̋",
    "c": "̧", "k": "̨", "r": "̊", "d": "̣", "b": "̱",
    "t": "͡",
}
# the accent alone, with an empty argument: \~{} in a URL is ~
SPACING = {'"': "¨", "'": "´", "`": "`", "^": "^", "~": "~", "=": "¯",
           ".": "˙", "u": "˘", "v": "ˇ", "H": "˝", "c": "¸",
           "k": "˛", "r": "˚"}
LETTERS = {"i": "ı", "j": "ȷ", "o": "ø", "O": "Ø", "l": "ł", "L": "Ł", "ss": "ß",
           "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ", "oe": "œ", "OE": "Œ",
           "dh": "ð", "DH": "Ð", "dj": "đ", "DJ": "Đ", "ng": "ŋ", "NG": "Ŋ",
           "th": "þ", "TH": "Þ"}
GREEK = dict(zip(
    "alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda "
    "mu nu xi pi varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi omega "
    "Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega".split(),
    "αβγδεεζηθϑικλμνξπϖρϱσςτυφφχψωΓΔΘΛΞΠΣΥΦΨΩ"))
SYMBOLS = {
    "textendash": "–", "textemdash": "—", "textquoteleft": "‘", "textquoteright": "’",
    "textquotedblleft": "“", "textquotedblright": "”", "textquotesingle": "'",
    "textquotedbl": '"', "textasciitilde": "~", "textasciicircum": "^",
    "textbackslash": "\\", "textbar": "|", "textless": "<", "textgreater": ">",
    "textunderscore": "_", "textdegree": "°", "textpm": "±", "textmu": "µ",
    "texttimes": "×", "textellipsis": "…", "ldots": "…", "dots": "…", "S": "§", "P": "¶",
    "textregistered": "®", "texttrademark": "™", "textcopyright": "©",
    "pm": "±", "times": "×", "cdot": "·", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "neq": "≠", "ne": "≠", "approx": "≈", "sim": "~", "infty": "∞",
    "circ": "°",  # as in $^\circ$C
}
KEEP_ARG = {"emph", "textit", "textbf", "textsl", "textsc", "textup", "textmd", "textrm",
            "textsf", "texttt", "textnormal", "textsuperscript", "textsubscript", "mbox",
            "hbox", "text", "mathrm", "mathit", "mathbf", "mathsf", "mathtt", "mathnormal",
            "ensuremath", "NoCaseChange"}
VERBATIM_ARG = {"url", "doi"}
DROP = {"em", "it", "bf", "sl", "sc", "rm", "sf", "tt", "up", "md", "normalfont", "itshape",
        "bfseries", "slshape", "scshape", "upshape", "mdseries", "rmfamily", "sffamily",
        "ttfamily", "relax", "protect", "ignorespaces", "unskip", "nobreak", "noindent"}


def _group_end(s, i):
    """Index of the } closing the { at s[i] (escaped braces do not count); len(s) if none."""
    depth = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(s)


def _skip_spaces(s, i):
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def _argument(s, i):
    """One macro argument from s[i] on (spaces skipped): {group}, command or character."""
    i = _skip_spaces(s, i)
    if i >= len(s) or s[i] == "}":
        return "", i
    if s[i] == "{":
        j = _group_end(s, i)
        return _decode(s[i + 1:j]), j + 1
    if s[i] == "\\":
        return _command(s, i)
    return s[i], i + 1


def _accent(cmd, arg):
    if not arg:
        return SPACING.get(cmd, "")
    k = 1  # the accent goes after the first character and its own combining marks
    while k < len(arg) and unicodedata.combining(arg[k]):
        k += 1
    base = {"ı": "i", "ȷ": "j"}.get(arg[0], arg[0])  # \'{\i} is í, not ı + accent
    return base + arg[1:k] + ACCENTS[cmd] + arg[k:]


def _verbatim(s):
    s = re.sub(r"\\([_%&#$~])", r"\1", s)
    return " ".join(s.replace("{", "").replace("}", "").split())


def _command(s, i):
    """Decode the command at s[i] (a backslash): (text, index after it)."""
    j = i + 1
    if j >= len(s):
        return "", j
    if not (s[j].isascii() and s[j].isalpha()):  # control symbol: \" \& \\ ...
        c = s[j]
        if c in ACCENTS:
            arg, end = _argument(s, j + 1)
            return _accent(c, arg), end
        if c in "\\ \t\r\n,;:>":
            return " ", j + 1
        if c in "-/@!":
            return "", j + 1
        return c, j + 1  # \& \% \$ \# \_ \{ \} and any other symbol
    k = j
    while k < len(s) and s[k].isascii() and s[k].isalpha():
        k += 1
    name, after = s[j:k], _skip_spaces(s, k)  # spaces after a control word are not text
    if name in ACCENTS:
        arg, end = _argument(s, after)
        return _accent(name, arg), end
    for table in (LETTERS, GREEK, SYMBOLS):
        if name in table:
            return table[name], after
    if name in DROP:
        return "", after
    braced = after < len(s) and s[after] == "{"
    if name in KEEP_ARG:
        return _argument(s, after) if braced else ("", after)
    if braced:
        end = _group_end(s, after)
        inner = s[after + 1:end]
        if name in VERBATIM_ARG:
            return _verbatim(inner), end + 1
        return "\\" + name + "{" + _decode(inner) + "}", end + 1  # unknown: keep it
    return "\\" + name + (" " if after > k else ""), after


def _decode(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            text, i = _command(s, i)
            out.append(text)
            continue
        if c == "{":
            j = _group_end(s, i)
            out.append(_decode(s[i + 1:j]))
            i = j + 1
            continue
        if c == "~":
            out.append(" ")
        elif c not in "}$^_":  # stray }, math shift, super- and subscript marks
            out.append(c)
        i += 1
    return "".join(out)


def decode(value):
    """LaTeX field value -> plain Unicode text."""
    return " ".join(unicodedata.normalize("NFC", _decode(value)).split())


# ------------------------------------------------------------------- BibTeX

class BibError(Exception):
    pass


MONTHS = dict(zip("jan feb mar apr may jun jul aug sep oct nov dec".split(),
                  "January February March April May June July August September "
                  "October November December".split()))
VERBATIM_FIELDS = {"doi", "url", "eprint", "file"}
NAME = re.compile(r"""[^\s"#%'(),={}]+""")  # field name, macro name, bare value
KEY = re.compile(r"""[^\s"#%'(),={}]+""")
TYPE = re.compile(r"@\s*([A-Za-z]\w*)\s*")
SKIP = re.compile(r"(?:\s|%[^\n]*)*")  # whitespace and %-comments
AT = re.compile(r"%[^\n]*|@")
NEXT_ENTRY = re.compile(r"\n[ \t]*@")
RUNAWAY = re.compile(r"\n[ \t]*@[A-Za-z]\w*\s*[{(]")  # a value that swallowed the next entry


class Parser:
    def __init__(self, text):
        self.s = text
        self.macros = dict(MONTHS)
        self.entries = []
        self.warnings = []

    def line(self, p):
        return self.s.count("\n", 0, p) + 1

    def skip(self, p):
        return SKIP.match(self.s, p).end()

    def expect(self, p, ch):
        p = self.skip(p)
        if not self.s.startswith(ch, p):
            raise BibError(f"expected {ch!r} on line {self.line(p)}")
        return p + 1

    def braced(self, p):  # s[p] == "{"; every brace counts, as in BibTeX
        depth = 0
        for q in range(p, len(self.s)):
            if self.s[q] == "{":
                depth += 1
            elif self.s[q] == "}":
                depth -= 1
                if depth == 0:
                    return self.s[p + 1:q], q + 1
        raise BibError("unbalanced braces")

    def quoted(self, p):  # s[p] == '"'; a " inside braces does not end the value
        depth = 0
        for q in range(p + 1, len(self.s)):
            c = self.s[q]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == '"' and depth == 0:
                return self.s[p + 1:q], q + 1
        raise BibError("unterminated quoted value")

    def value(self, p):
        parts = []
        while True:
            p = self.skip(p)
            c = self.s[p:p + 1]
            if c in ('{', '"'):
                part, p = self.braced(p) if c == "{" else self.quoted(p)
                if RUNAWAY.search(part):
                    raise BibError("unbalanced braces: a value runs into the next entry")
            else:
                m = NAME.match(self.s, p)
                if not m:
                    raise BibError(f"missing value on line {self.line(p)}")
                word, p = m.group(), m.end()
                part = word if word.isdigit() else self.macros.get(word.lower(), word)
            parts.append(part)
            p = self.skip(p)
            if not self.s.startswith("#", p):
                return "".join(parts), p
            p += 1

    def skip_group(self, p, closer):  # s[p] is the opening delimiter
        depth = 0
        for q in range(p + 1, len(self.s)):
            c = self.s[q]
            if c == "{":
                depth += 1
            elif c == "}" and depth:
                depth -= 1
            elif c == closer and depth == 0:
                return q + 1
        raise BibError(f"no closing {closer!r}")

    def entry(self, at):
        """Parse the @-item at s[at]; return the index after it."""
        m = TYPE.match(self.s, at)
        if not m:
            raise BibError("@ without an entry type")
        kind, p = m.group(1).lower(), m.end()
        opener = self.s[p:p + 1]
        if opener not in ("{", "("):
            if kind == "comment":  # BibTeX ignores "@comment text"
                return p
            raise BibError(f"@{m.group(1)} is not followed by {{ or (")
        closer = "}" if opener == "{" else ")"
        if kind in ("comment", "preamble"):
            return self.skip_group(p, closer)
        p = self.skip(p + 1)
        if kind == "string":
            m = NAME.match(self.s, p)
            if not m:
                raise BibError("@string without a name")
            name = m.group().lower()
            p = self.expect(m.end(), "=")
            self.macros[name], p = self.value(p)
            return self.expect(p, closer)
        m = KEY.match(self.s, p)
        if not m:
            raise BibError(f"@{kind} without a citekey")
        key, p = m.group(), self.skip(m.end())
        entry = {"citekey": key, "type": kind}
        if not self.s.startswith(closer, p):
            if not self.s.startswith(",", p):
                raise BibError(f"{key}: expected ',' after the citekey on line {self.line(p)}")
            while True:
                p = self.skip(p + 1)  # after a comma (several, or a trailing one, are fine)
                if self.s.startswith(",", p):
                    continue
                if self.s.startswith(closer, p):
                    break
                m = NAME.match(self.s, p)
                if not m:
                    raise BibError(f"{key}: expected a field name or {closer!r} "
                                   f"on line {self.line(p)}")
                field = m.group().lower()
                p = self.expect(m.end(), "=")
                raw, p = self.value(p)
                if field in ("citekey", "type"):
                    field += "_field"
                if field in entry:
                    self.warnings.append(f"line {self.line(p)}: {key}: repeated field "
                                         f"{field!r}, first value kept")
                else:
                    entry[field] = _verbatim(raw) if field in VERBATIM_FIELDS else decode(raw)
                p = self.skip(p)
                if self.s.startswith(closer, p):
                    break
                if not self.s.startswith(",", p):
                    raise BibError(f"{key}: expected ',' or {closer!r} after field "
                                   f"{field!r} on line {self.line(p)}")
        self.entries.append(entry)
        return p + 1

    def parse(self):
        p = 0
        while True:
            m = AT.search(self.s, p)
            while m and m.group() != "@":  # a %-comment line between entries
                m = AT.search(self.s, m.end())
            if not m:
                return self.entries
            at = m.start()
            try:
                p = self.entry(at)
            except BibError as exc:
                self.warnings.append(f"line {self.line(at)}: {exc}; entry left out")
                nxt = NEXT_ENTRY.search(self.s, at + 1)
                p = nxt.start() + 1 if nxt else len(self.s)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="bib.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bib", nargs="+", help=".bib file (UTF-8)")
    args = ap.parse_args(argv)
    entries, warnings = [], []
    for path in args.bib:
        try:
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
        except UnicodeDecodeError as exc:
            print(f"ERROR: {path} is not UTF-8 ({exc}); convert it first, "
                  f"e.g. iconv -f ISO-8859-9 -t UTF-8", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        parser = Parser(text)
        entries += parser.parse()
        warnings += [f"{path}: {w}" for w in parser.warnings]
    seen = set()
    for e in entries:
        if e["citekey"] in seen:
            warnings.append(f"duplicate citekey {e['citekey']!r}")
        seen.add(e["citekey"])
    json.dump(entries, sys.stdout, ensure_ascii=False, indent=2)
    print()
    print(f"{len(entries)} entries", file=sys.stderr)
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
