"""Shared interest/tag vocabulary and signal-type enum. Single source of
truth — do not duplicate these in individual agents (see CLAUDE.md Section 4
and Section 6)."""

# Real declared_interests -> topic_tags vocabulary, from Neha's tags.docx
# (2026-08-20), replacing the earlier placeholder domain. Most map 1:1 by
# name. Two calls worth flagging:
# - "International Tax" includes PILLAR_TWO as well as INTL_TAX: Pillar
#   Two has no interest of its own in tags.docx, and is squarely an
#   international-tax sub-topic, so content tagged PILLAR_TWO should
#   score as a full match for someone who only declared International Tax.
# - "Tax Technology" maps to AI_TAX_OPS (the only tax-technology-shaped
#   tag tags.docx actually lists). The already-seeded c001-c008 rows
#   still carry a literal "TAX_TECHNOLOGY" tag (on c003) that isn't in
#   tags.docx's 11-tag list at all — harmless (unmapped tags just never
#   match), but worth cleaning up once c003's real content is swapped in.
INTEREST_TO_TAG: dict[str, list[str]] = {
    "Tax Transformation": ["TAX_TRANSFORMATION"],
    "International Tax": ["INTL_TAX", "PILLAR_TWO"],
    "Transfer Pricing": ["TRANSFER_PRICING"],
    "Cyber Security": ["CYBER_SECURITY"],
    "Tax Technology": ["AI_TAX_OPS"],
    "Compliance Advisory": ["COMPLIANCE_ADVISORY"],
    "ESG Tax & Incentives": ["ESG_TAX"],
    "Mergers & Acquisitions": ["MERGERS_ACQUISITIONS"],
    "Digital Transformation": ["DIGITAL_TRANSFORMATION"],
    "Regulatory Reporting": ["REGULATORY_REPORTING"],
}

# Matches the real signal_weight_config rows in beyondportal-db, verified
# live 2026-08-20, and independently confirmed by tags.docx's signal_type
# list. Summarize/Simplify/Translate all fall under the generic
# AI_TOOL_USED type; Ask AI's is ASK_AI_QUERY. ARTICLE_SHARED and
# CONTENT_DOWNLOAD have no agent/trigger in this POC yet but are valid
# pre-existing signal types.
SIGNAL_TYPES: frozenset[str] = frozenset(
    {
        "ARTICLE_READ",
        "VIDEO_WATCHED",
        "AI_TOOL_USED",
        "ASK_AI_QUERY",
        "ARTICLE_SHARED",
        "CONTENT_DOWNLOAD",
    }
)
