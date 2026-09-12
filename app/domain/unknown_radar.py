"""Part 13.3 (Unknown Radar) and Part 13.4 (Survey Mission). Classifies what's known about a
site for a given knowledge_type, and surfaces which knowledge types still need attention.

Classification rule -- the Blueprint doesn't give exact numeric thresholds here the way C1/C2/
C6/C9 do, so this is a labeling convention over the fields Part 16 already requires (source,
confidence, verified_by), not an invented business number:
- UNKNOWN: no SurveyObservation exists at all for this site + knowledge_type.
- KNOWN: at least one observation exists with verified_by set (someone signed off on it).
- PARTIAL: observations exist, but none are verified -- there's a lead, not a confirmed fact.
"""

import uuid

from app.domain.site_knowledge import find_observations

KNOWN = "KNOWN"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"


def classify_knowledge(session, site_id: uuid.UUID, knowledge_type: str) -> str:
    observations = find_observations(session, site_id, knowledge_type)
    if not observations:
        return UNKNOWN
    if any(obs.verified_by for obs in observations):
        return KNOWN
    return PARTIAL


def survey_checklist(session, site_id: uuid.UUID, relevant_knowledge_types: list[str]) -> dict[str, str]:
    """Part 13.4: which knowledge types for this site still need survey attention.

    `relevant_knowledge_types` is caller-supplied (e.g. by a product's own recipe) rather than
    hardcoded here -- the Blueprint doesn't give a fixed list of what's relevant per product,
    and inventing one would be exactly the kind of business-fact fabrication this repo has been
    avoiding throughout.
    """
    return {kt: classify_knowledge(session, site_id, kt) for kt in relevant_knowledge_types}
