import re
import time

import requests

from google import genai

from core.env import require
from core.matrix import MatrixRegistry, format_for_prompt
from core.rag import cache
from core.vessel import VesselProfile

SYSTEM_PROMPT = """You are the Ocean GRC Compliance Engine, a precise context layer built for United Kingdom Maritime and Coastguard Agency (MCA) statutes, specifically the Sport or Pleasure Vessel Code (SPVC) and the Workboat Code Edition 3 (WBC3).

Your primary task is to eliminate general legal summaries and enforce strict real-world vessel specifications.

[CORE ARCHITECTURAL STATE]
The context layer has locked in this user's verified vessel attributes:
- Vessel Type: {vessel_type}
- Length overall (LOA): {vessel_length} metres
- Operating Area Category: Category {area_category}
- Hull Material: {hull_material}
- Passenger Count: {passenger_count}

[CRITICAL INSTRUCTIONS FOR REASONING]
1. APPLICABILITY IS ALREADY FILTERED. The clauses below have been mechanically
   filtered against the vessel state above: any clause whose scope explicitly
   excludes this vessel has already been removed before you saw it. Treat every
   clause you are given as potentially binding. Do not re-derive applicability
   from scratch, and never reference rules for other categories or lengths as if
   they bound this vessel. If a clause carries a scope condition, restate it
   verbatim in the Statutory Reference Matrix.

2. CROSS-MATRIX TABLES. Maritime codes rely heavily on multi-variable tables.
   When a retrieved extract is tabular and its row/column structure is intact,
   trace the intersection of this vessel's specifications and state the direct
   value.
   When the extract is tabular but the structure has been flattened during
   extraction — values present with no recoverable row and column headers — you
   must NOT guess the intersection. Name the table, give its page number, state
   which two axes the user must read across, and mark the verdict as REQUIRES
   VISUAL CONFIRMATION. A fabricated matrix value is the single most damaging
   output this system can produce.

3. CONDITIONAL EXEMPTIONS. If a clause contains parent/child rules or footnotes
   ("Except as provided in Section 7.4", "For vessels under 15m only"), evaluate
   them against the verified vessel length and category. If the clause depends on
   a cross-referenced section that is NOT present in the extracts below, say so
   explicitly and name the missing reference. Never assume the content of a
   clause you cannot see.

4. SOURCE DISCIPLINE. Answer only from the extracts provided. Do not use outside
   knowledge of maritime regulations. Never paraphrase legal terms or
   definitions — quote them.

5. HONEST REFUSAL. If the extracts do not address the question, say so plainly
   in the Direct Applicability Verdict and name where the answer is likely to
   sit instead (the Regulations rather than the Code, a commercially licensed
   ISO/BSI standard, or Certifying Authority discretion). A reliable refusal is
   worth more to a surveyor than a confident guess.

[OUTPUT SPECIFICATION FOR SURVEYORS & AUDITORS]

Begin EVERY response with a single machine-readable verdict line, exactly:

VERDICT: <STATUS> — <one sentence, max 20 words>

<STATUS> must be exactly one of:
  REQUIRED        the extracts establish this IS required for this vessel
  NOT_REQUIRED    the extracts positively establish it is NOT required — only
                  where a clause says so, never merely because nothing was found
  CONDITIONAL     required only if some stated condition holds
  NOT_ESTABLISHED the extracts do not settle it either way

The distinction between NOT_REQUIRED and NOT_ESTABLISHED is the most important
judgement you make. "No retrieved clause imposes this" is NOT_ESTABLISHED. Only
use NOT_REQUIRED when a provision affirmatively exempts or excludes this vessel.
Reporting absence of evidence as evidence of absence is the single most
dangerous error available to you: a designer who reads NOT_REQUIRED will stop
looking, and may omit something the Code requires elsewhere.

Then the three-part body:

### ✅ Direct Applicability Verdict
[A clear, 1-2 sentence direct answer customised exactly to their {vessel_length}m, Category {area_category} vessel specifications. Bold the mandatory action or equipment required. If the answer is not in the extracts, say so here instead.]

### 🔎 Statutory Reference Matrix
- **Applicable Code:** [Name of Code]
- **Exact Binding Anchor:** Clause/Section [e.g. 17.5.3 or Table 14.11.2], p.[page]
- **Scope Condition:** [The specific rule criteria, e.g. "Vessels >= 15m operating in Category 2"]

CITATION PRECISION. Anywhere you reference a provision — in any of the three
sections above — give the full clause number exactly as it appears in the
extract you are citing, e.g. "Clause 5.6.3.1". Never give a range or a guess
("Section 5 or 6", "somewhere in Section 12"). If you cannot identify the
governing clause precisely from the extracts, that is a NOT_ESTABLISHED verdict
and you must say the extracts do not identify it — an imprecise citation is
worse than none, because a reader cannot check it.

### 🗒 True Context Extract
> [The exact textual extraction or structured matrix rows retrieved from the code database. Never paraphrase legal terms or definitions.]
"""

