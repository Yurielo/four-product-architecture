# Four Products — Vertical-First Development Roadmap

**Status:** Owner-directed roadmap proposal recorded for governed review (2026-10-29).  
**Authority:** This document coordinates cross-product user journeys; it does not replace product-specific roadmaps, Product Rules, native release lifecycles, or the activated-release registry. Proposed reprioritization becomes executable only after its applicable Owner/governance approval and product control-plane reconciliation.

## North star

Deliver a usable end-to-end workflow in which **Seminar A creates human-accepted, source-grounded Canonical Knowledge; Seminar B enriches that same knowledge without losing prior evidence or revisions; users navigate the accumulated knowledge and its history**. Favor the smallest demonstrable vertical slice over independent horizontal subsystem expansion.

- **SeminarText:** owns transcription/timing evidence, semantic proposals and review, Concept identity, Canonical Knowledge admission and immutable development history.
- **VideoText:** owns video, media and subtitles.
- **BookText:** owns document extraction/OCR and exports.
- **Integra:** owns orchestration, cross-product provenance checks and read-only presentation; it never becomes a second semantic authority.
- **Obsidian:** rebuildable derived presentation, not a canonical database.
- **Central four-product registry:** records *activated releases only*, never seminar contents or semantic acceptance.

The accepted provider graph remains ST → VT, ST → Integra, VT → Integra and BT → Integra. No synchronized four-product release is implied by a provider update. Native activation, Owner Acceptance, Dataset/Gold boundaries and semantic human decisions remain independent mandatory gates.

## Vertical delivery sequence

| Slice | User-visible outcome / acceptance evidence | Product owner | Authorization and boundary |
| --- | --- | --- | --- |
| **S1 — One reviewed seminar** | A real **Стресс код** seminar has supported four-video Evidence, human-accepted Topics/Concepts/relations, a validated Canonical Knowledge result, deterministic Obsidian output and working source navigation. Unavailable registered documents and deferred claims are visible, not fabricated. | SeminarText | **Current approved Issue #68**, Draft PR #121. DOMAIN_REVIEW is pending; QA clearance is not semantic acceptance. |
| **Checkpoint — Release / Integration Readiness** | Verify actual integration, provenance, native runtime identity, contract compatibility and outstanding gaps; do not infer production readiness from merged code. | SeminarText, with consumers only where affected | **Existing prescribed checkpoint after #68**; execute only when its existing authorization boundary is satisfied. |
| **S2 — Second seminar enriches accepted knowledge** | A second authorized seminar proposes an existing-Concept enrichment, a human-resolved possible alias, a distinct/new Concept and a deferred/contradictory claim; accepted changes create a new immutable revision with an inspectable before/after history, exact evidence from both seminars and refreshed Obsidian projection. Replay is idempotent; stale inputs and unreviewed claims fail closed. | SeminarText | **PROPOSED ROADMAP CHANGE**: move bounded cross-seminar accumulation ahead of optional Dataset D / Topic Automation expansion. Requires explicit roadmap/scope authorization; no automatic semantic acceptance. |
| **S3 — Navigate accumulated knowledge in Integra** | Read-only Concept, relation, revision/history and exact source-evidence navigation from accepted SeminarText artifacts; missing/stale inputs are explicit and semantic state is not mutated. | Integra | New bounded GUI authorization and normal Integra Candidate/Owner acceptance. Existing PR #305 is a project/source/artifact browser, **not** this knowledge view. |

Obsidian export is reused within S1 and S2; it is **not** a separate late milestone. A history model is part of the first cross-seminar update, not postponed until after updates.

## Minimal missing work and dependency discipline

