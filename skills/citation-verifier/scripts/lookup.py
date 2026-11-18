#!/usr/bin/env python3
"""Database lookups for the citation-verifier skill (Python 3 standard library).

  lookup.py doi DOI
      Is the DOI registered? Asks the doi.org handle API
      (https://doi.org/api/handles/DOI) and never contacts the publisher:
      publishers such as Wiley, NEJM and MDPI answer automated requests with
      HTTP 403, so following the DOI redirect makes real DOIs look broken.
      Prints exactly one word:
        RESOLVES      registered (handle responseCode 1)                 exit 0
        NOT_FOUND     not registered (responseCode 100, HTTP 404)        exit 1
        UNVERIFIABLE  network error, timeout or any other answer         exit 2
      The reason for UNVERIFIABLE goes to stderr. A "https://doi.org/" prefix
      (the rest is then percent-decoded) or a "doi:" prefix is removed first.

  lookup.py crossref DOI
      Does Crossref have a record for the DOI? Asks the Crossref REST API
      (https://api.crossref.org/works/DOI). Prints the status on the first line:
        FOUND         a record; the API response follows on the second line
                      as JSON, without the record's reference list         exit 0
        NOT_FOUND     no record (HTTP 404)                                 exit 1
        UNVERIFIABLE  network error, timeout or any other answer           exit 2
      NOT_FOUND does not show that the DOI is unregistered: other agencies,
      such as DataCite and mEDRA, register DOIs that Crossref does not know
      (the doi subcommand asks the DOI registry itself). The reason for
      UNVERIFIABLE goes to stderr. Prefixes are removed as for doi.

  lookup.py pubmed --title TITLE [--author SURNAME]     (TITLE "-" reads it from stdin)
      Searches PubMed through the E-utilities API (esearch.fcgi) with the term
      TITLE[Title] AND SURNAME[Author]; if that finds nothing, with TITLE[Title]
      alone. The term is URL-encoded as a whole. Double quotes, parentheses,
      square brackets and upper-case AND/OR/NOT are PubMed query syntax, so they
      are removed from TITLE and SURNAME (the words are put in lower case).
      Prints one JSON object:
        status   FOUND (exit 0), NOT_IN_PUBMED (exit 1) or UNVERIFIABLE (exit 2)
        search   "title+author" or "title": the search the result comes from
        count    hits of that search
        pmids    their PMIDs (at most 20)
        term     the term sent
        error    why, with UNVERIFIABLE
      NCBI allows 3 requests per second without an API key; the fallback
      search waits 0.4 s.

  lookup.py existence --doi S --crossref S --pubmed S --openalex S
      Step 3's existence verdict, from the statuses the lookups gave:
        --doi       RESOLVES, NOT_FOUND, UNVERIFIABLE, or NONE for no DOI  (2a)
        --crossref  FOUND, NOT_FOUND, UNVERIFIABLE or SKIPPED              (2b)
        --pubmed    FOUND, NOT_IN_PUBMED, UNVERIFIABLE or SKIPPED          (2c)
        --openalex  FOUND, NOT_FOUND, UNVERIFIABLE or SKIPPED              (2d)
      Prints exactly one word, from the first rule that applies:
        1. DOI RESOLVES, or Crossref FOUND               EXISTS
        2. PubMed or OpenAlex FOUND (a title match)      DOI_NOT_REGISTERED if the
                                                         DOI is NOT_FOUND, else EXISTS
        3. DOI, Crossref, PubMed or OpenAlex             UNVERIFIABLE
           UNVERIFIABLE, or PubMed or OpenAlex
           SKIPPED (a title search not done),
           with or without a DOI
        4. DOI NOT_FOUND                                 FABRICATED
        5. no DOI                                        NOT_INDEXED
      FABRICATED therefore needs every check to have run and found nothing: DOI
      NOT_FOUND, Crossref NOT_FOUND or SKIPPED, PubMed NOT_IN_PUBMED and
      OpenAlex NOT_FOUND. Exit 0; an unknown or missing value is a usage error
      (exit 2). No network access.

  lookup.py authors [--et-al] [SURNAME ...] [--authors-json FILE]
      Stdin is saved Crossref output. A JSON list of {family,given} or {name}
      objects checks full ordered identities. Positional names check surnames.
        MATCH          complete ordered person/group identities match
        PARTIAL_MATCH  surname-only match, or an et-al prefix with omitted authors
        MISMATCH       conflicting names or order
        REVIEW         missing names, initials ambiguity or unresolved truncation
      Prints status and JSON detail. A surname/prefix match never establishes
      full author identity. Exit 0; malformed/missing source data exits 2.

  lookup.py notices                                     (stdin: crossref output)
      Publication notices in the Crossref record. Crossref lists the notices
      about an article under "updated-by"; "update-to" marks the record itself
      as a notice. Prints the status on the first line, the first that applies:
        IS_NOTICE              the record has update-to: it is a notice itself
        RETRACTED              retraction, partial_retraction, withdrawal, removal
        EXPRESSION_OF_CONCERN  expression_of_concern
        CORRECTED              correction, corrigendum, erratum, addendum,
                               clarification
        NONE_FOUND             none of these
      then JSON {"status", "items": [{"type", "doi", "date", "source", "kind"}]}:
      Crossref's update type, the notice's DOI (for update-to: the DOI of the
      article the record is a notice about), the update date (YYYY-MM-DD),
      who reported it (publisher, retraction-watch) and the status the item
      gives. Exit 0. Without a Crossref record on stdin: UNVERIFIABLE, exit 2.

      authors and notices read the output of `lookup.py crossref DOI` (the
      FOUND line, then the JSON line) or the JSON alone.

  lookup.py pubmed-notices PMID
      The same statuses from PubMed (E-utilities efetch, XML). PublicationType
      "Retracted Publication" gives RETRACTED, "Retraction of Publication"
      IS_NOTICE. CommentsCorrections: RetractionIn and RetractedandRepublishedIn
      give RETRACTED, ExpressionOfConcernIn EXPRESSION_OF_CONCERN, ErratumIn
      and CorrectedandRepublishedIn CORRECTED; RetractionOf,
      ExpressionOfConcernFor and ErratumFor IS_NOTICE. Prints the status, then
      JSON {"status", "pmid", "publication_types",
      "items": [{"kind", "ref_type", "pmid", "ref_source"}]}. Exit 0; a
      network error, an HTTP error or an answer without the record prints
      UNVERIFIABLE (exit 2).

Every request times out after 15 seconds.
"""

