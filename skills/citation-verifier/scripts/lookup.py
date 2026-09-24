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
        3. DOI, PubMed or OpenAlex UNVERIFIABLE, or      UNVERIFIABLE
           OpenAlex SKIPPED (no title search)
        4. DOI NOT_FOUND                                 FABRICATED
        5. no DOI                                        NOT_INDEXED
      A failed or skipped search therefore never gives FABRICATED. Exit 0; an
      unknown or missing value is a usage error (exit 2). No network access.

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
CROSSREF_API = "https://api.crossref.org/works/"
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
    if "UNVERIFIABLE" in (doi, pubmed, openalex) or openalex == "SKIPPED":
        return "UNVERIFIABLE"  # a failed or missing search proves nothing
    if doi == "NOT_FOUND":
        return "FABRICATED"
    return "NOT_INDEXED"  # no DOI, and no database has the title


def cmd_existence(args):
    print(existence(args.doi, args.crossref, args.pubmed, args.openalex))
    return 0


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
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
