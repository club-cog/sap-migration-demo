"""Reference cases where the Python port deliberately differs from the legacy output.

ONLY add an entry here together with ``docs/findings/<model>.md`` and a PR flagged
"Human decision needed". Never edit ``legacy/reference_outputs`` instead.

Format: ``{model: {case_id: reason}}``. Listed cases run as strict ``xfail``: if a listed
case starts matching the reference, the suite fails so the list stays honest.
"""

_WEEKEND_TRUNCATION = (
    "legacy weekend path truncates the call amount (rounding.to_unit_v1, Quill L55) instead of "
    "rounding half-up; port rounds half-up. Human decision needed: "
    "docs/findings/collateral_margin_call.md"
)

KNOWN_DEVIATIONS: dict[str, dict[str, str]] = {
    "collateral_margin_call": {
        "MC-006": _WEEKEND_TRUNCATION,
        "MC-012": _WEEKEND_TRUNCATION,
        "MC-023": _WEEKEND_TRUNCATION,
    },
}
