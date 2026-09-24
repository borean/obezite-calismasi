---
name: citation-verifier
description: "Verifies all citations in a .bib file or LaTeX manuscript against PubMed, Crossref, and OpenAlex, and checks every cited claim against the full-text PDFs in the project folder (PDF page + verbatim quote). Flags fabricated DOIs, wrong author/year combinations, retracted papers, and unsupported claims. Use whenever the user wants to verify references, says 'check citations', or before submission to ensure citation integrity."
allowed-tools: [Read, Bash, Grep, Glob, Write, WebFetch, WebSearch]
license: MIT License
metadata:
    skill-author: Bora Ulukapı
    version: "1.3.0"
---

# Citation Verifier

Verifies every citation in a bibliography against real academic databases. Designed for a pediatric endocrinologist who discovered a ~20% DOI fabrication rate in AI-generated citations. This skill catches fabricated DOIs, wrong metadata, retracted papers, and unsupported claims.

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

`scripts/bib.py` in this skill's folder parses the `.bib` file into a JSON list, one object per entry: `citekey` (the label, e.g. `smith2023thyroid`), `type` (`article`, `book`, ...) and every field under its lower-case name. The later steps use `author`, `title`, `year`, `journal` or `booktitle`, `doi`, `pmid`, `volume` and `pages`. `SKILL_DIR` here and below is the folder this SKILL.md was loaded from, e.g. `~/.claude/skills/citation-verifier`.

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
- `message.update-to` — if this field exists with type `retraction`, flag as **RETRACTED**

**Title matching heuristic:** Lowercase both, remove punctuation, compare. If Levenshtein-like similarity is below 70%, flag as **WRONG_DOI** (title mismatch). A quick check:

```bash
python3 -c "
from difflib import SequenceMatcher
a = '''CITED_TITLE'''.lower().strip()
b = '''CROSSREF_TITLE'''.lower().strip()
ratio = SequenceMatcher(None, a, b).ratio()
print(f'MATCH_RATIO:{ratio:.3f}')
if ratio < 0.70:
    print('FLAG:WRONG_DOI')
elif ratio < 0.85:
    print('FLAG:TITLE_MISMATCH_WARNING')
else:
    print('FLAG:TITLE_OK')
"
```

**Author matching:** Check if at least the first author's surname appears in the Crossref author list. If zero authors match, flag as **FABRICATED_AUTHOR**.

**Year matching:** If the real publication year differs from the cited year by more than 1, flag as **WRONG_YEAR**.

**Journal matching:** Compare journal names with fuzzy matching (abbreviations are common). If they are clearly different journals, flag as **WRONG_JOURNAL**.

**Retraction check:** Look for `message.update-to` with `type: "retraction"` or check if `message.is-retracted` is present and true.

#### 2c. PubMed Verification

For biomedical citations, search PubMed by title and first author through the official E-utilities API (`esearch.fcgi`):

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
- `FOUND` = the DOI search returns a work (a JSON object with an `id`), or a title-search result (`results[*].display_name`) matches the cited title by 2b's title heuristic: MATCH_RATIO ≥ 0.70 (`TITLE_OK` or `TITLE_MISMATCH_WARNING`)
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
| `FABRICATED` | DOI not registered (2a NOT_FOUND) AND no title match in PubMed AND no title match in OpenAlex | CRITICAL |
| `DOI_NOT_REGISTERED` | DOI not registered (2a NOT_FOUND), but PubMed or OpenAlex finds the paper by its title: the paper is real, the DOI is wrong | HIGH |
| `WRONG_DOI` | DOI resolves but title similarity < 70% | HIGH |
| `FABRICATED_AUTHOR` | No cited authors appear in the real paper's author list | HIGH |
| `WRONG_YEAR` | Year differs by > 1 from real publication date | MEDIUM |
| `WRONG_JOURNAL` | Journal name is clearly different | MEDIUM |
| `RETRACTED` | Paper marked as retracted in Crossref or OpenAlex | CRITICAL |
| `SUSPICIOUS_PATTERN` | DOI has suspiciously round numbers (e.g., `10.1000/1000`) or sequential DOIs across entries | LOW |
| `NO_DOI` | No DOI provided — cannot fully verify | LOW |
| `NOT_INDEXED` | No DOI and no match in any database (may be too new, grey literature, or fabricated) | MEDIUM |
| `UNVERIFIABLE` | Nothing found the paper, but a lookup failed (network error, timeout, rate limit) or the OpenAlex title search was not done: re-run it; never FABRICATED | MEDIUM |

**Existence verdict:** whether the paper exists is decided by one command from the statuses of Step 2, never by one lookup alone, so that `FABRICATED`, `DOI_NOT_REGISTERED`, `UNVERIFIABLE` and `NOT_INDEXED` always follow the table:

