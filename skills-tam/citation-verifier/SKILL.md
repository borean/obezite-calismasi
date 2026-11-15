---
name: citation-verifier
description: "Verifies all citations in a .bib file or LaTeX manuscript against PubMed, Crossref, and OpenAlex, and checks every cited claim against the full-text PDFs in the project folder (PDF page + verbatim quote). Flags fabricated DOIs, wrong author/year combinations, retracted papers, and unsupported claims. Use whenever the user wants to verify references, says 'check citations', or before submission to ensure citation integrity."
allowed-tools: [Read, Bash, Grep, Glob, Write, WebFetch, WebSearch]
license: MIT License
metadata:
    skill-author: Bora Ulukapı
    version: "1.4.1"
---

# Citation Verifier

Verifies every citation in a bibliography against real academic databases. This skill catches fabricated DOIs, wrong metadata, retracted papers, and unsupported claims.

## When to Use

- User asks to verify citations in a `.bib` file or LaTeX manuscript
- User asks to check for fabricated or hallucinated references
- User asks to validate DOIs, author names, publication years, or journal names
- User wants a citation trust report before submitting a manuscript

## Input

The user provides one or more of:
- A `.bib` file path
- A `.tex` file path (with `\bibitem` entries or a linked `.bib`)
- A directory containing `.tex` and `.bib` files

## Procedure

### Step 0: Set Up a Checklist

Keep a checklist of these tasks: in the environment's task-list tool if it has one, otherwise in your reply, ticking each task off as it is done.
1. Extract citations from input files
2. Verify each citation against databases (DOI, Crossref, PubMed, OpenAlex)
3. Detect red flags (fabricated DOIs, wrong metadata, retractions, suspicious patterns)
4. Verify each claim against the full text in the project's source folder (page + verbatim quote)
5. Generate Citation Trust Report

### Step 1: Extract Citations

**From `.bib` files:**

`scripts/bib.py` in this skill's folder parses the `.bib` file into a JSON list, one object per entry: `citekey` (the label, e.g. `smith2023thyroid`), `type` (`article`, `book`, ...) and every field under its lower-case name. The later steps use `author`, `title`, `year`, `journal` or `booktitle`, `doi`, `pmid`, `volume` and `pages`. `SKILL_DIR` here and below is the folder this SKILL.md was loaded from, e.g. `~/.agents/skills/citation-verifier`.

```bash
python3 SKILL_DIR/scripts/bib.py "$BIB_FILE"
```

It counts braces as BibTeX does (a value may contain braces; an entry may close on the line of its last value), reads `{...}`, `"..."` and bare values (numbers, `@string` macros), decodes LaTeX accents and special letters to Unicode (`{\c{S}}{\i}klar` → `Şıklar`, `\.{I}` → `İ`, `Ramo{\u{g}}lu` → `Ramoğlu`) and drops protective braces (`{ROHHAD}` → `ROHHAD`). Use these decoded values in every later step. The entry count goes to stderr, with a `WARNING` for every entry that cannot be parsed (its line number; the entry is left out of the JSON: fix it, or verify that reference by hand), every duplicate citekey and every repeated field. Save the output as `citations.json` (`> citations.json`); Step 3 reads it.

**From `.tex` files with `\bibitem`:**

Use `Grep` to find `\bibitem` entries. Parse each entry for author, title, year, journal, and DOI. These are less structured, so use heuristics:
- Author names come first (before the title in quotes or italics)
- Year is a 4-digit number near the author block
- DOI may appear as `doi:...` or `https://doi.org/...`

### Step 2: Verify Each Citation Against Databases

#### Executable identity preflight

For each `.bib` file, run the citation-management validator with online checks enabled and save its evidence report beside the input:

```bash
python3 ~/.agents/skills/citation-management/scripts/validate_citations.py \
  "$BIB_FILE" --check-dois \
  --report "$(dirname "$BIB_FILE")/citation-identity-report.json"
```

Read the JSON report even when the command exits with errors. This identity preflight compares the cited title, first-author identity, publication year and journal with available Crossref metadata. It tolerates formatting differences and accepts a matching online or print publication year. Report mismatches and retain their cited/remote evidence. Missing metadata, incomplete comparisons and failed requests remain **unverified**; a working DOI alone is not a verified citation. Without `--check-dois`, the command performs offline structural checks only.

The preflight does not establish claim support or complete retraction screening. Continue the PubMed/OpenAlex cross-checks, retraction checks and manuscript-context review below. Entries without a DOI need title/author searches rather than being silently counted as verified. When several `.bib` files share a directory, use a distinct report filename for each.


Process citations **one at a time** with a **1-second delay** between API calls to respect rate limits. Use `sleep 1` between each Bash curl command.

#### 2a. DOI Resolution Check

For each citation with a DOI, check that the DOI is registered:

```bash
python3 SKILL_DIR/scripts/lookup.py doi "DOI_HERE"
```

It asks the doi.org handle API (`https://doi.org/api/handles/DOI`) and never contacts the publisher, because publishers such as Wiley, NEJM and MDPI answer automated requests with HTTP 403, which makes a real DOI look broken when its redirect is followed. A `https://doi.org/` or `doi:` prefix is removed first. It prints exactly one word, the DOI_STATUS of the Existence verdict (Step 3); a citation without a DOI has DOI_STATUS `NONE`:

- `RESOLVES` = the DOI is registered: continue to 2b
- `NOT_FOUND` = the DOI is not registered. A real paper can carry a wrong DOI, so this alone does not decide whether the paper exists: skip 2b; the title searches (2c, 2d) and the Existence verdict decide
- `UNVERIFIABLE` = network error or timeout (the reason is on stderr): retry once; if it stays UNVERIFIABLE, continue to 2b, where a Crossref record can still confirm the DOI

#### 2b. Crossref Metadata Verification

