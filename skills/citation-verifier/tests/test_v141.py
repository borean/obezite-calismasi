"""Failure-first regressions for incomplete evidence and notice identity."""
import hashlib
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import fulltext
import lookup
import report

TITLE = "Growth hormone treatment in children born small for gestational age"
DOI = "10.1000/target.42"

@pytest.mark.parametrize("prefix", ["Correction", "Erratum", "Author Correction", "Retraction Note"])
def test_notice_header_cannot_be_original_even_with_original_title_and_doi(prefix):
    page = f"{prefix}\n{TITLE}\nhttps://doi.org/{DOI}\nThe authors correct an error."
    assert fulltext.identify_pages([page], DOI, TITLE) != "MATCH"

@pytest.mark.parametrize("prefix", ["Correction to:", "Erratum to:", "Retraction of:"])
def test_prefixed_notice_cannot_be_original(prefix):
    page = f"{prefix} {TITLE}\nhttps://doi.org/{DOI}\nThe original article is amended."
    assert fulltext.identify_pages([page], DOI, TITLE) != "MATCH"

def test_deliberate_notice_title_can_match_its_own_doi():
    title = "Correction to: " + TITLE
    page = f"{title}\nhttps://doi.org/10.1000/correction.99"
    assert fulltext.identify_pages([page], "10.1000/correction.99", title) == "MATCH"

def test_original_merely_mentions_correction_in_body():
    page = f"{TITLE}\nhttps://doi.org/{DOI}\nAbstract\nCorrection for multiple comparisons was performed."
    assert fulltext.identify_pages([page], DOI, TITLE) == "MATCH"

def test_et_al_prefix_does_not_verify_omitted_authors():
    result = lookup.compare_authors(["Smith"], [{"family": "Smith"}, {"family": "Jones"}], et_al=True)
    assert result["status"] == "PARTIAL_MATCH"
    assert "omitted" in result["detail"].lower()

def row(source_path, **changes):
    sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    data = dict(citekey="study", sentence="The study reports the stated finding.",
                source_path=str(source_path), source_sha256=sha, source_format="text",
                pdf_page=1, quote="A saved source fixture; no clinical evidence is asserted.", note="Text fixture only.",
                existence="EXISTS",
                metadata="MATCH", notices="NONE_FOUND", authors="MATCH", claim="SUPPORTED",
                verdict="SUPPORTED", abstract_verdict="NOT_REPORTED",
                checked_at="2026-11-07T05:00:00+00:00", human="Example reviewer")
    data.update(changes)
    data["key"] = report.claim_key(data["sentence"], sha, data["citekey"])
    data["disposition"] = {"decision": "accept", "reviewer": data["human"],
                          "reviewed_at": "2026-11-07T05:01:00+00:00",
                          "review_key": report.review_key(data)}
    return data

@pytest.fixture
def source(tmp_path):
    p = tmp_path / "source.txt"
    p.write_text("A saved source fixture; no clinical evidence is asserted.")
    return p

def test_complete_bound_row_is_mechanically_ready(source):
    assert report.summarize([row(source)])["ready"]

@pytest.mark.parametrize("field,value", [
    ("existence", "UNVERIFIABLE"), ("authors", "REVIEW"), ("authors", "PARTIAL_MATCH"),
    ("metadata", "REVIEW"), ("claim", "SECONDARY"), ("notices", "UNKNOWN"),
])
def test_signature_cannot_clear_missing_or_incomplete_evidence(source, field, value):
    result = report.summarize([row(source, **{field: value})])
    assert result["ready"] is False

@pytest.mark.parametrize("field,value", [
    ("existence", "FABRICATED"), ("authors", "MISMATCH"),
    ("metadata", "MISMATCH"), ("claim", "NOT_SUPPORTED"), ("claim", "WRONG_PDF"),
])
def test_generic_override_cannot_clear_blocked_scientific_claim(source, field, value):
    result = report.summarize([row(source, override="I accept", **{field: value})])
    assert result["blocking"] == 1 and result["ready"] is False

def test_stale_sentence_fails_even_with_prior_human_disposition(source):
    data = row(source)
    data["sentence"] = "The study reports a different finding."
    assert not report.summarize([data])["ready"]