NO_VESSEL_PROMPT = """You are the Ocean GRC Compliance Engine, a precise context layer for UK MCA statutes (SPVC and Workboat Code Edition 3).

[CORE ARCHITECTURAL STATE]
No vessel profile has been locked in for this user. Applicability filtering is
therefore INACTIVE, and the extracts below may include clauses that do not bind
the user's vessel.

Because of this you must:
- Answer in general terms only, and state every scope condition attached to each
  clause you cite ("this applies to vessels under 15m in Category 2 or 3").
- Open the Direct Applicability Verdict by noting that no vessel profile is set,
  and that adding one will narrow the answer to their vessel.
- Never present a scoped clause as if it binds the reader unconditionally.

All other rules — source discipline, honest refusal, no paraphrasing of legal
terms, no guessing flattened table intersections — apply unchanged.

[OUTPUT SPECIFICATION]
### ✅ Direct Applicability Verdict
[General answer, opening with the missing-profile note.]

### 🔎 Statutory Reference Matrix
- **Applicable Code:** [Name of Code]
- **Exact Binding Anchor:** Clause/Section [x.x.x], p.[page]
- **Scope Condition:** [Who the clause actually binds]

### 🗒 True Context Extract
> [Verbatim extract.]
"""

class _TransientGenerationError(Exception):
    """Provider-side failure worth retrying or failing over, with its kind."""

    def __init__(self, kind: str, detail):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


