#!/usr/bin/env python3
"""Citation report mechanics; no network or automatic semantic judgment.

combine ABSTRACT FULLTEXT retains separate abstract/full-text evidence.
summarize ROWS_JSON checks source bytes, exact claim/citekey bindings, stage codes
and an explicit bound human disposition. ready means supplied records are complete;
it does not authenticate a reviewer or certify scientific correctness.
key SENTENCE SOURCE_SHA256 [--citekey KEY] prints the exact claim/source binding.
review-key ROW_JSON prints the current row key for a reviewer disposition.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import fulltext

ABSTRACT_CODES = ("COMPATIBLE", "NOT_REPORTED", "CONTRADICTED", "UNAVAILABLE")
FULLTEXT_CODES = ("SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "SECONDARY",
                  "NO_FULLTEXT", "WRONG_PDF", "SOURCE_FAILED")
BACKS_CLAIM = ("SUPPORTED", "PARTIAL", "SECONDARY")
FIELDS = ("existence", "metadata", "notices", "authors", "claim")
BLOCKING = {
    "existence": ("FABRICATED", "DOI_NOT_REGISTERED"), "metadata": ("MISMATCH",),
    "notices": ("RETRACTED", "IS_NOTICE"), "authors": ("MISMATCH",),
    "claim": ("NOT_SUPPORTED", "PARTIAL", "SOURCE_FAILED", "WRONG_PDF")}
UNRESOLVED = {
    "existence": ("UNVERIFIABLE", "NOT_INDEXED"), "metadata": ("REVIEW", "UNVERIFIED"),
    "notices": ("CORRECTED", "EXPRESSION_OF_CONCERN", "UNVERIFIABLE"),
    "authors": ("REVIEW", "PARTIAL_MATCH"),
    "claim": ("REVIEW", "NO_FULLTEXT", "SECONDARY")}
CLEAR = {"existence": ("EXISTS",), "metadata": ("MATCH",), "notices": ("NONE_FOUND",),
         "authors": ("MATCH",), "claim": ("SUPPORTED",)}


def combine(abstract, fulltext):
    if abstract not in ABSTRACT_CODES or fulltext not in FULLTEXT_CODES:
        raise ValueError(f"unknown abstract/full-text verdict: {abstract!r}, {fulltext!r}")
    return "REVIEW" if abstract == "CONTRADICTED" and fulltext in BACKS_CLAIM else fulltext


def _value(row, field):
    value = row.get(field)
    if value is None and field == "claim":
        value = row.get("combined")
    return str(value or "").strip()


def row_group(row):
    values = {f: _value(row, f) for f in FIELDS}
    if any(values[f] in BLOCKING[f] for f in FIELDS):
        return "blocking"
    return "clear" if all(values[f] in CLEAR[f] for f in FIELDS) else "unresolved"


def unknown_codes(row):
    return [(f, _value(row, f)) for f in FIELDS
            if _value(row, f) not in BLOCKING[f] + UNRESOLVED[f] + CLEAR[f]]


def claim_key(sentence, source_sha256, citekey=""):
    data = [str(citekey), str(sentence), str(source_sha256).strip().lower()]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def is_stale(row, sentence, source_sha256):
    return row.get("key") != claim_key(sentence, source_sha256, row.get("citekey", ""))


def review_key(row):
    data = {"claim_key": row.get("key"), "stages": {f: _value(row, f) for f in FIELDS},
            "abstract_verdict": row.get("abstract_verdict"), "checked_at": row.get("checked_at"),
            "citation_purpose": row.get("citation_purpose", "positive_scientific_support"),
            "source_location": {k: row.get(k) for k in
                                ("source_path", "source_format", "reference_doi", "reference_title")},
            "claim_evidence": {k: row.get(k) for k in ("verdict", "pdf_page", "quote", "note")}}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _dated(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def binding_errors(row):
    errors = []
    for field in ("citekey", "sentence", "source_path"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            errors.append(f"missing {field}")
    digest = row.get("source_sha256", "")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        errors.append("missing or invalid source_sha256")
    elif row.get("source_path"):
        try:
            actual = hashlib.sha256(Path(row["source_path"]).read_bytes()).hexdigest()
            if actual != digest.lower():
                errors.append("source bytes changed")
        except (OSError, TypeError):
            errors.append("source file unavailable")
    if row.get("key") != claim_key(row.get("sentence", ""), digest, row.get("citekey", "")):
        errors.append("stale or missing exact claim/source/citekey key")
    if not _dated(row.get("checked_at")):
        errors.append("missing dated check revision")
    abstract, verdict = row.get("abstract_verdict"), row.get("verdict")
    if abstract not in ABSTRACT_CODES or verdict not in FULLTEXT_CODES:
        errors.append("missing abstract or full-text verdict")
    elif _value(row, "claim") != combine(abstract, verdict):
        errors.append("combined claim verdict disagrees with abstract/full-text")
    if verdict in BACKS_CLAIM:
        errors.extend(fulltext_errors(row))
    return errors


def fulltext_errors(row):
    """Re-execute mechanical quote/page checks; semantic support stays human."""
    page, quote = row.get("pdf_page"), row.get("quote")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        return ["quote requires a positive integer page"]
    if not isinstance(quote, str) or not quote.strip() or len(quote.split()) > 40:
        return ["quote must contain 1 to 40 words"]
    try:
        path = Path(row.get("source_path", ""))
        raw = path.read_bytes()
        kind = row.get("source_format")
        if raw.startswith(b"%PDF-") or path.suffix.lower() == ".pdf":
            if kind != "pdf":
                return ["PDF source requires source_format pdf"]
            doi, title = row.get("reference_doi"), row.get("reference_title")
            if not isinstance(doi, str) or not doi.strip() or not isinstance(title, str) or not title.strip():
                return ["PDF identity requires expected reference_doi and reference_title"]
            pages = fulltext.extract(str(path), False)
            layout = fulltext.extract(str(path), True)
            if fulltext.identify_pages(pages, doi, title, alt_pages=layout) != "MATCH":
                return ["PDF article identity did not match the reference"]
            variants = [pages, layout]
        elif kind == "text":
            variants = [[raw.decode("utf-8")]]
        else:
            return ["source format must explicitly be pdf or text"]
        if not any(page <= len(pages) and fulltext.find_quote([pages[page - 1]], quote)
                   for pages in variants):
            return ["quote absent from the specified source page"]
    except (OSError, UnicodeError, TypeError, fulltext.ExtractError) as exc:
        return [f"full-text evidence could not be read: {exc}"]
    return []


def valid_disposition(row):
    decision = row.get("disposition")
    if not isinstance(decision, dict):
        return False
    reviewer = decision.get("reviewer")
    return bool(isinstance(reviewer, str) and reviewer.strip()
                and reviewer == row.get("human") and _dated(decision.get("reviewed_at"))
                and decision.get("review_key") == review_key(row))


def notice_exception(row):
    if not valid_disposition(row):
        return False
    d = row["disposition"]
    if not isinstance(d.get("reason"), str) or not d["reason"].strip():
        return False
    if any(_value(row, f) not in CLEAR[f] for f in FIELDS if f != "notices"):
        return False
    notice = _value(row, "notices")
    if notice in ("RETRACTED", "IS_NOTICE"):
        return (row.get("citation_purpose") == "retraction_discussion"
                and d.get("decision") == "retain_retraction_discussion")
    return (notice in ("CORRECTED", "EXPRESSION_OF_CONCERN")
            and d.get("decision") == "accept_after_notice_review")


def summarize(rows):
    counts = {"blocking": 0, "unresolved": 0, "unsigned": 0}
    if not rows:
        counts["unresolved"] = 1
    for row in rows:
        group, bound = row_group(row), not binding_errors(row)
        if group == "blocking":
            if not (bound and notice_exception(row)):
                counts["blocking"] += 1
        elif not bound:
            counts["unresolved"] += 1
        elif group == "unresolved":
            if not notice_exception(row):
                counts["unresolved"] += 1
        elif not valid_disposition(row) or row["disposition"].get("decision") != "accept":
            counts["unsigned"] += 1
    counts["ready"] = not any(counts.values())
    return counts


def _read_json(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_combine(args):
    try:
        print(combine(args.abstract, args.fulltext))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_summarize(args):
    try:
        rows = _read_json(args.rows)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {args.rows}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        print("ERROR: expected a JSON list of objects", file=sys.stderr)
        return 2
    for n, row in enumerate(rows):
        errors = binding_errors(row) + [f"missing or unknown {f}: {v!r}" for f, v in unknown_codes(row)]
        for error in errors:
            print(f"WARNING: row {n} ({row.get('citekey', '?')}): {error}", file=sys.stderr)
    out = summarize(rows)
    print(json.dumps(out))
    return 0 if out["ready"] else 1


def cmd_key(args):
    sentence = sys.stdin.read() if args.sentence == "-" else args.sentence
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", args.sha256.strip()):
        print("ERROR: SOURCE_SHA256 must be 64 hex digits", file=sys.stderr)
        return 2
    print(claim_key(sentence, args.sha256, args.citekey))
    return 0


def cmd_review_key(args):
    try:
        row = _read_json(args.row)
        if not isinstance(row, dict):
            raise ValueError("expected one row object")
        errors = binding_errors(row)
        if errors:
            raise ValueError("; ".join(errors))
        print(review_key(row))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="report.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("combine")
    p.add_argument("abstract")
    p.add_argument("fulltext")
    p.set_defaults(func=cmd_combine)
    p = sub.add_parser("summarize")
    p.add_argument("rows", help='rows.json, or "-" for stdin')
    p.set_defaults(func=cmd_summarize)
    p = sub.add_parser("key")
    p.add_argument("sentence")
    p.add_argument("sha256")
    p.add_argument("--citekey", default="")
    p.set_defaults(func=cmd_key)
    p = sub.add_parser("review-key")
    p.add_argument("row", help='one current row JSON, or "-" for stdin')
    p.set_defaults(func=cmd_review_key)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