import argparse
import http.client
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

TIMEOUT = 15
NCBI_PAUSE = 0.4
USER_AGENT = "citation-verifier/1.2 (Claude Code skill)"
HANDLE_API = "https://doi.org/api/handles/"
CROSSREF_API = "https://api.crossref.org/works/"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NETWORK_ERRORS = (OSError, http.client.HTTPException)  # URLError and timeouts are OSErrors


def get_body(url, accept="application/json"):
    """(HTTP status, body bytes). Network failures raise NETWORK_ERRORS."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a body
        return exc.code, exc.read()


def get_json(url):
    """(HTTP status, parsed JSON or None). Network failures raise NETWORK_ERRORS."""
    status, body = get_body(url)
    try:
        return status, json.loads(body)
    except ValueError:
        return status, None


# ---------------------------------------------------------------------- doi

def clean_doi(raw):
    s = raw.strip()
    m = re.match(r"https?://(?:dx\.)?doi\.org/", s, re.I)
    if m:
        return urllib.parse.unquote(s[m.end():]).strip()
    return re.sub(r"^doi:\s*", "", s, flags=re.I)


def cmd_doi(args):
    doi = clean_doi(args.doi)
    if not doi:
        print("UNVERIFIABLE")
        print("ERROR: empty DOI", file=sys.stderr)
        return 2
    url = HANDLE_API + urllib.parse.quote(doi, safe="/")
    try:
        status, data = get_json(url)
    except NETWORK_ERRORS as exc:
        print("UNVERIFIABLE")
        print(f"doi.org: {exc}", file=sys.stderr)
        return 2
    code = data.get("responseCode") if isinstance(data, dict) else None
    if code == 1:
        print("RESOLVES")
        return 0
    if code == 100:  # the handle server says so; comes with HTTP 404
        print("NOT_FOUND")
        return 1
    print("UNVERIFIABLE")
    print(f"doi.org: HTTP {status}, responseCode {code}", file=sys.stderr)
    return 2


# ----------------------------------------------------------------- crossref

def cmd_crossref(args):
    doi = clean_doi(args.doi)
    if not doi:
        print("UNVERIFIABLE")
        print("ERROR: empty DOI", file=sys.stderr)
        return 2
    try:
        status, data = get_json(CROSSREF_API + urllib.parse.quote(doi, safe="/"))
    except NETWORK_ERRORS as exc:
        print("UNVERIFIABLE")
        print(f"api.crossref.org: {exc}", file=sys.stderr)
        return 2
    record = data.get("message") if isinstance(data, dict) else None
    if status == 200 and isinstance(record, dict):
        record.pop("reference", None)  # the cited works: long, and not compared
        print("FOUND")
        print(json.dumps(data, ensure_ascii=False))
        return 0
    if status == 404:  # Crossref answers "Resource not found."
        print("NOT_FOUND")
        return 1
    print("UNVERIFIABLE")
    print(f"api.crossref.org: HTTP {status}", file=sys.stderr)
    return 2


# ------------------------------------------------------------------- pubmed

def pubmed_words(s):
    s = re.sub(r'["()\[\]]', " ", s)
    s = re.sub(r"\b(?:AND|OR|NOT)\b", lambda m: m.group().lower(), s)
    return " ".join(s.split())


def esearch(term):
    query = urllib.parse.urlencode({"db": "pubmed", "term": term, "retmode": "json",
                                    "retmax": 20, "tool": "citation-verifier"})
    status, data = get_json(ESEARCH + "?" + query)
    result = data.get("esearchresult") if isinstance(data, dict) else None
    if status != 200 or not isinstance(result, dict):
        detail = data.get("error") if isinstance(data, dict) else None
        raise LookupError(f"HTTP {status}" + (f": {detail}" if detail else ""))
    if "ERROR" in result:
        raise LookupError(result["ERROR"])
    return int(result.get("count", 0)), result.get("idlist", [])


def cmd_pubmed(args):
    title = pubmed_words(sys.stdin.read() if args.title == "-" else args.title)
    author = pubmed_words(args.author)
    if not title:
        print(json.dumps({"status": "UNVERIFIABLE", "error": "empty title"}))
        return 2
    searches = [("title", f"{title}[Title]")]
    if author:
        searches.insert(0, ("title+author", f"{title}[Title] AND {author}[Author]"))
    for n, (label, term) in enumerate(searches):
        if n:
            time.sleep(NCBI_PAUSE)
        try:
            count, pmids = esearch(term)
        except (LookupError, ValueError, *NETWORK_ERRORS) as exc:
            out = {"status": "UNVERIFIABLE", "search": label, "term": term, "error": str(exc)}
            print(json.dumps(out, ensure_ascii=False))
            return 2
        if count:
            break
    out = {"status": "FOUND" if count else "NOT_IN_PUBMED", "search": label,
           "count": count, "pmids": pmids, "term": term}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if count else 1


# ---------------------------------------------------------------- existence

DOI_STATUSES = ("RESOLVES", "NOT_FOUND", "UNVERIFIABLE", "NONE")
SEARCH_STATUSES = ("FOUND", "NOT_FOUND", "UNVERIFIABLE", "SKIPPED")  # Crossref, OpenAlex
PUBMED_STATUSES = ("FOUND", "NOT_IN_PUBMED", "UNVERIFIABLE", "SKIPPED")


def existence(doi, crossref, pubmed, openalex):
    """Step 3's existence verdict; the rules are tried in this order."""
    if doi == "RESOLVES" or crossref == "FOUND":
        return "EXISTS"
    if "FOUND" in (pubmed, openalex):  # the paper, found by its title
        return "DOI_NOT_REGISTERED" if doi == "NOT_FOUND" else "EXISTS"
    # Only a complete set of negative answers proves anything; a failed lookup
    # or a title search that was not done (with or without a DOI) does not.
    if (doi not in ("NOT_FOUND", "NONE") or crossref not in ("NOT_FOUND", "SKIPPED")
            or pubmed != "NOT_IN_PUBMED" or openalex != "NOT_FOUND"):
        return "UNVERIFIABLE"
    if doi == "NOT_FOUND":
        return "FABRICATED"  # doi.org is authoritative for the DOI itself
    return "NOT_INDEXED"  # no DOI, and no database has the title


