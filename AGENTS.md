# Four-Product Architecture

This repository is the sole central authority for published current activated
releases of SeminarText, VideoText, BookText and Integra. It does not deploy them.

Before work, resolve and read the current canonical unified rules at
`Yurielo/integra`, `main:docs/governance/UNIFIED_CODEX_RULES.md`; record the exact
commit and document SHA-256. `docs/architecture.md` records the foundation's
binding Owner decisions and native lifecycle references.

Use the explicit task scope and verified facts. Preserve the four independent
product lifecycles, existing QA and Owner Acceptance. Never infer activation
from a branch, build, Candidate, accepted Integra CURRENT, or version label.
Do not modify product repositories without separate applicable authorization.

Use `registry.py publish` for activation publication. History and evidence are
immutable; rollback is a new, evidenced activation. Do not force-reset main or
edit a historical event to make a consumer appear synchronized. A new repository
foundation is explicitly authorized; ordinary later changes use a reviewed
branch/PR when required by their task or configured repository rules.

For code changes run `python -m unittest discover -s tests -v` and
`python registry.py validate`. For a change against an existing main also use
`python registry.py validate --base <exact-base-commit>`.
These are repository structural checks, not additional product release gates.
No product builds, inference or E2E are required for this foundation.

Finish authorized safe repository transactions. Report actual checks and
limitations. At a terminal state emit one audible signal as the final local
action, when supported.
