"""citation-verifier 1.4.0: offline tests for Bora's six checks and the review findings.

Run: python3 -m pytest -q tests/   (from the skill folder; no network)
Fixtures are live records saved on 2026-11-07: Wakefield 1998 (Crossref + PubMed).
"""
import json
import hashlib
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import fulltext  # noqa: E402
import lookup  # noqa: E402
import report  # noqa: E402

FIX = HERE / "fixtures"
WAKEFIELD = json.loads((FIX / "wakefield_crossref.json").read_text(encoding="utf-8"))["message"]


# ------------------------------------------------- check 1-2: existence verdict

@pytest.mark.parametrize("doi,crossref,pubmed,openalex,expected", [
    ("NOT_FOUND", "UNVERIFIABLE", "NOT_IN_PUBMED", "NOT_FOUND", "UNVERIFIABLE"),  # failed Crossref
    ("NOT_FOUND", "SKIPPED", "SKIPPED", "NOT_FOUND", "UNVERIFIABLE"),             # PubMed title search never ran
    ("NONE", "SKIPPED", "SKIPPED", "NOT_FOUND", "UNVERIFIABLE"),                  # no DOI and PubMed never ran
    ("NOT_FOUND", "SKIPPED", "NOT_IN_PUBMED", "NOT_FOUND", "FABRICATED"),         # Crossref inapplicable: doi.org is authoritative
    ("NOT_FOUND", "NOT_FOUND", "NOT_IN_PUBMED", "NOT_FOUND", "FABRICATED"),
    ("NONE", "SKIPPED", "NOT_IN_PUBMED", "NOT_FOUND", "NOT_INDEXED"),
    ("NOT_FOUND", "NOT_FOUND", "FOUND", "NOT_FOUND", "DOI_NOT_REGISTERED"),
    ("RESOLVES", "FOUND", "SKIPPED", "SKIPPED", "EXISTS"),
])
def test_existence_never_fabricated_on_incomplete_checks(doi, crossref, pubmed, openalex, expected):
    assert lookup.existence(doi, crossref, pubmed, openalex) == expected


# ------------------------------------------------------ check 3: author identity

def test_surname_normalisation_handles_turkish_dotless_i():
    assert lookup.normalize_surname("Ulukapı") == lookup.normalize_surname("Ulukapi")
    assert lookup.normalize_surname("Şimşek") == lookup.normalize_surname("Simsek")
    assert lookup.normalize_surname("İnce") == lookup.normalize_surname("Ince")
    assert lookup.normalize_surname("van der Berg") == lookup.normalize_surname("VAN DER BERG")


def _cr(*families):
    return [{"family": f, "given": "X"} for f in families]


def test_full_author_list_in_order_matches():
    cited = [{"family": f, "given": "Example"} for f in ["Ulukapı", "Şimşek", "Demir"]]
    remote = [{"family": f, "given": "Example"} for f in ["Ulukapi", "Simsek", "Demir"]]
    assert lookup.compare_authors(cited, remote)["status"] == "MATCH"


def test_chimera_right_first_author_invented_coauthors_fails():
    real = WAKEFIELD["author"]
    assert real[0]["family"].lower() == "wakefield"
    out = lookup.compare_authors(["Wakefield", "Smith", "Jones"], real)
    assert out["status"] == "MISMATCH"


def test_reordered_authors_fail():
    assert lookup.compare_authors(["Demir", "Ulukapi"], _cr("Ulukapi", "Demir"))["status"] == "MISMATCH"


def test_vancouver_et_al_prefix_is_only_partial():
    real = WAKEFIELD["author"]
    cited = [a["family"] for a in real[:6]]
    assert lookup.compare_authors(cited, real, et_al=True)["status"] == "PARTIAL_MATCH"


def test_incomplete_list_without_et_al_needs_review():
    assert lookup.compare_authors(["Ulukapi", "Simsek"], _cr("Ulukapi", "Simsek", "Demir"))["status"] == "REVIEW"


def test_group_author_needs_review():
    crossref = [{"name": "TODAY Study Group"}]
    assert lookup.compare_authors(["TODAY Study Group"], crossref)["status"] == "REVIEW"


# ------------------------------------------------- check 4: publication notices

def test_retraction_read_from_updated_by():
    out = lookup.notices(WAKEFIELD)
    assert out["status"] == "RETRACTED"
    found = {(i["type"], i["doi"].lower()) for i in out["items"]}
    assert ("retraction", "10.1016/s0140-6736(10)60175-4") in found
    assert ("correction", "10.1016/s0140-6736(04)15715-2") in found