def cmd_existence(args):
    print(existence(args.doi, args.crossref, args.pubmed, args.openalex))
    return 0


# ------------------------------------------------------------------ authors

# letters NFKD leaves whole: Turkish ı/İ, Nordic ø/æ, Polish ł, South Slavic đ, Icelandic þ/ð
UNDECOMPOSED = str.maketrans({"ı": "i", "İ": "I", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE",
                              "œ": "oe", "Œ": "OE", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
                              "þ": "th", "Þ": "TH", "ð": "d", "Ð": "D", "ß": "ss"})


def normalize_surname(s):
    """A surname for comparison: Turkish ı/İ as i/I (U+0131 has no Unicode
    decomposition, so this comes before NFKD), accents and other combining
    marks dropped, case folded, spaces and punctuation removed."""
    s = str(s or "").translate(UNDECOMPOSED)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("M"))
    return "".join(ch for ch in s.casefold() if ch.isalnum())


def compare_authors(cited, crossref_authors, et_al=False):
    """Ordered person/group identities. Strings check surnames only."""
    if not isinstance(crossref_authors, list) or not crossref_authors or not cited:
        return {"status": "REVIEW", "detail": "missing cited or Crossref authors"}
    families_only, ambiguous = False, False
    for pos, (raw, remote) in enumerate(zip(cited, crossref_authors), 1):
        local = raw if isinstance(raw, dict) else {"family": str(raw)}
        if not isinstance(remote, dict):
            return {"status": "REVIEW", "detail": f"malformed Crossref author {pos}"}
        if local.get("name") or remote.get("name"):
            if not local.get("name") or not remote.get("name"):
                return {"status": "REVIEW", "detail": f"group author {pos} needs its complete name"}
            if normalize_surname(local["name"]) != normalize_surname(remote["name"]):
                return {"status": "MISMATCH", "detail": f"group author {pos} differs"}
            continue
        left, right = local.get("family", ""), remote.get("family", "")
        if not str(left).strip() or not str(right).strip():
            return {"status": "REVIEW", "detail": f"missing surname at position {pos}"}
        if normalize_surname(left) != normalize_surname(right):
            return {"status": "MISMATCH", "detail": f"author {pos}: cited {left!r}, Crossref {right!r}"}
        lg, rg = str(local.get("given") or "").strip(), str(remote.get("given") or "").strip()
        if not lg or not rg:
            families_only = True
            continue
        if normalize_surname(lg) == normalize_surname(rg):
            # Matching initials are compatible, not a full given-name check.
            tokens = re.findall(r"[^\W\d_]+", lg, re.UNICODE)
            if tokens and all(len(t) == 1 for t in tokens):
                ambiguous = True
            continue
        lt, rt = re.findall(r"[^\W\d_]+", lg, re.UNICODE), re.findall(r"[^\W\d_]+", rg, re.UNICODE)
        if lt and rt and any(len(t) == 1 for t in lt + rt):
            if all(normalize_surname(a)[0] == normalize_surname(b)[0] for a, b in zip(lt, rt)):
                ambiguous = True
                continue
        return {"status": "MISMATCH", "detail": f"author {pos}: incompatible given names {lg!r}, {rg!r}"}
    n, m = len(cited), len(crossref_authors)
    if n < m:
        if et_al:
            return {"status": "PARTIAL_MATCH", "detail": f"{n} names match in order; {m-n} omitted authors were not checked"}
        return {"status": "REVIEW", "detail": f"{n} of Crossref's {m} authors cited, without et al."}
    if n > m:
        return {"status": "REVIEW", "detail": f"{n} authors cited, Crossref lists {m}"}
    if families_only:
        return {"status": "PARTIAL_MATCH", "detail": f"all {n} surnames match in order; given names were not checked"}
    if ambiguous:
        return {"status": "REVIEW", "detail": "ordered names are compatible, but initials do not establish full given-name identity"}
    return {"status": "MATCH", "detail": f"all {n} complete author identities match, in order"}