For each citation whose DOI 2a reported as `RESOLVES` or `UNVERIFIABLE`; for `NOT_FOUND` and for a citation without a DOI, CROSSREF_STATUS is `SKIPPED`:

```bash
python3 SKILL_DIR/scripts/lookup.py crossref "DOI_HERE"
```

It asks the Crossref REST API (`https://api.crossref.org/works/DOI`). The first line it prints is CROSSREF_STATUS for the Existence verdict (Step 3):

- `FOUND` = Crossref has a record for the DOI; the API response follows on the second line as JSON, without the record's long `reference` list. For a DOI that 2a reported as `UNVERIFIABLE`, this record confirms that the DOI is registered
- `NOT_FOUND` = Crossref has no record (HTTP 404). This does not show that the DOI is unregistered: other agencies, such as DataCite and mEDRA, register DOIs that Crossref does not know. Only 2a can show that
- `UNVERIFIABLE` = network error, timeout, rate limit or any other answer (the reason is on stderr): retry once, as in Rate Limiting

Parse the JSON response. Extract and compare:
- `message.title[0]` vs the cited title (fuzzy match — allow minor differences in capitalization, punctuation)
- `message.author[*].family` vs cited author surnames
- `message.published-print.date-parts[0][0]` or `message.published-online.date-parts[0][0]` vs cited year
- `message.container-title[0]` vs cited journal name
- `message.updated-by` and `message.update-to`: publication notices; read them only through the notice check below

**Title matching:** Use the executable identity preflight and preserve meaningful title words and clinical/math signs. HIV+ versus HIV- or <10 versus >10 requires review. A high fuzzy score cannot clear a differing title. This manual check is a conservative fallback:

```bash
python3 -c "
from difflib import SequenceMatcher
a = '''CITED_TITLE'''.lower().strip()
b = '''CROSSREF_TITLE'''.lower().strip()
ratio = SequenceMatcher(None, a, b).ratio()
print(f'MATCH_RATIO:{ratio:.3f}')
if ratio < 0.70:
    print('FLAG:WRONG_DOI')
elif a == b:
    print('FLAG:TITLE_OK')
else:
    print('FLAG:TITLE_REVIEW')
"
```

**Author matching:** Compare every listed author in order, including given names or corporate names when available. The cited first author must match the Crossref first author; finding that surname among later coauthors is insufficient. Save the Crossref response once and reuse it for authors and notices.

For full identities, supply a JSON list of `{"family": "Smith", "given": "John"}` or `{"name": "TODAY Study Group"}` objects:

```bash
python3 SKILL_DIR/scripts/lookup.py authors --authors-json cited-authors.json < crossref.txt
```

The legacy positional surname interface remains available: `lookup.py authors [--et-al] SURNAME ...`. Its scope is surname order only.
- `MATCH`: the complete ordered person/group identities match.
- `PARTIAL_MATCH`: a matching "et al." prefix omits authors, or only surnames were supplied. Omitted authors/given names were not verified; expand from an authoritative source or perform and record the complete comparison.
- `MISMATCH`: different surname/order, corporate name or incompatible given names.
- `REVIEW`: missing metadata, initial-only ambiguity, unmarked truncation, extra authors, or an unresolvable group name.

The external preflight retains the first-author given-name check. Do not turn a helper's partial surname result into full identity approval.

**Year matching:** Accept a cited year matching an actual online, print or other recorded publication year. A one-year difference is not automatically accepted; retain evidence for the timing distinction. Unexplained discrepancies require review.

**Journal matching:** Preserve distinctions such as Cell versus Cells. Resolve abbreviations against the source record/ISSN; a fuzzy match alone does not clear a different journal.

**Notice check (retractions, expressions of concern, corrections):** Crossref puts a notice on the original article under `updated-by`; `update-to` sits on the notice record itself. For a DOI that Crossref has (2b `FOUND`):

```bash
python3 SKILL_DIR/scripts/lookup.py crossref "DOI_HERE" | python3 SKILL_DIR/scripts/lookup.py notices
```

The first line is the status, then JSON `{"status", "items": [{"type", "doi", "date", "source"}]}`, one item per notice:
- `RETRACTED` = a retraction points at the article
- `EXPRESSION_OF_CONCERN` = an expression of concern points at it
- `CORRECTED` = a correction points at it
- `IS_NOTICE` = the cited DOI is itself a notice (its record has `update-to`), not the article: say so in the report
- `NONE_FOUND` = Crossref links no notice to it

Once 2c has found a PMID, ask PubMed as a second signal:

```bash
python3 SKILL_DIR/scripts/lookup.py pubmed-notices PMID_HERE
```

It prints the same statuses, read from PublicationType (`Retracted Publication`) and CommentsCorrections (`RetractionIn`, `ExpressionOfConcernIn`, `ErratumIn`), then JSON with `publication_types` and `items`. A network failure prints `UNVERIFIABLE`: retry once, as in Rate Limiting. OpenAlex `is_retracted` (2d) is a third signal.

Report retractions, expressions of concern and corrections separately, each with its source, notice DOI and date, and never merge the sources silently: they can disagree. For Wakefield 1998 (`10.1016/S0140-6736(97)11096-0`), Crossref labels the 2004 notice (`10.1016/S0140-6736(04)15715-2`) a correction, while PubMed links it as a retraction (`RetractionIn`), and only PubMed links an expression of concern (Eur J Gastroenterol Hepatol 2011). An empty result is "no notice found in the checked sources on <date>", naming the sources, never "clean".

#### 2c. PubMed Verification

For biomedical citations, and for any citation whose DOI 2a and 2b did not confirm (Step 3 calls a paper `FABRICATED` or `NOT_INDEXED` only after this search), search PubMed by title and first author through the official E-utilities API (`esearch.fcgi`):

```bash
python3 SKILL_DIR/scripts/lookup.py pubmed --title "TITLE_HERE" --author "SURNAME_HERE"
```