VERDICT_PATTERN = re.compile(
    r"^\s*VERDICT:\s*(REQUIRED|NOT_REQUIRED|CONDITIONAL|NOT_ESTABLISHED)\s*[—\-–]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def split_verdict(answer_text: str):
    """Pull the machine-readable verdict line off the front of an answer.

    Returned separately so the UI renders a status the MODEL asserted. Deriving
    it in the frontend would mean inferring a legal position from prose — the
    difference between "not required" and "not established" is exactly what
    cannot be guessed at.
    """
    match = VERDICT_PATTERN.search(answer_text or "")
    if not match:
        return None, answer_text

    status = match.group(1).upper()
    summary = match.group(2).strip()
    body = (answer_text[: match.start()] + answer_text[match.end() :]).lstrip("\n")
    return {"status": status, "summary": summary}, body


LOW_CONFIDENCE_THRESHOLD = 0.45
CACHE_SIMILARITY_THRESHOLD = 0.92

# Matches both prose citations ("Clause 8.3.2") and the Binding Anchor line
# ("Clause/Section 17.5.3"), plus table anchors ("Table 14.11.2").
CITATION_PATTERN = re.compile(
    r"(?:Clause|Section|Table)[/\s]*(?:Section\s*)?([0-9]+[A-Z]?(?:\.[0-9]+)*)",
    re.IGNORECASE,
)

# Dotted clause numbers appearing anywhere in retrieved statute — including
# bare cross-references like "the requirements of 5.6.1 and 5.6.2", which carry
# no "Clause" prefix. Requires at least one dot so ordinary numbers (measurements,
# percentages, years) are not mistaken for provisions.
CROSS_REFERENCE_PATTERN = re.compile(r"\b(\d+[A-Z]?(?:\.\d+)+)\b")

# Language that makes a provision conditional or transitional. A "not required"
# statement qualified by any of these is an exemption for a SPECIFIC class of
# vessel — typically one transitioning from a superseded code — not a general
# exemption. Treating one as the other is the most dangerous output this system
# can produce, because a designer who reads NOT_REQUIRED stops looking.
CONDITIONAL_EXEMPTION_MARKERS = (
    "existing vessel",
    "transitioning from",
    "transitional",
    "provided that",
    "providing the vessel",
    "unless",
    "but where",
    "where a watertight",
    "shall be considered to meet",
    "may be accepted",
    "at the discretion",
)

# Structure-bearing markers. If a tabular extract retains none of these, its
# rows and columns did not survive extraction and the intersection cannot be
# traced mechanically.
TABLE_STRUCTURE_MARKERS = ("|", "\t", "\n")

NO_ANSWER_VERDICT = (
    "VERDICT: NOT_ESTABLISHED — No clause in the ingested Codes addresses this "
    "for your vessel.\n\n"
    "### ✅ Direct Applicability Verdict\n"
    "I could not find a clause in the ingested Code that directly addresses this "
    "for your {descriptor}. This may sit in the Merchant Shipping Regulations "
    "rather than the Code itself, in a commercially licensed ISO/BSI standard "
    "that cannot be reproduced here, or in Certifying Authority discretion — "
    "please check with the MCA or your Certifying Authority directly.\n\n"
    "### 🔎 Statutory Reference Matrix\n"
    "- **Applicable Code:** None matched\n"
    "- **Exact Binding Anchor:** Not found\n"
    "- **Scope Condition:** Not applicable\n\n"
    "### 🗒 True Context Extract\n"
    "> No extract met the retrieval confidence threshold for this question."
)


COMPARE_PROMPT = """You are the Ocean GRC Compliance Engine performing a CROSS-CODE COMPARISON for a naval architect or surveyor.

[CORE ARCHITECTURAL STATE]
- Vessel Type: {vessel_type}
- Length overall (LOA): {vessel_length} metres
- Operating Area Category: Category {area_category}
- Hull Material: {hull_material}
- Passenger Count: {passenger_count}

You are given extracts from TWO OR MORE codes, kept separate and labelled. Each
set has already been filtered against the vessel state above.

Your task is to state what actually DIFFERS for this specific vessel between the
codes — not to summarise each code in turn.

Rules:
- Compare only on points where you have extracts from both codes. If one code
  has no retrieved extract on a point, say "no comparable extract retrieved from
  [code]" rather than inferring silence means no requirement.
- Quote the binding clause from each code side by side.
- Where the codes agree, say so plainly and briefly. Difference is the product.
- Never infer a value from a flattened table. Mark it REQUIRES VISUAL CONFIRMATION.

[OUTPUT SPECIFICATION]

### ⚖️ Cross-Code Verdict
[1-3 sentences: for this {vessel_length}m Category {area_category} vessel, what materially changes between the codes. **Bold** the practical consequence.]

### 📊 Side-by-Side Requirements
| Requirement | {code_list} |
|---|---|
[One row per point of comparison. Cite clause and page in each cell.]

### 🗒 True Context Extracts
**[Code name]** — Clause X.X.X, p.NN
> [verbatim]

**[Code name]** — Clause Y.Y.Y, p.NN
> [verbatim]

### ⚠️ Not Established
[Any point where extracts were missing from one side, or a table could not be read.]
"""


class Answerer:
    # Pinned deliberately, not "gemini-flash-latest". This product's claim is
    # reproducible, auditable answers; a floating model alias would change the
    # engine underneath a published eval result without any code change.
    # (gemini-2.5-flash was retired for new API keys — it 404s.)
    def __init__(self, registry, model: str = "gemini-3.5-flash", matrices=None):
        self.registry = registry
        self.model = model
        self.matrices = matrices if matrices is not None else MatrixRegistry()

        self.api_key = require("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.last_model_used = model

    # Gemini's free tier exhausts quickly under eval load. Retry transient
    # limits rather than recording a failed test case — a 429 is an
    # infrastructure fact, not an answer-quality result, and conflating the two
    # corrupts the metric.
    GEN_MAX_RETRIES = 4
    GEN_BACKOFF_BASE_SECONDS = 5.0

    # Tried in order when the primary is overloaded. A 503 is Google's capacity,
    # not ours, and it would otherwise take the whole product down for the
    # duration. The model that actually answered is returned alongside the text
    # so it can be recorded — silently substituting a model would make the
    # engine version in a provenance record false.
    # Verified reachable. Google retires models without notice — 2.5-flash and
    # 2.5-flash-lite both now 404 for new keys — and a capacity incident can take
    # out some generations while leaving others healthy, so the chain spans
    # different generations rather than different sizes of the same one.
    FALLBACK_MODELS = ("gemini-3.6-flash", "gemini-flash-lite-latest")

    # Different provider, different infrastructure. The only failover that
    # survives a Google-wide incident.
    COHERE_MODEL = "command-r-08-2024"

    @staticmethod
    def _classify(message: str) -> str:
        """quota | overloaded | fatal — they need different responses."""
        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            return "quota"
        if "503" in message or "UNAVAILABLE" in message or "overloaded" in message.lower():
            return "overloaded"
        return "fatal"

    def _try_model(self, model: str, prompt: str):
        """Attempt one model with backoff. Returns text, or raises with a kind."""
        last_error = None
        kind = "fatal"

        for attempt in range(self.GEN_MAX_RETRIES):
            try:
                return self.client.models.generate_content(model=model, contents=prompt).text
            except Exception as exc:
                message = str(exc)
                kind = self._classify(message)
                if kind == "fatal":
                    raise
                last_error = message

                # Quota does not recover on a 35-second timescale, and it is
                # account-wide rather than per-model. Retrying it burned ~105
                # seconds across the candidate chain before the cross-provider
                # failover was even attempted — long enough that the UI looked
                # dead. Fail out immediately so Cohere is reached at once.
                if kind == "quota":
                    break

                if attempt < self.GEN_MAX_RETRIES - 1:
                    time.sleep(self.GEN_BACKOFF_BASE_SECONDS * (2**attempt))

        raise _TransientGenerationError(kind, last_error)

    def _generate_cohere(self, prompt: str) -> str:
        """Last-resort generation on a different provider entirely.

        Gemini quota is account-wide and Google capacity outages hit every Gemini
        model at once, so failing over between them does not protect a live
        demonstration. Cohere is a separate company on separate infrastructure —
        the only failover that survives a whole-provider incident.

        The answer will be produced by a smaller, older model, so the strict
        three-part format may come back less cleanly. That is a deliberate
        trade: a slightly weaker answer beats a stack trace in front of a
        customer, and `model_used` records which engine actually answered so the
        provenance record stays true.
        """
        response = requests.post(
            "https://api.cohere.com/v2/chat",
            headers={
                "Authorization": f"Bearer {require('COHERE_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.COHERE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=90,
        )

        if response.status_code != 200:
            raise _TransientGenerationError(
                "overloaded", f"Cohere {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        text = "".join(
            block.get("text", "")
            for block in payload.get("message", {}).get("content", [])
            if block.get("type") == "text"
        )
        if not text.strip():
            raise _TransientGenerationError("overloaded", "Cohere returned an empty message")
        return text

    def _generate(self, prompt: str) -> str:
        text, model_used = self._generate_with_model(prompt)
        self.last_model_used = model_used
        return text

    def _generate_with_model(self, prompt: str):
        last = None

        for model in (self.model,) + self.FALLBACK_MODELS:
            try:
                return self._try_model(model, prompt), model
            except Exception as exc:
                # A retired model (404) or any other hard error on ONE candidate
                # must not end the request — that is precisely when the
                # remaining candidates matter. Only exhausting every provider is
                # a real failure.
                if not isinstance(exc, _TransientGenerationError):
                    print(f"[answer] {model} unusable ({str(exc)[:80]}), trying next candidate")
                    last = _TransientGenerationError("fatal", str(exc))
                    continue
                last = exc
                if exc.kind == "quota":
                    # Free-tier quota is account-wide, so every other Gemini
                    # model is exhausted too. Stop wasting time and cross
                    # providers.
                    print("[answer] Gemini quota exhausted — failing over to Cohere")
                    break
                print(f"[answer] {model} unavailable, trying next candidate")

        try:
            return self._generate_cohere(prompt), f"cohere:{self.COHERE_MODEL}"
        except _TransientGenerationError as exc:
            cohere_detail = str(exc.detail)[:200]

        raise RuntimeError(
            "Both generation providers are unavailable. "
            f"Gemini: {str(last.detail)[:160] if last else 'unknown'} | "
            f"Cohere: {cohere_detail}"
        )

    def _verify_citations(self, answer_text: str, sources: list) -> bool:
        """Every anchor the model cites must exist in what it was given.

        Clauses flagged unreliable are deliberately excluded from the accepted
        set: their labels are parser artefacts, so citing one is a fabricated
        reference even though the underlying text was retrieved.

        Known limit, and it is the important one — this proves the citation was
        RETRIEVED, not that it is the RIGHT clause for the question. The
        applicability filter is what narrows "retrieved" toward "correct"; this
        check only catches invention.
        """
        cited = set(CITATION_PATTERN.findall(answer_text))

        grounded = {
            str(s["clause"])
            for s in sources
            if s.get("clause") and s.get("clause_reliable", True)
        }

        # Clause numbers appearing INSIDE retrieved statute are grounded too.
        # Clause 5.6.3.1 reads "...meeting the requirements of 5.6.1 and 5.6.2",
        # so a model that names 5.6.1 read it from the extract rather than
        # inventing it. Before this, correctly reporting an unretrieved
        # cross-reference — which instruction 3 explicitly requires — was marked
        # as an unverified citation, penalising the exact behaviour the prompt
        # asks for.
        for source in sources:
            for match in CROSS_REFERENCE_PATTERN.findall(source.get("text", "")):
                grounded.add(match)

        return cited.issubset(grounded) if cited else True

    @staticmethod
    def _structure_note(result: dict) -> str:
        """Flag tabular extracts whose row/column structure did not survive."""
        if result.get("content_type") != "table":
            return ""
        if any(marker in result["text"] for marker in TABLE_STRUCTURE_MARKERS):
            return ""
        return (
            "  [STRUCTURE WARNING: this is tabular content whose row and column "
            "headers were lost during PDF extraction. Do NOT infer the "
            "intersection value. Name the table and page and mark the verdict "
            "REQUIRES VISUAL CONFIRMATION.]"
        )

    @staticmethod
    def _guard_not_required(verdict, answer_text: str, sources: list):
        """Downgrade an unsupported NOT_REQUIRED verdict to CONDITIONAL.

        A prompt instruction is not enough here. Smaller fallback models in
        particular will read "existing vessels transitioning from MGN 280 ... are
        not required to be fitted" and report it as a general exemption, losing
        the class the exemption actually applies to.

        So: NOT_REQUIRED is only allowed to stand when no clause the answer
        relied on carries conditional or transitional language. Where one does,
        the verdict becomes CONDITIONAL and the qualifying phrase is named, which
        is the honest reading — the vessel MIGHT be exempt, if it falls in that
        class, and only the user can establish that.

        Never rewrites the body, only the verdict. The reasoning stays visible so
        the reader can judge it.
        """
        if not verdict or verdict.get("status") != "NOT_REQUIRED":
            return verdict, None

        for source in sources:
            text = (source.get("text") or "").lower()
            for marker in CONDITIONAL_EXEMPTION_MARKERS:
                if marker in text:
                    return (
                        {
                            "status": "CONDITIONAL",
                            "summary": (
                                f"Exemption found, but it is conditional — it turns on "
                                f'"{marker}". Confirm your vessel falls in that class '
                                f"before relying on it."
                            ),
                        },
                        {
                            "downgraded_from": "NOT_REQUIRED",
                            "reason": (
                                f"The exemption relied on is qualified by "
                                f'"{marker}" in Clause {source.get("clause")} '
                                f"(p.{source.get('page')}). A conditional exemption is "
                                f"not a general one."
                            ),
                        },
                    )

        return verdict, None

    def _build_context(self, results: list) -> str:
        blocks = []
        for r in results:
            code = r.get("code_name", "")
            prefix = f"[{code}] " if code else ""
            if r.get("clause_reliable", True):
                header = f"{prefix}[Clause {r['clause_number']}, Page {r['page_number']}]"
            else:
                # Clause label is a parser artefact. Give the model the page and
                # section instead so it anchors to something real rather than
                # citing a clause number that does not exist in the Code.
                header = (
                    f"{prefix}[Page {r['page_number']} — CLAUSE NUMBER UNRELIABLE, "
                    f"cite by page and section only]"
                )
            if r.get("section_title"):
                header += f" — {r['section_title']}"
            scope = f"  Scope condition: {r.get('scope_condition', 'not parsed')}"
            blocks.append(
                f"{header}\n{scope}{self._structure_note(r)}\n{r['text']}"
            )
        return "\n\n".join(blocks)

    def ask(
        self,
        question: str,
        top_k: int = 5,
        vessel: VesselProfile | None = None,
        code_ids: list[str] | None = None,
    ):
        query_embedding = self.registry.embed_query(question)

        # The cache is partitioned by vessel scope. Without this, an answer
        # computed for an 11m Category 2 vessel could be served verbatim to a
        # 20m Category 0 vessel asking a near-identical question — a wrong
        # answer with a valid citation, which is the exact failure this whole
        # layer exists to prevent.
        # The corpus set is part of the cache identity: the same question asked
        # against SPVC alone and against SPVC+WBC3 are different questions.
        scope_key = cache.scope_key(vessel, code_ids or self.registry.available_ids)

        cached = cache.find_similar(
            query_embedding, scope_key=scope_key, threshold=CACHE_SIMILARITY_THRESHOLD
        )
        if cached:
            return {
                "answer": cached["answer"],
                "sources": cached["sources"],
                "filtered_out": cached["filtered_out"],
                "verified": cached["verified"],
                "from_cache": True,
                "guardrail_triggered": None,
                "vessel": vessel.to_dict() if vessel else None,
                "filtering_active": vessel is not None,
            }

        retrieval = self.registry.search(
            question, top_k=top_k, vessel=vessel, code_ids=code_ids
        )
        results = retrieval["results"]
        filtered_out = retrieval["filtered_out"]

        sources = [
            {
                "clause": r["clause_number"],
                "page": r["page_number"],
                "score": r["score"],
                "text": r["text"],
                "scope_condition": r["scope_condition"],
                "content_type": r["content_type"],
                "clause_reliable": r.get("clause_reliable", True),
                "code_id": r.get("code_id"),
                "code_name": r.get("code_name"),
            }
            for r in results
        ]
        top_score = results[0]["score"] if results else 0

        if top_score < LOW_CONFIDENCE_THRESHOLD:
            descriptor = vessel.describe() if vessel else "vessel"
            answer = NO_ANSWER_VERDICT.format(descriptor=descriptor)
            cache.store(
                question, query_embedding, answer, sources, filtered_out,
                verified=True, scope_key=scope_key,
            )
            return {
                "answer": answer,
                "sources": sources,
                "filtered_out": filtered_out,
                "verified": True,
                "from_cache": False,
                "guardrail_triggered": "low_retrieval_confidence",
                "vessel": vessel.to_dict() if vessel else None,
                "filtering_active": retrieval["filtering_active"],
                "verdict": split_verdict(answer)[0],
            }

        if vessel:
            system_prompt = SYSTEM_PROMPT.format(
                vessel_type=vessel.vessel_type,
                vessel_length=vessel.length_overall,
                area_category=vessel.area_category,
                hull_material=vessel.hull_material,
                passenger_count=vessel.passenger_count,
            )
        else:
            system_prompt = NO_VESSEL_PROMPT

        context = self._build_context(results)

        # Excluded clauses are deliberately NOT named in the prompt.
        #
        # An earlier version listed them under "do not cite these". Measured
        # leakage was 16.7% — the model cited them anyway, because naming a
        # clause number in context makes it available to be cited no matter what
        # instruction accompanies it. A negative instruction cannot beat the
        # presence of the token.
        #
        # The exclusions still reach the caller in the API response, which is
        # what the debug panel renders. They just never reach the model.
        exclusion_note = (
            f"\n\n[{len(filtered_out)} clause(s) were removed by the applicability "
            f"filter before you saw this context because they cannot bind this "
            f"vessel. They are not shown and must not be guessed at.]"
            if filtered_out
            else ""
        )

        # Deterministic table lookups, where a verified transcription exists.
        # These bypass retrieval entirely — the intersection is resolved by the
        # matrix, so the model states the value instead of declining to read a
        # flattened table.
        matrix_hits = self.matrices.resolve_for(question, vessel, code_ids)
        matrix_note = format_for_prompt(matrix_hits)

        answer_text = self._generate(
            f"{system_prompt}\n\nRetrieved clauses:\n\n{context}"
            f"{exclusion_note}{matrix_note}\n\nQuestion: {question}"
        )

        guarded_verdict, guard_note = self._guard_not_required(
            split_verdict(answer_text)[0], answer_text, sources
        )
        if guard_note:
            print(f"[answer] verdict downgraded: {guard_note['reason']}")
        verified = self._verify_citations(answer_text, sources)

        cache.store(
            question, query_embedding, answer_text, sources, filtered_out,
            verified=verified, scope_key=scope_key,
        )

        return {
            "answer": answer_text,
            "sources": sources,
            "filtered_out": filtered_out,
            "verified": verified,
            "from_cache": False,
            "guardrail_triggered": None,
            "vessel": vessel.to_dict() if vessel else None,
            "filtering_active": retrieval["filtering_active"],
            "codes_searched": retrieval["codes_searched"],
            "matrix_hits": matrix_hits,
            "verdict": guarded_verdict,
            "verdict_guard": guard_note,
            # Which model actually produced this. Normally self.model, but a
            # provider capacity failure can fail over — and a record claiming an
            # engine that did not answer is worse than no record.
            "model_used": self.last_model_used,
        }

    def compare(
        self,
        question: str,
        code_ids: list[str],
        top_k: int = 4,
        vessel: VesselProfile | None = None,
    ):
        """Answer one question against several codes at once, side by side.

        The retrieval sets are kept per-code rather than blended, because a
        blended set cannot support a difference claim — the model would have no
        way to tell whether silence from one code means "no requirement" or
        "nothing retrieved". Missing extracts are reported, never inferred.
        """
        if len(code_ids) < 2:
            raise ValueError("Comparison needs at least two code_ids.")

        query_embedding = self.registry.embed_query(question)
        key = cache.scope_key(vessel, code_ids, mode="compare")

        cached = cache.find_similar(
            query_embedding, scope_key=key, threshold=CACHE_SIMILARITY_THRESHOLD
        )
        if cached:
            return {
                "answer": cached["answer"],
                "sources": cached["sources"],
                "filtered_out": cached["filtered_out"],
                "verified": cached["verified"],
                "from_cache": True,
                "vessel": vessel.to_dict() if vessel else None,
                "codes_compared": code_ids,
            }

        comparison = self.registry.compare(
            question, top_k=top_k, vessel=vessel, code_ids=code_ids
        )

        sources, blocks = [], []
        for code_id, payload in comparison["per_code"].items():
            results = payload["results"]
            if not results:
                blocks.append(
                    f"=== {payload['code_name']} ===\n"
                    f"NO EXTRACTS RETRIEVED. Report this as 'no comparable extract "
                    f"retrieved' — do not infer that the code is silent on the point."
                )
                continue
            blocks.append(f"=== {payload['code_name']} ===\n{self._build_context(results)}")
            for r in results:
                sources.append(
                    {
                        "clause": r["clause_number"],
                        "page": r["page_number"],
                        "score": r["score"],
                        "text": r["text"],
                        "scope_condition": r["scope_condition"],
                        "content_type": r["content_type"],
                        "clause_reliable": r.get("clause_reliable", True),
                        "code_id": code_id,
                        "code_name": r.get("code_name"),
                    }
                )

        if not sources:
            answer = NO_ANSWER_VERDICT.format(
                descriptor=vessel.describe() if vessel else "vessel"
            )
            return {
                "answer": answer,
                "sources": [],
                "filtered_out": comparison["filtered_out"],
                "verified": True,
                "from_cache": False,
                "vessel": vessel.to_dict() if vessel else None,
                "codes_compared": code_ids,
            }

        code_list = " | ".join(
            comparison["per_code"][c]["short_name"] for c in comparison["per_code"]
        )
        vessel_for_prompt = vessel or VesselProfile("unspecified", 1.0, 0, "unspecified", 0)
        prompt = COMPARE_PROMPT.format(
            vessel_type=vessel_for_prompt.vessel_type if vessel else "not set",
            vessel_length=vessel_for_prompt.length_overall if vessel else "not set",
            area_category=vessel_for_prompt.area_category if vessel else "not set",
            hull_material=vessel_for_prompt.hull_material if vessel else "not set",
            passenger_count=vessel_for_prompt.passenger_count if vessel else "not set",
            code_list=code_list,
        )

        answer_text = self._generate(
            f"{prompt}\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}"
        )
        verified = self._verify_citations(answer_text, sources)

        cache.store(
            question, query_embedding, answer_text, sources,
            comparison["filtered_out"], verified=verified, scope_key=key,
        )

        return {
            "answer": answer_text,
            "sources": sources,
            "filtered_out": comparison["filtered_out"],
            "verified": verified,
            "from_cache": False,
            "vessel": vessel.to_dict() if vessel else None,
            "codes_compared": code_ids,
        }
