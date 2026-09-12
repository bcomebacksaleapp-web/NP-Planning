"""Part 13.1: Next Best Action. "What should we do next?" Every recommendation follows the
Blueprint's own pattern: Detect -> Explain -> Recommend -> Execute/Draft (never auto-executed --
Law 14: AI may READ/SUGGEST/DRAFT, COMMIT requires explicit human authorization).

Recommendations are derived only from structural facts already recorded by this system (Quote
gate_status, CriticalSpec state) -- not from invented business judgment about what "good" looks
like beyond what the Constitution gates (C1-C10) already define. If a situation isn't already
covered by an existing gate or state, this module deliberately has nothing to say about it
rather than guessing.
"""

from dataclasses import dataclass

from app.core.models.critical_spec import CriticalSpec
from app.core.models.quote import Quote, QuoteRevision
from app.domain.revisioning import latest_revision


@dataclass(frozen=True)
class NextBestAction:
    issue: str
    why: str
    risk: str
    recommended_action: str
    # READ / SUGGEST / DRAFT / COMMIT (Part 24) -- the level of AI autonomy appropriate for the
    # recommended_action itself. Never COMMIT here: nothing in this module is allowed to
    # recommend an action strong enough to require that level (Law 14).
    allowed_next_action: str


def recommend_for_quote(session, quote: Quote) -> list[NextBestAction]:
    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    if current is None:
        return []

    if current.gate_status == "BLOCKED":
        return [
            NextBestAction(
                issue="Quote is blocked by a Constitution gate",
                why=current.gate_note,
                risk="Cannot be confirmed until resolved (Part 5: no commercial override on a hard block)",
                recommended_action="Revise pricing, quantity basis, or cost inputs and re-quote",
                allowed_next_action="DRAFT",
            )
        ]
    if current.gate_status == "OVERRIDE_REQUIRED":
        return [
            NextBestAction(
                issue="Quote requires an explicit override to confirm",
                why=current.gate_note,
                risk="Confirming without an override_reason is refused (Law 12: who/why)",
                recommended_action="Obtain management/senior sign-off and supply an override reason before confirming",
                allowed_next_action="SUGGEST",
            )
        ]
    return []


def recommend_for_critical_spec(spec: CriticalSpec) -> list[NextBestAction]:
    if spec.state == "DISCUSSION":
        return [
            NextBestAction(
                issue=f"Critical spec '{spec.spec_type}' is still in Discussion",
                why="C5: no critical spec without confirmation -- procurement/fabrication cannot proceed on an unconfirmed spec",
                risk="Proceeding without confirming risks procuring/fabricating the wrong item",
                recommended_action="Advance to Proposed once a specific option is settled on",
                allowed_next_action="SUGGEST",
            )
        ]
    if spec.state == "PROPOSED":
        return [
            NextBestAction(
                issue=f"Critical spec '{spec.spec_type}' is Proposed but not yet Confirmed",
                why="C5: no critical spec without confirmation",
                risk="Proceeding without confirming risks procuring/fabricating the wrong item",
                recommended_action="Get explicit confirmation (confirmed_by) before proceeding",
                allowed_next_action="SUGGEST",
            )
        ]
    return []