```bash
python3 SKILL_DIR/scripts/lookup.py existence --doi DOI_STATUS --crossref CROSSREF_STATUS --pubmed PUBMED_STATUS --openalex OPENALEX_STATUS
```

- DOI_STATUS: the word 2a printed (`RESOLVES`, `NOT_FOUND`, `UNVERIFIABLE`), or `NONE` for a citation without a DOI
- CROSSREF_STATUS: the first line 2b printed (`FOUND`, `NOT_FOUND`, `UNVERIFIABLE`), or `SKIPPED` when 2b did not run
- PUBMED_STATUS: the `status` 2c printed (`FOUND`, `NOT_IN_PUBMED`, `UNVERIFIABLE`), or `SKIPPED` when PubMed was not searched (not a biomedical paper)
- OPENALEX_STATUS: as 2d sets it (`FOUND`, `NOT_FOUND`, `UNVERIFIABLE`, `SKIPPED`)

It prints one word, from the first rule that applies:

1. DOI `RESOLVES`, or Crossref `FOUND` → `EXISTS`
2. PubMed or OpenAlex `FOUND` (a title match) → `DOI_NOT_REGISTERED` if the DOI is `NOT_FOUND`, otherwise `EXISTS`
3. DOI, PubMed or OpenAlex `UNVERIFIABLE`, or OpenAlex `SKIPPED` (no title search) → `UNVERIFIABLE`
4. DOI `NOT_FOUND` → `FABRICATED`
5. No DOI → `NOT_INDEXED`

`EXISTS` is not a flag: the paper is real, and the other rows of the table still apply. Any other word is the citation's flag; do not set these four flags any other way. A failed lookup never yields `FABRICATED`: re-run it (Rate Limiting), then run the command again.

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

Check every cited claim against the full text of the cited paper, not its abstract. Each claim gets one verdict code (4f). A verdict that says the paper backs the claim carries a PDF page and a verbatim quote that anyone can find again (4g).

`scripts/fulltext.py` in this skill's folder does the mechanical parts (Python standard library; text from `pdftotext` if installed, else `pypdf`). Its docstring (`-h`) has the details.

```bash
FT=SKILL_DIR/scripts/fulltext.py   # SKILL_DIR = the folder this SKILL.md was loaded from, e.g. ~/.claude/skills/citation-verifier
python3 "$FT" pages PDF --out TXT            # page-separated text: "=== PAGE n ===", n = PDF page index
python3 "$FT" pages PDF --layout --out TXT   # physical layout, better for tables
python3 "$FT" quote PDF "QUOTE"              # FOUND pages=[..] (exit 0) or NOT_FOUND (exit 1)
python3 "$FT" identify PDF --doi DOI --title "TITLE"   # MATCH (exit 0) or NO_MATCH (exit 1)
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
4. If no legal copy exists, ask the user to add the PDF to the source folder as `<citekey>.pdf`. Until then every claim citing that key is NO_FULLTEXT: apply the old abstract-level heuristic (do the title and abstract from Crossref, PubMed or OpenAlex plausibly cover the claim?) and start the note with `abstract-level heuristic, not checked against the full text`. Leave `pdf_page` and `quote` empty.

#### 4c. Check identity

Before reading a PDF, make sure it is the cited paper, using the DOI and title of the `.bib` entry:

```bash
python3 "$FT" identify "$DIR/FILE.pdf" --doi "DOI" --title "TITLE"
```

- `MATCH`: go on.
- `NO_MATCH`: every claim citing that key is WRONG_PDF. Never judge a claim against the wrong file, even if it happens to contain similar text. In the note, say what the file appears to be (its first-page title) and ask the user for the right PDF.
- Exit status 2 (unreadable, e.g. a scan without a text layer): NO_FULLTEXT, with the reason in the note.

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

SOURCE_FAILED, WRONG_PDF and NO_FULLTEXT come first: when one applies, the claim is not judged against any text. For PARTIAL, start the note with the part that differs (`number:`, `population:`, `strength:`, `setting:`, `time:`; several may apply). Strength means the claim says more than the paper: causal wording for an association, "significant" for a non-significant difference, a general statement drawn from a subgroup. Keep the rows for Step 5 as a JSON list, `rows.json`: the 4a fields plus verdict, pdf_page, quote and note.

#### 4g. Evidence rule

- SUPPORTED, PARTIAL and SECONDARY need a verbatim quote of at most 40 words, copied from the extracted text (not retyped, not from memory), plus the PDF page index: the 1-based page of the PDF file as `pages` and `quote` print it, not the journal's printed page number.
- Run `fulltext.py quote` on every quote, including any quote in a note. The row's `pdf_page` must be one of the pages it reports. `NOT_FOUND` means: fix the quote (copy it again from the extracted text) or change the verdict.
- A quote is one continuous passage. Never paraphrase inside quotation marks: no ellipses, no inserted or corrected words.
- NOT_SUPPORTED: the note lists what was searched (numbers and terms). If a closest passage exists, put it in `quote` and `pdf_page`, checked like any other quote, and say in the note why it falls short.

#### 4h. Numbers rule

A claim with a number is SUPPORTED only if the paper gives the same number for the same quantity. Allowed: rounding (the paper's number, rounded to the claim's precision, equals the claim's number), a decimal comma for a point or vice versa, and exact equivalents such as a percentage and the same fraction. Anything else is PARTIAL (number): quote the passage with the paper's number and give both numbers in the note. A matching number for another quantity, subgroup or time point does not count.

#### 4i. Population rule

Before any verdict, read the study population in Methods: age range, adults or children, sex, setting, country. If the claim's population differs, the verdict is at most PARTIAL (population); a pediatric claim that cites an adult-only study is PARTIAL (population). Quote a passage that shows the paper's population (the finding itself if it names the population, otherwise Methods) and give the other passage's page in the note.

### Step 5: Generate Citation Trust Report

After all checks, produce a summary report. Write it to a file named `citation-verification-report.txt` in the same directory as the input file.

Write the claim rows of Step 4 to `citation-claims.csv` next to the report: UTF-8, header `line,citekey,verdict,pdf_page,quote,note`, one row per claim and key in manuscript order, standard CSV quoting (write it with Python's `csv` module, never by joining strings). `verdict` holds the bare code (`PARTIAL`, not `PARTIAL (number)`); `pdf_page` is empty when there is no quote.

```bash
python3 - rows.json "$REPORT_DIR/citation-claims.csv" <<'EOF'
import csv, json, sys
rows = json.load(open(sys.argv[1], encoding="utf-8"))
with open(sys.argv[2], "w", encoding="utf-8", newline="") as fh:
    out = csv.writer(fh)
    out.writerow(["line", "citekey", "verdict", "pdf_page", "quote", "note"])
    out.writerows([r["line"], r["citekey"], r["verdict"], r.get("pdf_page", ""),
                   r.get("quote", ""), r.get("note", "")] for r in rows)