1. **Finish S1, do not restart it.** Issue #68's four-video evidence, provisional proposals and review package exist. Complete the genuine human semantic decisions, then exercise actual admission/export/navigation; repair only proven integration defects. Four video sources are not seven-of-seven registered-source coverage.
2. **S2 reuses existing primitives.** Stable Concept IDs, aliases, evidence refs, ReviewDecision, relations, revision/lineage and Obsidian exporter exist. The current admission path is source/notebook-bound; a *bounded, versioned extension* must admit reviewed evidence from Seminar B into a revision of Seminar A's accepted knowledge. Add explicit human Concept identity outcomes (SAME_CONCEPT / NEW_CONCEPT / RELATED / DISTINCT / DEFER), preserve original terms and both sources. Do not create another Knowledge Engine or require embeddings.
3. **S3 extends the existing read-only projection.** Integra's current knowledge validator is bounded to a pinned Golden Slice; extend it only for the actual accepted SeminarText contract. Do not copy or mutate canonical semantic records.
4. **Parallel technical tracks remain available**, but Topic Engine production readiness, Dataset D evaluation, a graph database, universal multimodal coverage, full Obsidian synchronization and synchronized releases are **not presumed prerequisites** for bounded S1/S2/S3. Preserve Dataset D as LOCKED TEST, Dataset E exclusion, Gold role/freeze decisions and all source-quality gates.
5. **Product release integration stays provider-to-consumer.** Use exact native release/component identities and the central registry's actual activation events. A PR, Candidate or built artifact is not an activated release. No new central database/service.

## Current evidence and known gaps (snapshot, not a release claim)

- SeminarText: `main` at `a31f3a7a1f743343476a49d2e36d9ad786f05fba`; Issue #68 / PR #121 review work is more advanced than its stale `NOT_STARTED` State projection. Canonical Evidence/Word Timeline and knowledge admission primitives exist; complete-seminar semantic acceptance and cross-seminar journey are not complete.
- Four-product architecture: `main` at `1c0834b3ccd9f36c8f41a3805143582f01166772`; **registry.json**, not this text, is authoritative for current activated releases.
- Integra: seminar library preview merged as PR #303; read-only GUI PR #305 is draft and awaiting Owner test/acceptance. It browses projects/sources/artifacts, not Concepts or development history.
- BookText and VideoText retain their independent product lifecycles; no additional direct ST → BookText edge is introduced.

These SHA values are evidence snapshots only. Refresh GitHub, native runtime and the registry before implementation; never reset newer work to these references.

## Next actions and gates

**Next technical step (existing authority):** mechanically reconcile SeminarText `SEMINARTEXT_4_ROADMAP.md`, `SEMINARTEXT_4_STATE.json` and `integrity/milestone_reconciliation.json` to the exact current Issue #68 review checkpoint, preserving active/incomplete and `accepted:false`. Clarify historical versus current integration status here and in `docs/architecture.md` without rewriting activation history.

**Next product gate:** existing Issue #68 DOMAIN_REVIEW and subsequent accepted S1 knowledge/export evidence.

**Strategic Owner gate:** approve the **proposed** S2-before-Dataset-D/Topic-Automation reprioritization. This roadmap records the proposed vertical direction but does not silently authorize a product Roadmap change or execute S2.

**S3 gate:** separate bounded Integra GUI scope and native acceptance after actual accepted knowledge artifacts exist.

## Definition of progress

A milestone is vertically valuable when it demonstrably changes what a user can do with a real seminar, has source-grounded acceptance evidence, states unsupported coverage honestly, and respects human semantic authority. Technical experiments and component contracts are prerequisites only when an actual blocker is demonstrated. Record IMPLEMENTED, INTEGRATED, ACCEPTED, DEPLOYED, CENTRALLY_REGISTERED and PRODUCTION_READY separately.

## Authoritative references

- [Four Products architecture and integration order](docs/architecture.md)
- [Central activated-release registry](registry.json)
- [SeminarText Roadmap](https://github.com/Yurielo/seminartext/blob/main/SEMINARTEXT_4_ROADMAP.md)
- [SeminarText State](https://github.com/Yurielo/seminartext/blob/main/SEMINARTEXT_4_STATE.json)
- [SeminarText Product Rules](https://github.com/Yurielo/seminartext/blob/main/docs/architecture/SEMINARTEXT_PRODUCT_RULES.md)
- [SeminarText Issue #68](https://github.com/Yurielo/seminartext/issues/68) / [PR #121](https://github.com/Yurielo/seminartext/pull/121)
- [Integra PR #305](https://github.com/Yurielo/integra/pull/305)

Do not duplicate the SeminarText implementation roadmap or activation history here. Keep this document a short cross-product vertical coordination plan.
