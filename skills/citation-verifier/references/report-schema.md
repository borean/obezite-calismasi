# Citation report row schema

The helper checks supplied records. It does not authenticate reviewers or independently decide whether a quotation supports a claim. Never fabricate a human name, approval, date or rationale.

Required row fields:
- `line`, `manuscript_path`, `citekey`, `sentence`: occurrence location and exact current sentence. The caller must check extraction against the current manuscript; the helper does not parse TeX.
- `source_path`: absolute path to the saved full-text source; `source_sha256`: its SHA-256. The helper rereads the bytes.
- `source_format`: explicitly `pdf` or `text`. PDF rows require the expected `reference_doi` and `reference_title`; identity is rechecked with the full-text helper. Saved UTF-8 text is treated as one page; its source identity and provenance require the separately documented metadata review. A PDF cannot be relabelled as text to bypass PDF checks.
- `key`: `report.claim_key(sentence, source_sha256, citekey)`, or `report.py key SENTENCE SHA256 --citekey KEY`.
- `checked_at`: ISO timestamp with timezone for this check revision. Refresh it when metadata/notices are rechecked.
- `existence`: EXISTS / DOI_NOT_REGISTERED / FABRICATED / UNVERIFIABLE / NOT_INDEXED.
- `metadata`: MATCH / MISMATCH / REVIEW / UNVERIFIED, covering the title, journal and publication years. Preserve the detailed compared records separately.
- `authors`: MATCH / MISMATCH / REVIEW / PARTIAL_MATCH. MATCH requires complete ordered identities; a surname-only or et-al prefix comparison is partial.
- `notices`: NONE_FOUND / RETRACTED / IS_NOTICE / CORRECTED / EXPRESSION_OF_CONCERN / UNVERIFIABLE. Preserve each source, raw evidence and notice link/date separately.
- `abstract_verdict`: COMPATIBLE / NOT_REPORTED / CONTRADICTED / UNAVAILABLE.
- `verdict`: SUPPORTED / PARTIAL / NOT_SUPPORTED / SECONDARY / NO_FULLTEXT / WRONG_PDF / SOURCE_FAILED.
- `claim` or `combined`: the output of `report.py combine ABSTRACT VERDICT`; inconsistent combination cannot pass.
- `pdf_page`, `quote`, `note`: exact evidence. SUPPORTED, PARTIAL and SECONDARY require a positive integer page and a nonempty quotation of at most 40 words. Summarization re-extracts PDFs in reading/layout order, checks reference identity, and requires the quotation on that exact page. Saved text uses page 1 and the same findable-quotation rule. These checks do not determine semantic support.
- `human`: recorded reviewer name/initials, empty until that person decides.
- `disposition`: object with `decision`, `reviewer` matching `human`, timezone-bearing `reviewed_at`, and `review_key`.

For an actual reviewer decision, calculate the current review key with `report.py review-key row.json` (one row object). It binds the claim key, source location/format/expected identity, full-text verdict/page/quote/note, current stage statuses, abstract verdict, check timestamp and citation purpose. Only after the reviewer decides, record that key in their disposition; generating the key is not approval.

Allowed dispositions:
- `accept`: every stage is complete, source/claim bindings match, and the reviewer accepts the row.
- `accept_after_notice_review`: only CORRECTED or EXPRESSION_OF_CONCERN remains; all other stages are clear. Requires a specific `reason` explaining the actual notice review.
- `retain_retraction_discussion`: only RETRACTED or IS_NOTICE blocks the row; `citation_purpose` must be `retraction_discussion`, with a specific `reason`. All other checks, including full-text support for the retraction-discussion sentence, must pass. Positive clinical support is not an allowed exception.

No generic `override` is honored. Missing/unknown/failed stages, unsupported claims, wrong PDFs, mismatched authors, partial identities, secondary claims and stale bindings must be resolved rather than signed away. Deliberate nonstandard sources need a separately documented review path; this bounded helper leaves them unresolved.

Save full `rows.json` as the canonical machine record. CSV is a readable export: retain all fields above; JSON-encode the disposition object in its cell. A CSV alone must not discard the sentence, path, hash, check revision or stage codes. Recompute bindings and review keys after edits; earlier signatures never automatically transfer.

The source hash checks bytes, not truth. PDF identity and page/quotation checks are rerun mechanically; interpretation, saved-text provenance, DOI/metadata/notice/abstract judgments and citation coverage still require the wider workflow. `ready: true` is mechanical record completeness, not externally authenticated human approval or submission authorization.
