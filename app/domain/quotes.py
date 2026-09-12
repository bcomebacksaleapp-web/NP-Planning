import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models.quote import Quote, QuoteLine, QuoteRevision
from app.domain.constitution import combine_gate_statuses, evaluate_gm30_gate
from app.domain.events import record_event
from app.domain.pricing import gross_margin_percent
from app.domain.revisioning import next_revision_number


def _build_revision(
    quote_id: uuid.UUID,
    revision_number: int,
    true_cost: float,
    selling_price: float,
    lines: list[dict],
    restored_from: int | None = None,
    additional_gates: list[tuple[str, str]] | None = None,
) -> QuoteRevision:
    """`additional_gates` lets a caller fold other Constitution gates (e.g. C3's quantity-basis
    check) into this quote's overall gate_status via combine_gate_statuses -- so a placeholder-
    quantity quote can never show as a clean PASS just because its GM% alone would pass C2
    (Part 5: a high score on one gate must not compensate for a hard block/override on another).
    """
    gm_percent = gross_margin_percent(selling_price, true_cost)
    gm_status, gm_note = evaluate_gm30_gate(gm_percent)

    other_gates = additional_gates or []
    gate_status = combine_gate_statuses([gm_status] + [status for status, _ in other_gates])
    gate_note = "; ".join(note for note in [gm_note] + [n for _, n in other_gates] if note)

    revision = QuoteRevision(
        quote_id=quote_id,
        revision_number=revision_number,
        true_cost=true_cost,
        selling_price=selling_price,
        gm_percent=gm_percent,
        gate_status=gate_status,
        gate_note=gate_note,
        restored_from_revision_number=restored_from,
    )
    revision.lines = [
        QuoteLine(
            description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_total=line["quantity"] * line["unit_price"],
            product_id=line.get("product_id"),
        )
        for line in lines
    ]
    return revision


def create_quote(
    session: Session,
    project_id: uuid.UUID,
    true_cost: float,
    selling_price: float,
    lines: list[dict],
    actor_user_id: uuid.UUID | None = None,
    additional_gates: list[tuple[str, str]] | None = None,
) -> Quote:
    quote = Quote(project_id=project_id)
    session.add(quote)
    session.flush()

    revision = _build_revision(quote.id, 1, true_cost, selling_price, lines, additional_gates=additional_gates)
    session.add(revision)
    session.flush()
    record_event(
        session,
        "quote",
        quote.id,
        "created",
        {"revision_number": 1, "gate_status": revision.gate_status, "gm_percent": revision.gm_percent},
        actor_user_id,
    )
    return quote


def update_quote(
    session: Session,
    quote: Quote,
    true_cost: float,
    selling_price: float,
    lines: list[dict],
    actor_user_id: uuid.UUID | None = None,
    additional_gates: list[tuple[str, str]] | None = None,
) -> QuoteRevision:
    revision_number = next_revision_number(session, QuoteRevision, "quote_id", quote.id)
    revision = _build_revision(
        quote.id, revision_number, true_cost, selling_price, lines, additional_gates=additional_gates
    )
    session.add(revision)
    session.flush()
    record_event(
        session,
        "quote",
        quote.id,
        "revision_created",
        {"revision_number": revision_number, "gate_status": revision.gate_status, "gm_percent": revision.gm_percent},
        actor_user_id,
    )
    return revision


def restore_quote_revision(
    session: Session, quote: Quote, target_revision_number: int, actor_user_id: uuid.UUID | None = None
) -> QuoteRevision:
    """Law 4: restoring Rev N creates a NEW revision copying Rev N's price basis and lines. It
    never touches the old rows -- the gate decision is re-evaluated (not copied verbatim) so a
    restored revision's gate_status always reflects the current GM30 rules, in case those rules
    changed between when Rev N was created and now."""
    target = session.execute(
        select(QuoteRevision).where(
            QuoteRevision.quote_id == quote.id,
            QuoteRevision.revision_number == target_revision_number,
        )
    ).scalar_one()

    lines = [
        {
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "product_id": line.product_id,
        }
        for line in target.lines
    ]
    new_revision_number = next_revision_number(session, QuoteRevision, "quote_id", quote.id)
    revision = _build_revision(
        quote.id,
        new_revision_number,
        target.true_cost,
        target.selling_price,
        lines,
        restored_from=target.revision_number,
    )
    session.add(revision)
    session.flush()
    record_event(
        session,
        "quote",
        quote.id,
        "revision_restored",
        {"revision_number": new_revision_number, "restored_from_revision_number": target.revision_number},
        actor_user_id,
    )
    return revision