def test_cited_doi_that_is_itself_a_notice():
    record = {"DOI": "10.1000/notice.1", "update-to": [{"DOI": "10.1000/original.1", "type": "retraction"}]}
    assert lookup.notices(record)["status"] == "IS_NOTICE"


def test_expression_of_concern_and_correction_are_distinct():
    eoc = {"DOI": "10.1000/a", "updated-by": [{"DOI": "10.1000/n", "type": "expression_of_concern"}]}
    cor = {"DOI": "10.1000/b", "updated-by": [{"DOI": "10.1000/m", "type": "correction"}]}
    assert lookup.notices(eoc)["status"] == "EXPRESSION_OF_CONCERN"
    assert lookup.notices(cor)["status"] == "CORRECTED"


def test_no_notice_is_never_called_clean():
    out = lookup.notices({"DOI": "10.1000/c"})
    assert out["status"] == "NONE_FOUND"
    assert out["items"] == []


def test_pubmed_second_signal():
    out = lookup.pubmed_notices((FIX / "wakefield_pubmed.xml").read_text(encoding="utf-8"))
    assert out["status"] == "RETRACTED"
    assert "Retracted Publication" in out["publication_types"]
    assert "EXPRESSION_OF_CONCERN" in {i["kind"] for i in out["items"]}


# ------------------------------------------------- check 5: abstract, separately

def test_openalex_abstract_reconstruction():
    inv = {"children": [2], "Obesity": [0], "in": [1], "obesity": [4], "with": [3]}
    assert lookup.abstract_from_openalex(inv) == "Obesity in children with obesity"


@pytest.mark.parametrize("abstract,fulltext_verdict,expected", [
    ("COMPATIBLE", "NO_FULLTEXT", "NO_FULLTEXT"),     # the abstract never upgrades a claim
    ("COMPATIBLE", "SUPPORTED", "SUPPORTED"),
    ("CONTRADICTED", "SUPPORTED", "REVIEW"),           # conflict goes to a human
    ("NOT_REPORTED", "SUPPORTED", "SUPPORTED"),        # numbers are often absent from abstracts
    ("UNAVAILABLE", "PARTIAL", "PARTIAL"),
    ("COMPATIBLE", "SOURCE_FAILED", "SOURCE_FAILED"),
    ("COMPATIBLE", "WRONG_PDF", "WRONG_PDF"),
])
def test_abstract_and_fulltext_verdicts_combine(abstract, fulltext_verdict, expected):
    assert report.combine(abstract, fulltext_verdict) == expected


def test_unknown_verdict_codes_are_rejected():
    with pytest.raises(ValueError):
        report.combine("PASSED", "SUPPORTED")


# ------------------------------------------------ check 6: the right full text

TITLE = "Growth hormone treatment in children born small for gestational age"
HEADER = f"Journal of Pediatrics 2020\n{TITLE}\nA. Demir, B. Kaya\nhttps://doi.org/10.1000/target.42\nAbstract\n..."


def test_identify_title_and_doi_in_header():
    assert fulltext.identify_pages([HEADER, "Methods ..."], "10.1000/target.42", TITLE) == "MATCH"


def test_identify_ignores_doi_that_only_appears_in_references():
    other = "Adult hypertension outcomes in primary care\nC. Lee\nhttps://doi.org/10.1000/other.7\nAbstract ..."
    page2 = "Discussion ...\nReferences\n1. Demir A, et al. J Pediatr. 2020. doi:10.1000/target.42"
    assert fulltext.identify_pages([other, page2], "10.1000/target.42", TITLE) == "NO_MATCH"


def test_identify_doi_in_header_but_title_differs_is_conflict():
    page = "Adult hypertension outcomes in primary care\nhttps://doi.org/10.1000/target.42\nAbstract ..."
    assert fulltext.identify_pages([page], "10.1000/target.42", TITLE) == "CONFLICT"


def test_identify_title_matches_but_header_shows_another_doi_is_conflict():
    page = f"{TITLE}\nhttps://doi.org/10.1000/other.7\nAbstract ..."
    assert fulltext.identify_pages([page], "10.1000/target.42", TITLE) == "CONFLICT"