# ------------------------------------------------------------------ notices

NOTICE_ORDER = ("IS_NOTICE", "RETRACTED", "EXPRESSION_OF_CONCERN", "CORRECTED")  # most serious first
CROSSREF_NOTICE_KINDS = {
    "retraction": "RETRACTED", "partial_retraction": "RETRACTED",
    "withdrawal": "RETRACTED", "removal": "RETRACTED",
    "expression_of_concern": "EXPRESSION_OF_CONCERN",
    "correction": "CORRECTED", "corrigendum": "CORRECTED", "erratum": "CORRECTED",
    "addendum": "CORRECTED", "clarification": "CORRECTED",
}
PUBMED_NOTICE_KINDS = {  # CommentsCorrections RefType
    "RetractionIn": "RETRACTED", "RetractedandRepublishedIn": "RETRACTED",
    "ExpressionOfConcernIn": "EXPRESSION_OF_CONCERN",
    "ErratumIn": "CORRECTED", "CorrectedandRepublishedIn": "CORRECTED",
    "RetractionOf": "IS_NOTICE", "ExpressionOfConcernFor": "IS_NOTICE", "ErratumFor": "IS_NOTICE",
}
PUBMED_TYPE_KINDS = {"Retracted Publication": "RETRACTED", "Retraction of Publication": "IS_NOTICE"}