EOF
```

The report's CLAIM–SOURCE TABLE lists every row; CLAIM VERIFICATION FLAGS lists the rows that are not SUPPORTED, for human review. Write the report in the user's language; verdict codes and their PARTIAL labels stay in English, exactly as in the CSV, and so do the flag codes of Step 3.

**Report format:**

```
CITATION VERIFICATION REPORT
Generated: [date]
Input: [filename]
Checked against: Crossref, PubMed, OpenAlex

SUMMARY
═══════
Total citations: [N]
  Verified (all checks passed):  [n] ([%])
  Warnings (minor issues):       [n] ([%])
  Failed (critical issues):      [n] ([%])
  Unverifiable (no DOI, not indexed): [n] ([%])
Claims checked: [M] (rows in citation-claims.csv)
  SUPPORTED:     [n]
  PARTIAL:       [n]
  NOT_SUPPORTED: [n]
  SECONDARY:     [n]
  NO_FULLTEXT:   [n]
  WRONG_PDF:     [n]
  SOURCE_FAILED: [n]

CRITICAL FAILURES
═════════════════
[ref_key] Author et al., Year, "Title..."
  DOI: 10.xxxx/yyyy → NOT_FOUND (not registered)
  PubMed: No match for title + author
  OpenAlex: No match
  Verdict: LIKELY FABRICATED
  Recommendation: Remove or replace with a verified reference

[ref_key] Author et al., Year
  Crossref: Paper retracted on [date]
  Verdict: RETRACTED
  Recommendation: Remove citation; do not cite retracted work

WARNINGS
════════
[ref_key] Author et al., Year
  Title mismatch: cited "Pediatric thyroid..." vs Crossref "Adult thyroid..."
  Verdict: WRONG_REFERENCE — verify manually

[ref_key] Author et al., Year
  Year mismatch: cited 2023, actual 2021
  Verdict: WRONG_YEAR — correct the year

CLAIM VERIFICATION FLAGS
════════════════════════
Line [N]: "[claim text]" \cite{key}
  Cited paper topic: [topic from abstract]
  Concern: [description of mismatch]
  Action: VERIFY MANUALLY

CLAIM–SOURCE TABLE
══════════════════
Full texts: [source folder]; same rows as citation-claims.csv
Line [N] | [citekey] | [VERDICT] | PDF p. [n]
  Claim: "[full sentence]"
  Quote: "[verbatim, ≤ 40 words]"
  Note:  [what differs / what was searched / primary source to cite / PDF to add]

