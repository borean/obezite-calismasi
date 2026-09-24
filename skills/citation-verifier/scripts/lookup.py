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

Every request times out after 15 seconds.
"""

import argparse
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 15
NCBI_PAUSE = 0.4
USER_AGENT = "citation-verifier/1.2 (Claude Code skill)"
HANDLE_API = "https://doi.org/api/handles/"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NETWORK_ERRORS = (OSError, http.client.HTTPException)  # URLError and timeouts are OSErrors


def get_json(url):
    """(HTTP status, parsed JSON or None). Network failures raise NETWORK_ERRORS."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            status, body = res.status, res.read()
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a JSON body
        status, body = exc.code, exc.read()
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


# --------------------------------------------------------------------- main

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
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
    p = sub.add_parser("pubmed", help="PMIDs for a title and first author (E-utilities)")
    p.add_argument("--title", required=True, help='the title, or "-" to read it from stdin')
    p.add_argument("--author", default="", help="first author's surname")
    p.set_defaults(func=cmd_pubmed)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