def test_exact_sentence_whitespace_is_part_of_binding(source):
    data = row(source)
    data["sentence"] = data["sentence"].replace("study reports", "study  reports")
    assert not report.summarize([data])["ready"]

def test_replaced_source_fails_even_if_old_hash_is_retained(source):
    data = row(source)
    source.write_text("A replacement file.")
    assert not report.summarize([data])["ready"]

def test_citekey_change_invalidates_prior_disposition(source):
    data = row(source)
    data["citekey"] = "another-study"
    assert not report.summarize([data])["ready"]

def test_refreshing_machine_key_cannot_reuse_old_human_disposition(source):
    data = row(source)
    data["sentence"] += " It also shows another result."
    data["key"] = report.claim_key(data["sentence"], data["source_sha256"], data["citekey"])
    assert not report.summarize([data])["ready"]

def test_new_notice_check_invalidates_old_human_disposition(source):
    data = row(source)
    data["checked_at"] = "2026-11-08T05:00:00+00:00"
    assert not report.summarize([data])["ready"]

def test_empty_report_is_not_ready():
    assert not report.summarize([])["ready"]

def test_deliberate_retraction_discussion_requires_explicit_bound_disposition(source):
    data = row(source, notices="RETRACTED", citation_purpose="retraction_discussion")
    data["disposition"].update(decision="retain_retraction_discussion", reason="This sentence reports the retraction, not clinical support.")
    assert report.summarize([data])["ready"]
    data["citation_purpose"] = "positive_scientific_support"
    assert not report.summarize([data])["ready"]

def test_retraction_exception_cannot_clear_another_block(source):
    data = row(source, notices="RETRACTED", citation_purpose="retraction_discussion", claim="NOT_SUPPORTED")
    data["disposition"].update(decision="retain_retraction_discussion", reason="Retraction discussion.")
    assert not report.summarize([data])["ready"]

def test_corrected_paper_requires_reasoned_notice_disposition(source):
    data = row(source, notices="CORRECTED")
    assert not report.summarize([data])["ready"]
    data["disposition"].update(decision="accept_after_notice_review", reason="The correction was opened and does not change this claim.")
    assert report.summarize([data])["ready"]

@pytest.mark.parametrize("left,right,expected", [
    ({"family":"Smith","given":"John"}, {"family":"Smith","given":"James"}, "MISMATCH"),
    ({"family":"Smith","given":"J."}, {"family":"Smith","given":"John"}, "REVIEW"),
    ("Smith", {"family":"Smith","given":"John"}, "PARTIAL_MATCH"),
    ({"name":"TODAY Study Group"}, {"name":"TODAY Study Group"}, "MATCH"),
])
def test_full_author_identity_is_not_established_by_surname_alone(left, right, expected):
    assert lookup.compare_authors([left], [right])["status"] == expected

def test_missing_field_is_not_cleared_by_a_name(source):
    data = row(source)
    del data["metadata"]
    assert not report.summarize([data])["ready"]

def test_absent_disposition_is_not_an_authenticated_signoff(source):
    data = row(source)
    del data["disposition"]
    assert report.summarize([data])["unsigned"] == 1

def test_mismatched_abstract_and_fulltext_cannot_pass(source):
    data = row(source, abstract_verdict="CONTRADICTED")
    assert not report.summarize([data])["ready"]

@pytest.mark.parametrize("field,value", [
    ("pdf_page",999), ("pdf_page",0), ("pdf_page",True), ("pdf_page",1.5),
    ("quote","A quotation absent from this source."),
    ("quote",""), ("quote","word " * 41),
])
def test_bad_quote_or_page_cannot_be_approved_even_with_fresh_disposition(source, field, value):
    data = row(source, **{field:value})
    assert not report.summarize([data])["ready"]

@pytest.mark.parametrize("field,value", [
    ("pdf_page",999), ("quote","A quotation absent from this source."),
    ("note","A materially changed interpretation."), ("verdict","SECONDARY"),
])
def test_quote_page_note_verdict_edit_invalidates_disposition(source, field, value):
    data = row(source)
    before = report.review_key(data)
    data[field] = value
    assert report.review_key(data) != before
    assert not report.summarize([data])["ready"]

def test_report_requires_explicit_text_source_format(source):
    data = row(source)
    data.pop("source_format",None)
    assert not report.summarize([data])["ready"]