The helper sends the term `TITLE[Title] AND SURNAME[Author]`, URL-encoded as a whole (titles contain `:` and `?`, surnames letters such as `ı` and `ş`); if that finds nothing, it searches the title alone. A title that contains `"`, `$` or a backtick is safer on stdin: `--title -`. It prints one JSON object: `status`, `search` (`title+author`, or `title` for the title-only search), `count`, `pmids` and the `term` it sent.
- `FOUND` via `title+author`: the paper exists in PubMed. Record the PMID.
- `FOUND` via `title`: a paper with this title is in PubMed, but not under this first author. Compare its authors (esummary below).
- `NOT_IN_PUBMED`: this does **not** automatically mean fabricated (not all papers are in PubMed), but note as "Not found in PubMed."
- `UNVERIFIABLE`: network error, timeout or rate limit (see `error`): retry once, as in Rate Limiting.

If a PMID was found, optionally fetch the full record to cross-check metadata:

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=PMID_HERE&retmode=json" \
  --max-time 15
```

#### 2d. OpenAlex Cross-Validation

Search OpenAlex by DOI or title. Search by title as well unless 2a printed `RESOLVES` or 2b printed `FOUND` (so for `NOT_FOUND`, an unconfirmed `UNVERIFIABLE` and no DOI): a paper cited with a wrong DOI can only be found by its title.

```bash
# By DOI (preferred):
curl -s "https://api.openalex.org/works/doi:DOI_HERE" \
  -H "User-Agent: CitationVerifier/1.0 (mailto:bora@example.com)" \
  --max-time 15

# By title (fallback; required unless 2a or 2b confirmed the DOI):
ENCODED_TITLE=$(echo "TITLE_HERE" | python3 -c "import re,sys,urllib.parse; print(urllib.parse.quote(' '.join(w for w in re.findall(r'\w+', sys.stdin.read()) if len(w) > 1)))")
curl -s "https://api.openalex.org/works?filter=title.search:${ENCODED_TITLE}" \
  -H "User-Agent: CitationVerifier/1.0 (mailto:bora@example.com)" \
  --max-time 15
```

The title search sends only the title's words of two or more characters: OpenAlex rejects a comma or `?` in the query (HTTP 400), and a lone letter, such as the `s` left from `'s`, makes it find nothing. It finds only titles that contain every word sent.

Set OPENALEX_STATUS for the Existence verdict (Step 3):
- `FOUND` = the DOI search returns a work (a JSON object with an `id`), or a title-search result (`results[*].display_name`) matches the cited title by 2b's title heuristic: an exact normalized title with the same meaningful signs; fuzzy-only candidates remain review items
- `NOT_FOUND` = the title search ran and no result matches; the DOI search, if run, found nothing (HTTP 404: an HTML page instead of JSON)
- `UNVERIFIABLE` = a search failed (no output, i.e. a timeout or no connection, or a JSON `error`) and nothing was found: retry once, as in Rate Limiting
- `SKIPPED` = no title search was done

Use OpenAlex to:
- Confirm the paper exists in a second independent database
- Cross-check author names, year, journal, and cited-by count
- Check `is_retracted` field

### Step 3: Red Flag Detection

For each citation, evaluate:

| Flag | Condition | Severity |
|------|-----------|----------|
| `FABRICATED` | Required negative checks completed: DOI registry NOT_FOUND; Crossref NOT_FOUND or inapplicable SKIPPED after registry confirmation; completed PubMed NOT_IN_PUBMED and OpenAlex NOT_FOUND | CRITICAL |
| `DOI_NOT_REGISTERED` | DOI not registered (2a NOT_FOUND), but PubMed or OpenAlex finds the paper by its title: the paper is real, the DOI is wrong | HIGH |
| `WRONG_DOI` | DOI resolves but title similarity < 70% | HIGH |
| authors `MISMATCH` | `lookup.py authors` (2b): a cited name differs at some position, or the names are reordered. Before 1.4.0 this was `FABRICATED_AUTHOR` | CRITICAL |
| authors `REVIEW` / `PARTIAL_MATCH` | Incomplete ordered identities, initial-only ambiguity, omitted authors, surname-only comparison or missing source metadata | HUMAN REVIEW |
| `WRONG_YEAR` | Cited year matches no recorded publication year; investigate online/print timing | MEDIUM |
| `WRONG_JOURNAL` | Journal name is clearly different | MEDIUM |
| `RETRACTED` | `notices` or `pubmed-notices` (2b) printed RETRACTED, or OpenAlex `is_retracted` is true | CRITICAL |
| `IS_NOTICE` | The cited DOI is itself a notice (retraction, expression of concern or correction), not the article (2b) | CRITICAL |
| `EXPRESSION_OF_CONCERN` | A notice source (2b) links an expression of concern to the paper | HUMAN REVIEW |
| `CORRECTED` | A notice source (2b) links a correction or erratum to the paper | HUMAN REVIEW |
| `SUSPICIOUS_PATTERN` | DOI has suspiciously round numbers (e.g., `10.1000/1000`) or sequential DOIs across entries | LOW |
| `NO_DOI` | No DOI provided — cannot fully verify | LOW |
| `NOT_INDEXED` | No DOI, and the PubMed and OpenAlex title searches ran and found nothing (may be too new, grey literature, or fabricated) | MEDIUM |
| `UNVERIFIABLE` | Nothing found the paper, but a lookup failed (network error, timeout, rate limit; Crossref too) or a PubMed or OpenAlex title search was not done, with or without a DOI: re-run or run it; never FABRICATED or NOT_INDEXED | MEDIUM |

CRITICAL flags count as `blocking` in Step 5, HUMAN REVIEW flags as `unresolved`. Give every notice flag with its source (2b): the same notice can carry different labels in different sources.

**Existence verdict:** whether the paper exists is decided by one command from the statuses of Step 2, never by one lookup alone, so that `FABRICATED`, `DOI_NOT_REGISTERED`, `UNVERIFIABLE` and `NOT_INDEXED` always follow the table:

```bash
python3 SKILL_DIR/scripts/lookup.py existence --doi DOI_STATUS --crossref CROSSREF_STATUS --pubmed PUBMED_STATUS --openalex OPENALEX_STATUS
```

- DOI_STATUS: the word 2a printed (`RESOLVES`, `NOT_FOUND`, `UNVERIFIABLE`), or `NONE` for a citation without a DOI
- CROSSREF_STATUS: the first line 2b printed (`FOUND`, `NOT_FOUND`, `UNVERIFIABLE`), or `SKIPPED` when 2b did not run
- PUBMED_STATUS: the `status` 2c printed (`FOUND`, `NOT_IN_PUBMED`, `UNVERIFIABLE`), or `SKIPPED` when PubMed was not searched. When nothing else confirms the paper, a skipped search gives `UNVERIFIABLE`: search PubMed for every paper whose DOI 2a and 2b did not confirm, biomedical or not
- OPENALEX_STATUS: as 2d sets it (`FOUND`, `NOT_FOUND`, `UNVERIFIABLE`, `SKIPPED`)

It prints one word, from the first rule that applies:

1. DOI `RESOLVES`, or Crossref `FOUND` → `EXISTS`
2. PubMed or OpenAlex `FOUND` (a title match) → `DOI_NOT_REGISTERED` if the DOI is `NOT_FOUND`, otherwise `EXISTS`
3. DOI, Crossref, PubMed or OpenAlex `UNVERIFIABLE`, or PubMed or OpenAlex `SKIPPED` (a title search not done) → `UNVERIFIABLE`, with or without a DOI
4. DOI `NOT_FOUND` → `FABRICATED`: every check ran and found nothing (Crossref `NOT_FOUND` or `SKIPPED`, PubMed `NOT_IN_PUBMED`, OpenAlex `NOT_FOUND`)
5. No DOI → `NOT_INDEXED`

`EXISTS` is not a flag: the paper is real, and the other rows of the table still apply. Any other word is the citation's flag; do not set these four flags any other way. A failed lookup or a skipped title search never yields `FABRICATED`: re-run the lookup (Rate Limiting) or run the search, then run the command again.

**Suspicious DOI pattern detection:**

```bash
python3 - <<'EOF'
import json, os, re, sys

dois = json.loads(os.environ.get("DOI_LIST_JSON") or "null")  # list of DOIs from all citations
if not isinstance(dois, list):
    sys.exit("DOI_LIST_JSON must hold a JSON list of DOIs (see below how to build it)")
suspicious = []

for i, doi in enumerate(dois):
    # Check for round numbers
    if re.search(r'/\d+0{3,}', doi):
        suspicious.append((doi, 'Round number in DOI'))
    # Check for obviously fake prefixes
    if not re.match(r'10\.\d{4,}/', doi):
        suspicious.append((doi, 'Invalid DOI prefix format'))

# Check for sequential DOIs (same prefix, incrementing suffix)
sorted_dois = sorted(dois)
for i in range(1, len(sorted_dois)):
    prev_parts = sorted_dois[i-1].rsplit('/', 1)
    curr_parts = sorted_dois[i].rsplit('/', 1)
    if len(prev_parts) == 2 and len(curr_parts) == 2:
        if prev_parts[0] == curr_parts[0]:
            try:
                if abs(int(curr_parts[1]) - int(prev_parts[1])) == 1:
                    suspicious.append((sorted_dois[i], 'Sequential DOI with ' + sorted_dois[i-1]))
            except ValueError:
                pass

for doi, reason in suspicious:
    print(f'SUSPICIOUS: {doi} — {reason}')
EOF
```

The check reads the environment variable `DOI_LIST_JSON`: a JSON list of the DOIs of all entries. Build it from Step 1's output, `citations.json` (with `\bibitem` input, first save the entries you extracted in the same shape). Run this line in the same Bash call as the check, since environment variables do not carry over between calls:

```bash
export DOI_LIST_JSON="$(python3 -c 'import json; print(json.dumps([e["doi"] for e in json.load(open("citations.json")) if e.get("doi")]))')"
```

### Step 4: Claim Verification Against Full Text

Check every cited claim against the full text of the cited paper and, separately, against its abstract. Both verdicts are recorded, and only the full text decides: each claim gets one abstract verdict (4a2) and one full-text verdict code (4f), and the abstract never replaces or upgrades the full-text verdict. A verdict that says the paper backs the claim carries a PDF page and a verbatim quote that anyone can find again (4g).

`scripts/fulltext.py` in this skill's folder does the mechanical parts (Python standard library; text from `pdftotext` if installed, else `pypdf`). Its docstring (`-h`) has the details.

```bash
FT=SKILL_DIR/scripts/fulltext.py   # SKILL_DIR = the folder this SKILL.md was loaded from, e.g. ~/.agents/skills/citation-verifier
python3 "$FT" pages PDF --out TXT            # page-separated text: "=== PAGE n ===", n = PDF page index
python3 "$FT" pages PDF --layout --out TXT   # physical layout, better for tables
python3 "$FT" quote PDF "QUOTE"              # FOUND pages=[..] (exit 0) or NOT_FOUND (exit 1)
python3 "$FT" identify --doi DOI --title "TITLE" PDF   # MATCH (exit 0), NO_MATCH (exit 1) or CONFLICT (exit 3)
```

Exit status 2 means the PDF could not be read.

#### 4a. Build the claim list

Every citation command in the `.tex` files counts: `\cite`, `\citep`, `\citet`, `\parencite`, `\autocite`, `\textcite` (and their starred and capitalised forms), with or without optional `[..]` arguments such as `\citep[see][p.~4]{key}`. Text after an unescaped `%` is a comment and does not count. A multi-key cite such as `\citep{a,b}` gives one row per key. For each row record the line number (1-based, the line where the cite command starts), the citekey and the full sentence that contains the cite:

```bash
python3 - "$TEX_FILE" > claims.json <<'EOF'
import bisect, json, re, sys

CITE = (r"\\(?:[Cc]ite[pt]?|[Pp]arencite|[Aa]utocite|[Tt]extcite)\*?"
        r"(?:\s*\[[^\]]*\])*\s*\{([^}]*)\}")
NOCAP = CITE.replace("\\{([^}]*)\\}", "\\{[^}]*\\}")                 # same, without the group
TEXTUAL = re.compile(r"\\(?:[Cc]itet|[Tt]extcite)")                    # starts its own sentence
ABBREV = {"al", "e.g", "i.e", "vs", "cf", "etc", "fig", "figs", "tab", "eq", "no", "ca",
          "approx", "dr", "prof", "vb", "örn", "bkz", "yak"}

src = open(sys.argv[1], encoding="utf-8").read()
text = re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group()), src)  # drop comments, keep offsets

bounds = {0, len(text)}                     # sentence starts
for m in re.finditer(r"\n[ \t]*\n|\\\\|\\item\b|\\(?:begin|end)\{[^}]*\}"
                     r"|\\(?:chapter|(?:sub)*section|paragraph)\*?\{[^}]*\}", text):
    bounds.add(m.end())
for m in re.finditer(r"[.!?]['\")\]]*(?:~?" + NOCAP + r")*\s+", text):
    word = re.search(r"[^\s~({]*$", text[max(0, m.start() - 20):m.start()]).group().lower()
    nxt = text[m.end():m.end() + 1]
    if text[m.start()] == "." and word in ABBREV:
        continue
    if nxt.isupper() or nxt in "\\$\"'`(":
        bounds.add(m.end())
bounds = sorted(bounds)

rows = []
for m in re.finditer(CITE, text):
    s = m.start()
    w = max(0, s - 300)
    pre = re.sub(r"(?:\s|~|" + NOCAP + r")*$", "", text[w:s])
    if not TEXTUAL.match(m.group()) and re.search(r"[.!?]['\")\]]*$", pre):
        p, end = w + len(pre) - 1, m.end()          # "... finding.\cite{x}": the cite trails its sentence
    else:
        p, end = s, None
    i = bisect.bisect_right(bounds, p)
    sentence = " ".join(text[bounds[i - 1]:end or bounds[i]].split())
    for key in filter(None, (k.strip() for k in m.group(1).split(","))):
        rows.append({"line": text.count("\n", 0, s) + 1, "citekey": key, "sentence": sentence})
json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
EOF
```

Sentence splitting is heuristic: read each sentence against the manuscript and fix any that were cut wrongly. With several `.tex` files, run it on each and keep the file name with every row.

#### 4a2. Check the abstract

Before reading any full text, give every row an abstract verdict, so that it stays a separate signal. It goes in its own column, `abstract_verdict`, next to the full-text verdict (4f). Take the abstract from the first source that has one:

1. PubMed `efetch`, with the PMID from 2c: the abstract is in `AbstractText` (one per section in a structured abstract).
2. OpenAlex, the 2d record: `abstract_inverted_index` maps each word to its positions; put the words back in order.
3. Crossref, the 2b record: `message.abstract`, in JATS XML; drop the tags.

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=PMID_HERE&retmode=xml" --max-time 15 \
  | python3 -c "import sys, xml.etree.ElementTree as ET; print('\n'.join((t.get('Label', '') + ' ' + ''.join(t.itertext())).strip() for t in ET.parse(sys.stdin).iter('AbstractText')))"

curl -s "https://api.openalex.org/works/doi:DOI_HERE" -H "User-Agent: CitationVerifier/1.0 (mailto:bora@example.com)" --max-time 15 \
  | python3 -c "import json, sys; inv = json.load(sys.stdin).get('abstract_inverted_index') or {}; pos = {i: w for w, ix in inv.items() for i in ix}; print(' '.join(pos[i] for i in sorted(pos)))"

python3 SKILL_DIR/scripts/lookup.py crossref "DOI_HERE" | sed -n 2p \
  | python3 -c "import json, re, sys; print(' '.join(re.sub(r'<[^>]+>', ' ', json.load(sys.stdin)['message'].get('abstract', '')).split()))"
```

| Abstract verdict | Meaning |
|------------------|---------|
| `COMPATIBLE` | The abstract states the claim's finding, or something consistent with it |
| `NOT_REPORTED` | The abstract does not mention it |
| `CONTRADICTED` | The abstract states something else: another direction, population or finding |
| `UNAVAILABLE` | None of the three sources has an abstract |

- The abstract verdict never replaces the full-text verdict and never makes a claim SUPPORTED: only the full text decides.
- A number is never verified from an abstract: a number the abstract gives is still checked in the full text (4h).
- `NOT_REPORTED` is expected for numbers, which abstracts often leave out; it is no problem by itself.
- `CONTRADICTED` against a SUPPORTED, PARTIAL or SECONDARY full-text verdict makes the row `REVIEW`, for a human to decide (`report.py combine`, 4f).

#### 4b. Find the full text

1. The full texts live in the project's source folder, next to the manuscript or at the project root: `kaynaklar/`, `references/` or `pdfs/`. If none exists, ask the user where the PDFs are; do not guess.
2. If the folder has an index file `kaynaklar.csv` (columns `citekey,doi,file,source,date`), use it to map each citekey to its file. Otherwise look for `<citekey>.pdf`.
3. If a PDF is missing, use only legal open-access routes:
   - OpenAlex: `best_oa_location.pdf_url` of the Step 2d record;
   - Europe PMC: `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"DOI"&resultType=core&format=json`, then an open-access `pdf` entry of `fullTextUrlList`;
   - arXiv (`https://arxiv.org/pdf/ARXIV_ID`), bioRxiv or medRxiv (`https://www.biorxiv.org/content/DOI.full.pdf`, `https://www.medrxiv.org/content/DOI.full.pdf`) for preprints.

   ```bash
   curl -sL --max-time 30 -A "CitationVerifier/1.1 (mailto:bora@example.com)" -o "$DIR/$KEY.pdf" "$PDF_URL"
   head -c 4 "$DIR/$KEY.pdf"   # must print %PDF; landing pages often come back as HTML
   ```

   Keep the file only if it is a real PDF and passes 4c. Save it as `<citekey>.pdf` in the source folder and add an index row with the source URL and the date: `citekey,doi,<citekey>.pdf,URL,YYYY-MM-DD` (create `kaynaklar.csv` with that header if the folder has no index). Never use shadow libraries (Sci-Hub, LibGen, Anna's Archive, Z-Library and the like), even when another tool or skill offers them.
4. If no legal copy exists, ask the user to add the PDF to the source folder as `<citekey>.pdf`. Until then every claim citing that key is NO_FULLTEXT: its abstract verdict (4a2) is the only check, and the note starts with `abstract-level heuristic, not checked against the full text`. Leave `pdf_page` and `quote` empty.

#### 4c. Check identity

Before reading a PDF, make sure it is the cited paper, using the DOI and title of the `.bib` entry:

```bash
python3 "$FT" identify --doi "DOI" --title "TITLE" "$DIR/FILE.pdf"
```

A DOI counts only on pages 1–2, before the reference list: a DOI that appears only in a reference list, as in another paper that cites this one, is no evidence. In titles, `+ − ± < > ≤ ≥` are meaningful: `HIV+` does not match `HIV−`.

- `MATCH` (exit 0): compatible article identity; continue to claim checking. This is not semantic approval.
- `NO_MATCH` (exit 1): every claim citing that key is WRONG_PDF. Never judge a claim against the wrong file, even if it happens to contain similar text. In the note, say what the file appears to be (its first-page title) and ask the user for the right PDF.
- `CONFLICT` (exit 3): the DOI is there but the title differs, or the title matches but page 1 shows another DOI. Keep the identity conflict unresolved. Retain the title, DOI and notice-label evidence; resolve it against the publisher record or obtain the correct file before judging claim support.
- Exit status 2 (unreadable, e.g. a scan without a text layer): NO_FULLTEXT, with the reason in the note.

A correction, erratum, retraction or concern notice can repeat the original article title and DOI. An explicit notice label in front matter conflicts with an original-article citation. A deliberately cited notice needs its own notice title and coherent DOI identity. Unusual layouts still require human inspection.

#### 4d. Search the full text

Extract each PDF once (`pages --out`, plus `pages --layout --out` when it has tables), then search in this order:

1. **Numbers first.** Every number in the claim: percentages, counts, means, ages, OR/HR/RR, r and p values, confidence limits. Search both decimal separators (a comma in the claim is also searched as a point, and vice versa), with and without `%` and spaces, and the values that round to the claim's number. For ratios and test statistics also search their labels (`OR`, `odds ratio`, `HR`, `hazard ratio`, `r =`, `p <`, `p =`).
2. **Then words.** Population terms (age group, sex, setting, country, disease group); exposure and outcome terms, including the paper's own synonyms and abbreviations; direction words (higher/lower, increased/decreased, associated/not associated, positive/negative, no significant difference).
3. **Read every candidate passage in context:** the whole paragraph, or the table with its caption and footnotes, plus Methods for who was studied. The paper's own Results and tables outrank its abstract, Introduction and Discussion.

A search that prints the page of every hit (the pattern is a case-insensitive Python regex, here a claim number x.y or x,y and two word stems; line breaks and hyphenation can split terms, so search short stems):

```bash
python3 - 'x[.,]y|associat|correlat' TXT <<'EOF'
import re, sys
pat, page = re.compile(sys.argv[1], re.I), "?"
for line in open(sys.argv[2], encoding="utf-8"):
    m = re.match(r"=== PAGE (\d+) ===", line)
    if m:
        page = m.group(1)
    elif pat.search(line):
        print("p" + page + ": " + line.rstrip())
EOF
```

#### 4e. Secondary statements

If the matching passage is the paper reporting someone else's finding (it carries a citation marker such as a numbered bracket `[12]`, a superscript number or an author–year reference, or it summarises earlier work in the Introduction or Discussion), the verdict is SECONDARY, however close the wording. Quote the passage, look the marker up in the paper's reference list, name the primary source in the note (authors, year, title or DOI) and recommend citing it instead. If the paper also shows the finding in its own results, judge those instead.

#### 4f. Verdict codes

One verdict per row:

| Verdict | Meaning |
|---------|---------|
| `SUPPORTED` | The full text states the claim: same finding, direction, population and numbers |
| `PARTIAL` | Part of the claim holds; the note names what differs: number, population, strength, setting or time |
| `NOT_SUPPORTED` | The full text does not state the claim, or states something else |
| `SECONDARY` | The paper states it only by citing another source (4e) |
| `NO_FULLTEXT` | No legal full text (4b); abstract-level heuristic only |
| `WRONG_PDF` | The file in the source folder is not the cited paper (4c) |
| `SOURCE_FAILED` | The reference failed Steps 2–3: FABRICATED, WRONG_DOI or RETRACTED |

SOURCE_FAILED, WRONG_PDF and NO_FULLTEXT come first: when one applies, the claim is not judged against any text. For PARTIAL, start the note with the part that differs (`number:`, `population:`, `strength:`, `setting:`, `time:`; several may apply). Strength means the claim says more than the paper: causal wording for an association, "significant" for a non-significant difference, a general statement drawn from a subgroup. Keep the rows for Step 5 as a JSON list, `rows.json`: the 4a fields plus verdict, pdf_page, quote and note, and these:

- `abstract_verdict`: the abstract verdict (4a2).
- `combined`: what `python3 SKILL_DIR/scripts/report.py combine ABSTRACT_VERDICT VERDICT` prints: the full-text verdict, except that `CONTRADICTED` against SUPPORTED, PARTIAL or SECONDARY gives `REVIEW`. The abstract never upgrades a verdict: `COMPATIBLE` with NO_FULLTEXT stays NO_FULLTEXT.
- `key`: exact UTF-8 sentence + source SHA-256 + citekey, using `report.py key SENTENCE SHA256 --citekey KEY`. Whitespace changes invalidate this key.
- `source_path` (absolute path), `source_sha256`, `source_format` (`pdf` or `text`), `checked_at` (ISO time with timezone): the saved source and current check revision. `summarize` rereads source bytes and rechecks supported quotation/page evidence. PDFs also require expected `reference_doi` and `reference_title` for identity verification.
- `existence`, `metadata`, `notices`, `authors`: current reference checks. `metadata` covers title, journal and publication year: MATCH only when all are resolved; otherwise MISMATCH or REVIEW. Names/initials alone do not establish full identity.
- `human` and `disposition`: filled only from an actual human decision. A nonempty name or free-text override cannot repair unresolved evidence.

Read [the report schema](references/report-schema.md) when assembling rows. It defines the exact source/claim bindings, bound disposition and narrow notice-review exceptions.

**Stale rows:** changed sentence, citation key, source bytes/location, quotation/page/note, stage statuses, citation purpose or dated check revision invalidates the corresponding prior disposition. Do not copy approval to a fresh row merely because a similar sentence appeared earlier. Missing/failed evidence remains unresolved even when a name is present.

#### 4g. Evidence rule

- SUPPORTED, PARTIAL and SECONDARY need a verbatim quote of at most 40 words, copied from the extracted text (not retyped, not from memory), plus the PDF page index: the 1-based page of the PDF file as `pages` and `quote` print it, not the journal's printed page number.
- Run `fulltext.py quote` on every quote, including any quote in a note. The row's `pdf_page` must be one of the pages it reports. `NOT_FOUND` means: fix the quote (copy it again from the extracted text) or change the verdict.
- A quote is one continuous passage. Never paraphrase inside quotation marks: no ellipses, no inserted or corrected words.
- NOT_SUPPORTED: the note lists what was searched (numbers and terms). If a closest passage exists, put it in `quote` and `pdf_page`, checked like any other quote, and say in the note why it falls short.

#### 4h. Numbers rule

A claim with a number is SUPPORTED only if the paper gives the same number for the same quantity. Allowed: rounding (the paper's number, rounded to the claim's precision, equals the claim's number), a decimal comma for a point or vice versa, and exact equivalents such as a percentage and the same fraction. Anything else is PARTIAL (number): quote the passage with the paper's number and give both numbers in the note. A matching number for another quantity, subgroup or time point does not count.

#### 4i. Population rule

Before any verdict, read the study population in Methods: age range, adults or children, sex, setting, country. If the claim's population differs, the verdict is at most PARTIAL (population); a pediatric claim that cites an adult-only study is PARTIAL (population). Quote a passage that shows the paper's population (the finding itself if it names the population, otherwise Methods) and give the other passage's page in the note.

### Step 5: Generate the Citation Verification Report

Save the full `rows.json` (including evidence bindings and dispositions), `citation-claims.csv`, and a readable report beside the manuscript. Keep one row per claim–source occurrence and include all cited files, captions and supplements; the heuristic extractor does not prove complete coverage. Preserve unresolved keys and parser warnings.

The report shows each of the six checks separately: DOI registration, Crossref retrieval, complete metadata identity, dated notices, abstract verdict, and full-text verdict with source/page/quote. Include the exact manuscript sentence and source location. Abstract/full-text judgments remain attributed reviewer annotations rather than automated fact certification.

Use [the report schema](references/report-schema.md) for required columns and human decisions, then run:

```bash
python3 SKILL_DIR/scripts/report.py summarize rows.json
```

Copy the emitted `blocking`, `unresolved`, `unsigned` counts and `ready` field verbatim. An empty report is unresolved. One critical failure is never averaged away. `SECONDARY` remains unresolved until its use is properly addressed. Failed metadata/claims, absent evidence, unknown codes and stale files cannot be waived by a signature or arbitrary override.

Only a bound, reasoned notice disposition can permit an explicitly described retraction discussion or record review of a correction/concern notice, with all other checks complete. It never converts a retracted study into valid positive clinical evidence. `ready` means supplied evidence/decision records pass these mechanical checks; the helper does not authenticate a human, establish extraction completeness or certify scientific correctness.

## Rate Limiting

Always insert delays between API calls:
- `sleep 1` between individual API calls within a citation
- `sleep 2` between citations if processing more than 20 citations
- If any API returns 429 (Too Many Requests), wait 10 seconds and retry once

Use this pattern:

```bash
sleep 1  # Rate limit: respect API terms of service
curl -s "https://api.crossref.org/works/$DOI" ...
```

## Important Notes

- **Not all papers are in PubMed.** PubMed primarily indexes biomedical literature. A missing PubMed result alone does not mean fabrication. Always cross-reference with Crossref and OpenAlex.
- **Book chapters and conference papers** may not have DOIs. Mark these as `NO_DOI` rather than `FABRICATED`.
- **Preprints** (bioRxiv, medRxiv, arXiv) have DOIs but may not be in PubMed. They should be verifiable via Crossref and OpenAlex.
- **Claims are checked against the full text.** Each verdict rests on the cited paper's PDF, with a page and a verbatim quote anyone can check; the abstract verdict is recorded beside it and never replaces it. Abstract-only checks are labeled NO_FULLTEXT and are heuristic. Never auto-delete a citation, whatever its verdict: a human reviews every row that is not SUPPORTED, and nothing is called verified until a human has signed its rows.
- **Grey literature** (reports, guidelines, theses) often has no DOI and may not be indexed anywhere. It is then `NOT_INDEXED`, not `FABRICATED`, once the PubMed and OpenAlex title searches have run; `UNVERIFIABLE` is for a lookup that failed or a title search that was not done.
- **Crossref is the most reliable** single source for DOI verification. If Crossref confirms the DOI, title, and authors, the citation is almost certainly real.
- **AI-generated bibliographies** tend to have specific patterns: plausible-sounding but nonexistent DOIs, real author names paired with fabricated titles, and correct journal names with wrong volumes/pages. This skill is specifically designed to catch these patterns.

## Changelog

- **1.4.1**: Shared-harness port retaining the executable identity preflight; full author/given-name scope, notice-PDF conflicts and fail-closed exact source/claim-bound report dispositions.
- **1.4.0**: Notices (2b): `lookup.py notices` reads Crossref's `updated-by`, where a notice sits on the original article, and calls a cited DOI that is itself a notice `IS_NOTICE`; `lookup.py pubmed-notices` adds PubMed as a second signal and OpenAlex `is_retracted` stays the third; retractions, expressions of concern and corrections are reported separately, per source, and an empty result is "no notice found in the checked sources on <date>". Authors (2b): `lookup.py authors` compares the full ordered list, with Turkish `ı`/`İ` and accents normalised; historically a Vancouver "et al." prefix was `MATCH` (superseded by 1.4.1 PARTIAL_MATCH), a different or reordered name is `MISMATCH` (CRITICAL; it replaces `FABRICATED_AUTHOR`), an incomplete list or a group author is `REVIEW`. Existence (Step 3): `FABRICATED` needs every check completed and negative; a failed Crossref lookup or a skipped PubMed or OpenAlex title search gives `UNVERIFIABLE`, also without a DOI. Abstract check (new 4a2): every row gets an abstract verdict in its own column, which never replaces the full-text verdict and never verifies a number; `report.py combine` turns a contradiction of SUPPORTED, PARTIAL or SECONDARY into `REVIEW`. Identity (4c): `fulltext.py identify` counts a DOI only on pages 1–2 before the reference list, keeps `+ − ± < > ≤ ≥` in titles and prints `CONFLICT` (exit 3), which is WRONG_PDF unless the user confirms the file. Rows (4f) gain `abstract_verdict`, `combined`, `key` (`report.py key`; a changed sentence or PDF makes the row stale) and `human` (the reviewer's initials). Step 5 replaces the averaged trust score with `report.py summarize` (`blocking`, `unresolved`, `unsigned`, `ready`). New tests in `tests/test_v140.py` run offline; their fixtures are the live Wakefield 1998 Crossref and PubMed records saved on 2026-11-07. Run them from the skill folder with `python3 -m pytest -q tests/`. Why: Wakefield 1998's retraction lives in Crossref `updated-by`, which the old `update-to`/`is-retracted` rule missed; the first-author-only check let invented co-authors pass; `FABRICATED` was given after a failed Crossref lookup or a skipped PubMed search; `identify` said `MATCH` when the DOI appeared only in another paper's reference list, and HIV+ and HIV− titles matched (0.98); the averaged trust score hid a single retraction; there was no stale-verdict detection and no separate abstract verdict; Turkish `ı` was not normalised.
- **1.3.0**: One existence verdict: `lookup.py existence` turns the statuses of 2a–2d into one word (`EXISTS`, `DOI_NOT_REGISTERED`, `FABRICATED`, `UNVERIFIABLE` or `NOT_INDEXED`), and the Step 3 table is the only definition. `FABRICATED` needs an unregistered DOI and no title match in PubMed or OpenAlex; the new `DOI_NOT_REGISTERED` is a real paper, found by its title, cited with a wrong DOI; the new `UNVERIFIABLE` is a failed lookup or a missing title search and never becomes `FABRICATED`. 2a no longer gives a verdict. Crossref (2b, now through `lookup.py crossref`) also checks a DOI whose doi.org check was `UNVERIFIABLE`. 2d says how to set OPENALEX_STATUS and sends only the title's words. Grey literature is `NOT_INDEXED`. Why: 2a called every unregistered DOI fabricated while the table also required no PubMed and no OpenAlex match, so a real paper cited with a wrong DOI was called fabricated and no flag described that case; the notes used `UNVERIFIABLE`, which the table did not define; a DOI whose doi.org check failed never reached Crossref, which could have confirmed it; OpenAlex rejects a title search that contains a comma or `?` (HTTP 400).
- **1.2.0**: `.bib` files are parsed by `scripts/bib.py` (braces counted as in BibTeX, `"..."` and bare values, LaTeX accents and special letters decoded to Unicode, protective braces dropped). The DOI check asks the doi.org handle API and never the publisher, and PubMed is searched through E-utilities with the whole `TITLE[Title] AND SURNAME[Author]` term URL-encoded (both in `scripts/lookup.py`). The suspicious-DOI check reads `DOI_LIST_JSON` from the environment, and Step 3 shows how to build it from Step 1's output. Step 0 no longer requires TodoWrite. Why: the regex parser cut `{\c{S}}{\i}klar` to `{\c{S`, `{ROHHAD}` to `{ROHHAD` and skipped an entry closed on the line of its last value; Wiley, NEJM and MDPI answer automated requests with HTTP 403, so real DOIs looked broken; curl read `[Title]` as a URL glob and sent nothing; the single-quoted `'$DOI_LIST_JSON'` never expanded; not every environment has TodoWrite.
- **1.1.0**: Step 4 checks each cited claim against the full-text PDF in the project's source folder instead of the abstract: claim list from every cite variant, legal open-access retrieval, identity check, verdict codes, numbers and population rules, and a verified PDF page + verbatim quote for every supporting verdict (`scripts/fulltext.py`). Step 5 adds the claim–source table and `citation-claims.csv`. Why: an abstract-level check cannot show where a paper supports a claim, and misses wrong numbers, wrong populations, secondary citations and wrong PDFs.
- **1.0.0**: Initial version.