def test_plus_minus_symbols_are_meaningful_in_titles():
    plus = "Bone density in HIV+ adolescents"
    minus = "Bone density in HIV− adolescents\nAbstract ..."
    assert fulltext.title_similarity(plus, minus) < fulltext.TITLE_THRESHOLD
    assert fulltext.identify_pages([minus], None, plus) == "NO_MATCH"
    assert fulltext.title_similarity("HIV-infected adolescents", "HIV-infected adolescents\nAbstract") >= fulltext.TITLE_THRESHOLD


# ------------------------------------------------- report: no hidden failures

def _row(**kw):
    source = FIX / "claim-source.txt"
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    row = {"existence": "EXISTS", "metadata": "MATCH", "notices": "NONE_FOUND",
           "authors": "MATCH", "claim": "SUPPORTED", "verdict": "SUPPORTED",
           "abstract_verdict": "NOT_REPORTED", "human": "Example reviewer",
           "citekey": "fixture", "sentence": "A test claim; not clinical evidence.",
           "source_path": str(source), "source_sha256": sha, "source_format": "text",
           "pdf_page": 1, "quote": "A test claim; not clinical evidence.", "note": "Text fixture only.",
           "checked_at": "2026-11-07T05:00:00+00:00"}
    row.update(kw)
    row["key"] = report.claim_key(row["sentence"], sha, row["citekey"])
    row["disposition"] = {"decision": "accept", "reviewer": row["human"],
                          "reviewed_at": "2026-11-07T05:01:00+00:00",
                          "review_key": report.review_key(row)}
    return row


def test_one_retraction_blocks_even_among_clean_rows():
    rows = [_row() for _ in range(19)] + [_row(notices="RETRACTED")]
    out = report.summarize(rows)
    assert out["blocking"] == 1 and out["ready"] is False


def test_unsigned_rows_are_not_verified():
    out = report.summarize([_row(), _row(human="")])
    assert out["unsigned"] == 1 and out["ready"] is False


@pytest.mark.parametrize("field,value", [
    ("existence", "UNVERIFIABLE"), ("notices", "CORRECTED"), ("notices", "EXPRESSION_OF_CONCERN"),
    ("authors", "REVIEW"), ("claim", "REVIEW"), ("claim", "NO_FULLTEXT"),
])
def test_unresolved_rows_block_readiness_until_signed(field, value):
    out = report.summarize([_row(), _row(human="", **{field: value})])
    assert out["unresolved"] == 1 and out["ready"] is False


def test_clean_signed_rows_are_ready():
    out = report.summarize([_row(), _row()])
    assert out == {"blocking": 0, "unresolved": 0, "unsigned": 0, "ready": True}


def test_verdict_goes_stale_when_sentence_or_source_changes():
    key = report.claim_key("BMI SDS fell by 0.3 in 12 months.", "a" * 64)
    assert report.claim_key("BMI SDS  fell by 0.3 in 12 months.", "a" * 64) != key  # exact sentence binding
    assert report.is_stale({"key": key}, "BMI SDS fell by 0.4 in 12 months.", "a" * 64)
    assert report.is_stale({"key": key}, "BMI SDS fell by 0.3 in 12 months.", "b" * 64)
    assert not report.is_stale({"key": key}, "BMI SDS fell by 0.3 in 12 months.", "a" * 64)


# ------------------------------------------ follow-ups found while building 1.4.0

def test_surnames_with_letters_unicode_does_not_decompose():
    for a, b in [("Sørensen", "Sorensen"), ("Łukasz", "Lukasz"), ("Đorđević", "Dordevic"),
                 ("Æbeltoft", "Aebeltoft"), ("Strauß", "Strauss")]:
        assert lookup.normalize_surname(a) == lookup.normalize_surname(b), (a, b)


def test_signed_review_rows_need_notice_specific_disposition():
    assert report.summarize([_row(), _row(notices="CORRECTED", human="HBU")])["ready"] is False


def test_blocking_rows_need_a_written_reason_not_just_a_signature():
    assert report.summarize([_row(notices="RETRACTED", human="HBU")])["blocking"] == 1
    as_example = _row(notices="RETRACTED", human="HBU", override="cited as an example of a retracted paper")
    assert report.summarize([as_example])["ready"] is False  # generic override is not a notice disposition


def test_summarize_reads_the_combined_column_skill_md_writes():
    row = _row()
    row.pop("claim")
    row["combined"] = "NOT_SUPPORTED"
    assert report.summarize([row])["blocking"] == 1