VERIFIED CITATIONS
══════════════════
[ref_key] Author et al., Year — DOI verified, metadata matches, found in PubMed + OpenAlex
[ref_key] Author et al., Year — DOI verified, metadata matches, found in Crossref + OpenAlex
...

TRUST SCORE: [n]/[total] citations verified ([%])
```

**Trust score calculation:**
- Each citation starts at 100 points
- FABRICATED / RETRACTED: 0 points (critical failure)
- WRONG_DOI: 20 points
- DOI_NOT_REGISTERED: 20 points (the paper is real, its DOI is wrong)
- FABRICATED_AUTHOR: 10 points
- WRONG_YEAR: 70 points
- WRONG_JOURNAL: 50 points
- SUSPICIOUS_PATTERN: 80 points
- NOT_INDEXED (no DOI and no match in any database): 60 points
- UNVERIFIABLE (a lookup failed or the title search was not done): 60 points
- NO_DOI: 50 points (cannot fully verify)
- All checks passed: 100 points

Overall trust score = average of all citation scores.

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
- **Claims are checked against the full text.** Each verdict rests on the cited paper's PDF, with a page and a verbatim quote anyone can check. Abstract-only checks are labeled NO_FULLTEXT and are heuristic. Never auto-delete a citation, whatever its verdict: a human reviews every row that is not SUPPORTED.
- **Grey literature** (reports, guidelines, theses) often has no DOI and may not be indexed anywhere. It is then `NOT_INDEXED`, not `FABRICATED`; `UNVERIFIABLE` is for a lookup that failed.
- **Crossref is the most reliable** single source for DOI verification. If Crossref confirms the DOI, title, and authors, the citation is almost certainly real.
- **AI-generated bibliographies** tend to have specific patterns: plausible-sounding but nonexistent DOIs, real author names paired with fabricated titles, and correct journal names with wrong volumes/pages. This skill is specifically designed to catch these patterns.

## Changelog

- **1.3.0**: One existence verdict: `lookup.py existence` turns the statuses of 2a–2d into one word (`EXISTS`, `DOI_NOT_REGISTERED`, `FABRICATED`, `UNVERIFIABLE` or `NOT_INDEXED`), and the Step 3 table is the only definition. `FABRICATED` needs an unregistered DOI and no title match in PubMed or OpenAlex; the new `DOI_NOT_REGISTERED` is a real paper, found by its title, cited with a wrong DOI; the new `UNVERIFIABLE` is a failed lookup or a missing title search and never becomes `FABRICATED`. 2a no longer gives a verdict. Crossref (2b, now through `lookup.py crossref`) also checks a DOI whose doi.org check was `UNVERIFIABLE`. 2d says how to set OPENALEX_STATUS and sends only the title's words. Grey literature is `NOT_INDEXED`. Why: 2a called every unregistered DOI fabricated while the table also required no PubMed and no OpenAlex match, so a real paper cited with a wrong DOI was called fabricated and no flag described that case; the notes used `UNVERIFIABLE`, which the table did not define; a DOI whose doi.org check failed never reached Crossref, which could have confirmed it; OpenAlex rejects a title search that contains a comma or `?` (HTTP 400).
- **1.2.0**: `.bib` files are parsed by `scripts/bib.py` (braces counted as in BibTeX, `"..."` and bare values, LaTeX accents and special letters decoded to Unicode, protective braces dropped). The DOI check asks the doi.org handle API and never the publisher, and PubMed is searched through E-utilities with the whole `TITLE[Title] AND SURNAME[Author]` term URL-encoded (both in `scripts/lookup.py`). The suspicious-DOI check reads `DOI_LIST_JSON` from the environment, and Step 3 shows how to build it from Step 1's output. Step 0 no longer requires TodoWrite. Why: the regex parser cut `{\c{S}}{\i}klar` to `{\c{S`, `{ROHHAD}` to `{ROHHAD` and skipped an entry closed on the line of its last value; Wiley, NEJM and MDPI answer automated requests with HTTP 403, so real DOIs looked broken; curl read `[Title]` as a URL glob and sent nothing; the single-quoted `'$DOI_LIST_JSON'` never expanded; not every environment has TodoWrite.
- **1.1.0**: Step 4 checks each cited claim against the full-text PDF in the project's source folder instead of the abstract: claim list from every cite variant, legal open-access retrieval, identity check, verdict codes, numbers and population rules, and a verified PDF page + verbatim quote for every supporting verdict (`scripts/fulltext.py`). Step 5 adds the claim–source table and `citation-claims.csv`. Why: an abstract-level check cannot show where a paper supports a claim, and misses wrong numbers, wrong populations, secondary citations and wrong PDFs.
- **1.0.0**: Initial version.
