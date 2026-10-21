"""Reference cases where the Python port deliberately differs from the legacy output.

ONLY add an entry here together with ``docs/findings/<model>.md`` and a PR flagged
"Human decision needed". Never edit ``legacy/reference_outputs`` instead.

Format: ``{model: {case_id: reason}}``. Listed cases run as strict ``xfail``: if a listed
case starts matching the reference, the suite fails so the list stays honest.
"""

KNOWN_DEVIATIONS: dict[str, dict[str, str]] = {}