def notice_status(kinds):
    """The most serious of the kinds, or NONE_FOUND."""
    return next((s for s in NOTICE_ORDER if s in kinds), "NONE_FOUND")


def _update_date(update):
    """YYYY-MM-DD (or shorter) from an update's "updated" date, else None."""
    updated = update.get("updated")
    if not isinstance(updated, dict):
        return None
    if updated.get("date-time"):
        return str(updated["date-time"])[:10]
    parts = [p for p in ((updated.get("date-parts") or [[]])[0] or []) if p is not None]
    if not parts:
        return None
    return "-".join([str(parts[0]).zfill(4)] + [str(p).zfill(2) for p in parts[1:3]])


def notices(record):
    """{"status", "items"}: the publication notices in a Crossref work record
    (the API's "message"). Notices about the article are under "updated-by";
    "update-to" means the record is itself a notice (kind IS_NOTICE)."""
    items = []
    for field in ("updated-by", "update-to"):
        for update in record.get(field) or []:
            if not isinstance(update, dict):
                continue
            utype = re.sub(r"[\s-]+", "_", str(update.get("type") or "").strip().lower())
            kind = "IS_NOTICE" if field == "update-to" else CROSSREF_NOTICE_KINDS.get(utype)
            items.append({"type": utype, "doi": str(update.get("DOI") or ""),
                          "date": _update_date(update), "source": update.get("source"),
                          "kind": kind})
    return {"status": notice_status({i["kind"] for i in items}), "items": items}


def pubmed_notices(xml_text):
    """{"status", "pmid", "publication_types", "items"} from PubMed efetch XML
    (str or bytes). ValueError if it holds no PubMed record."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"not PubMed XML: {exc}") from None
    article = next((e for e in root.iter() if e.tag in ("PubmedArticle", "PubmedBookArticle")), None)
    if article is None:
        raise ValueError("no PubMed record in the answer")
    pmid = (article.findtext("MedlineCitation/PMID") or article.findtext("BookDocument/PMID") or "").strip()
    types = [t.text.strip() for t in article.iter("PublicationType") if t.text and t.text.strip()]
    items = []
    for cc in article.iter("CommentsCorrections"):
        ref_type = cc.get("RefType", "")
        if ref_type in PUBMED_NOTICE_KINDS:
            items.append({"kind": PUBMED_NOTICE_KINDS[ref_type], "ref_type": ref_type,
                          "pmid": (cc.findtext("PMID") or "").strip() or None,
                          "ref_source": " ".join((cc.findtext("RefSource") or "").split())})
    kinds = {i["kind"] for i in items} | {PUBMED_TYPE_KINDS[t] for t in types if t in PUBMED_TYPE_KINDS}
    return {"status": notice_status(kinds), "pmid": pmid or None,
            "publication_types": types, "items": items}


# ----------------------------------------------------------------- abstract

def abstract_from_openalex(inverted_index):
    """The abstract text from OpenAlex's abstract_inverted_index (word -> positions)."""
    words = {}
    for word, positions in (inverted_index or {}).items():
        for p in positions or []:
            words[p] = word
    return " ".join(words[p] for p in sorted(words))


# ---------------------------------------------------- authors/notices: CLI

def crossref_record(text):
    """The work record in `lookup.py crossref` output (a FOUND line, then
    JSON) or in bare JSON (the API response or the record). ValueError if none."""
    text = text.strip()
    if not text:
        raise ValueError("stdin is empty: pipe in the output of `lookup.py crossref DOI`")
    first, _, rest = text.partition("\n")
    if first.strip() in ("NOT_FOUND", "UNVERIFIABLE"):
        raise ValueError(f"no Crossref record: lookup.py crossref printed {first.strip()}")
    if first.strip() == "FOUND":
        text = rest
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("stdin is neither `lookup.py crossref` output nor JSON") from None
    record = data.get("message", data) if isinstance(data, dict) else None
    if not isinstance(record, dict):
        raise ValueError("the JSON on stdin is not a Crossref record")
    return record


def _status_and_json(out, code=0):
    print(out["status"])
    print(json.dumps(out, ensure_ascii=False))
    return code


def cmd_authors(args):
    try:
        record = crossref_record(sys.stdin.read())
    except ValueError as exc:
        return _status_and_json({"status": "REVIEW", "detail": f"{exc}; compare the authors by hand"}, 2)
    # A JSON input preserves given and corporate names; the legacy positional
    # interface intentionally remains a partial surname-only comparison.
    cited = args.surnames
    if args.authors_json:
        try:
            with open(args.authors_json, encoding="utf-8") as fh:
                cited = json.load(fh)
            if not isinstance(cited, list) or not all(isinstance(a, dict) for a in cited):
                raise ValueError("authors JSON must be a list of name objects")
        except (OSError, ValueError) as exc:
            return _status_and_json({"status": "REVIEW", "detail": str(exc)}, 2)
    return _status_and_json(compare_authors(cited, record.get("author"), et_al=args.et_al))


def cmd_notices(args):
    try:
        record = crossref_record(sys.stdin.read())
    except ValueError as exc:
        return _status_and_json({"status": "UNVERIFIABLE", "error": str(exc)}, 2)
    return _status_and_json(notices(record))


def cmd_pubmed_notices(args):
    pmid = re.sub(r"^pmid:?\s*", "", args.pmid.strip(), flags=re.I)
    if not re.fullmatch(r"[0-9]+", pmid):
        return _status_and_json({"status": "UNVERIFIABLE", "error": f"not a PMID: {args.pmid!r}"}, 2)
    query = urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "xml",
                                    "tool": "citation-verifier"})
    try:
        status, body = get_body(EFETCH + "?" + query, accept="application/xml")
    except NETWORK_ERRORS as exc:
        return _status_and_json({"status": "UNVERIFIABLE", "error": f"eutils.ncbi.nlm.nih.gov: {exc}"}, 2)
    if status != 200:
        return _status_and_json({"status": "UNVERIFIABLE",
                                 "error": f"eutils.ncbi.nlm.nih.gov: HTTP {status}"}, 2)
    try:
        out = pubmed_notices(body)
    except ValueError as exc:
        return _status_and_json({"status": "UNVERIFIABLE", "error": f"PMID {pmid}: {exc}"}, 2)
    return _status_and_json(out)


# --------------------------------------------------------------------- main

def main(argv=None):
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="lookup.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("doi", help="is the DOI registered? (doi.org handle API)")
    p.add_argument("doi")
    p.set_defaults(func=cmd_doi)
    p = sub.add_parser("crossref", help="does Crossref have a record for the DOI? (Crossref REST API)")
    p.add_argument("doi")
    p.set_defaults(func=cmd_crossref)
    p = sub.add_parser("pubmed", help="PMIDs for a title and first author (E-utilities)")
    p.add_argument("--title", required=True, help='the title, or "-" to read it from stdin')
    p.add_argument("--author", default="", help="first author's surname")
    p.set_defaults(func=cmd_pubmed)
    p = sub.add_parser("existence", help="Step 3's existence verdict from the lookup statuses (no network)")
    p.add_argument("--doi", required=True, choices=DOI_STATUSES, help="2a; NONE when there is no DOI")
    p.add_argument("--crossref", required=True, choices=SEARCH_STATUSES, help="2b")
    p.add_argument("--pubmed", required=True, choices=PUBMED_STATUSES, help="2c")
    p.add_argument("--openalex", required=True, choices=SEARCH_STATUSES, help="2d")
    p.set_defaults(func=cmd_existence)
    p = sub.add_parser("authors", help="cited author list vs Crossref's (stdin: crossref output)")
    p.add_argument("--et-al", action="store_true", help='the cited list ends in "et al."')
    p.add_argument("surnames", nargs="*", metavar="SURNAME", help="the cited surnames, in the cited order")
    p.add_argument("--authors-json", help="JSON list of {family,given} or {name} objects; full identity comparison")
    p.set_defaults(func=cmd_authors)
    p = sub.add_parser("notices", help="retractions, expressions of concern, corrections "
                                       "(stdin: crossref output)")
    p.set_defaults(func=cmd_notices)
    p = sub.add_parser("pubmed-notices", help="the same notices from PubMed (E-utilities efetch)")
    p.add_argument("pmid")
    p.set_defaults(func=cmd_pubmed_notices)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
