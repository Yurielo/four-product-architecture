# Four-Product Architecture

The private `Yurielo/four-product-architecture` repository, `main`, is the single
central authority for **published current activated releases** of SeminarText,
VideoText, BookText and Integra. A Git commit atomically contains current pointers,
immutable activation history and retained evidence. There is no runtime service.

Read [architecture and native authority](docs/architecture.md) before integration.
The registry never deploys a product or grants acceptance. A local checkout is
a snapshot at its Git revision, not necessarily remote current state.

## Files and local checks

- `registry.json`: four product states and append-only activation history.
- `schemas/registry.schema.json`: JSON Schema draft 2020-12; semantic validation
  additionally enforces identity, history, graph, receipt and rollback constraints.
- `evidence/*.json`: immutable retained native evidence with bound subjects.
- `registry.py`: structural validation, derived dependency status and Git publisher.
- `tests/test_registry.py`: deterministic transitions and isolated local Git transactions.

Python 3.10+ and Git are required. The foundation was verified on Python 3.14.6.
Dependencies are scoped to this checkout; no product environment is changed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python registry.py validate
.venv/bin/python registry.py status
```

To verify a change also preserves history relative to a known commit:

```sh
.venv/bin/python registry.py validate --base EXACT_BASE_COMMIT
```

These checks validate the central repository. They introduce no additional
product QA or Owner Acceptance. No hosted CI, database or new release manager
is necessary for this foundation.

## Event and evidence contract

Use the native lifecycle's **already successful** completion evidence to prepare
an event conforming to `$defs/event` in the schema. `registry.json` contains real
examples; tests contain synthetic examples that must never be published.

An event has product, generation, predecessor, action (`activate` or `rollback`),
rollback target, deployment target, actual/unknown activation time, central
record time, exact native release/artifact identities, actual dependency
identities, evidence references and a content-derived event ID.

For first registration, generation is 1 and predecessor is null. Thereafter it
is previous generation + 1 and predecessor must be the product's current event.
`activated_at` may be null only when the historical evidence does not establish
the time; do not substitute a comment date or the observation time. Version
labels do not identify bytes. Unknown source commits remain null. App/Core
composites retain separate identities; do not assign a Core commit to the GUI.

After preparing all metadata except `event_id`/`evidence`, the native completion
adapter serializes its existing evidence in `evidence/<unique-name>.json`:

```python
import registry

# event is derived from the actual completed native operation, not a build.
receipt = {
    "kind": "native_activation",
    "status": "SUCCEEDED",
    "subject_sha256": registry.subject_hash(event),
    "native_reference": native_completion_reference,
    "native_evidence": existing_native_completion_evidence,
}
payload = registry.encode(receipt)
# Persist payload at a new unique evidence path, preserving original evidence.
event["evidence"] = [{"path": evidence_path, "sha256": registry.sha256(payload)}]
event["event_id"] = registry.event_id(event)
# Persist this complete event once; retries use the exact same bytes/identity.
```

`canonical()` is UTF-8 JSON with sorted keys, compact separators, unescaped
Unicode and no NaN. Event ID is `sha256:` plus SHA-256 of canonical event fields
excluding only `event_id`. Subject hash excludes `event_id` and `evidence`, so
the receipt binds action, generation, predecessor, release, target, times and
dependencies without a circular hash. Evidence reference hashes cover exact
stored file bytes. Unknown fields and ambiguous duplicate JSON keys fail closed.

Digest algorithms are explicit:

- `sha256-file`: SHA-256 of one file's bytes.
- `sha256-file-list-v1`: the native VideoText release-gate algorithm: all regular
  non-symlink files beneath the bundle, byte-sorted `./relative/path`; SHA-256 of
  concatenated `file_sha256 + "  " + relative_path + "\n"` records. It excludes
  directory metadata, permissions and symlinks; native signing/validation stays
  authoritative. Also used for the bounded BookText GUI observation.
- `git-sha1-tree`: exact Git tree object for clean tracked source; it does not
  attest external models/tools or ignored files.
- `sha256-tree-excluding-candidate-manifest`: Integra's existing native Candidate
  algorithm; reuse its manifest, never relabel a different digest algorithm.

Dependency `mode` separates bundled, compiled-from-source and externally pinned
components. A consumer keeps its actual old source/hash even after its provider
updates. New product/component edges require an authorized architecture change.

## Atomic publication and retries

Authenticate Git with write access to this private repository. The CLI requires
its exact GitHub origin and uses existing Git user identity. Inspect remote main,
the applicable native completion evidence and intended event before sending:

```sh
git ls-remote origin refs/heads/main
.venv/bin/python registry.py publish \
  --event /absolute/path/to/completed-activation.json \
  --expected-head EXACT_REMOTE_MAIN_COMMIT
```

The publisher fetches the exact remote commit, validates its registry and retained
evidence, then checks event identity and expected main. It creates new evidence
blobs and registry content in **one** tree/commit whose sole parent is that main.
One leased Git ref update performs compare-and-swap. The lease is not permission
to rewrite history: the constructed commit is always a direct child of the
verified expected head. No checkout, index, local registry or product is replaced.

It reads back remote main and verifies the event before returning PUBLISHED.
Another product may publish concurrently; one transaction wins, the other
must inspect/refetch and retry against the new main. A same-product successor
also requires the correct predecessor/generation. Never just rebase or reseal
a delayed native event over a later activation or rollback.

An exact event already in history returns ALREADY_PUBLISHED even with an old
expected main. This does not reactivate a superseded event: the response includes
the actual current pointer. Different content cannot reuse its event identity.

If native activation succeeds but publication fails, keep the native receipt and
event unchanged: **ACTIVATED / PUBLICATION_PENDING**. Central main still describes
the last published state, not guaranteed instantaneous installation truth. There
is no atomic transaction spanning independent product installation and GitHub.
After an ambiguous push response, read-back detects an already committed event;
otherwise retry the same event only after inspecting central state. No local
pending receipt is an alternative current-version authority.

Because publication leaves the local checkout untouched, use a clean checkout
and `git pull --ff-only` when you need to inspect the newly published snapshot.
Preserve local work if that fast-forward cannot be performed.

## Rollback and partial convergence

First complete the product's existing authorized rollback and native verification.
Then create a new event with higher generation, predecessor=current,
action=rollback and rollback_of=an earlier event for that product. Release,
target and dependency identities must exactly match that earlier event. A new
receipt must attest the restored bytes; an old installation receipt cannot be
reused because its subject differs. All history remains intact. Git-reverting
the registry is not product rollback.

If SeminarText S2 activates while VideoText V1 embeds S1, register S2 and preserve
V1(S1). `status` derives UPDATE_REQUIRED for that edge. It never rewrites V1 or
claims all products synchronized. SOURCE_PIN_MATCH is only source comparison,
not compatibility or semantic acceptance; composite releases with unknown root
source return COMPARISON_UNAVAILABLE. A missing provider registration returns
PROVIDER_UNREGISTERED. Use exact native component identities during integration.

## Trust and operational limits

JSON Schema, hashes and the publisher verify structural consistency and evidence
binding. They do **not** independently authenticate a human decision or prove the
truth of an arbitrary authored receipt. Only an authorized publisher using actual
successful native evidence may publish. Existing native QA/acceptance remains
the authority; this foundation adds no signature service or acceptance board.

Git write/admin access can bypass the helper or change code/history. This small
repository is not a tamper-proof external authority system. Use the governed
publisher, append-only validation and normal access controls; no claim is made
that branch protection or an independent attestation service has been installed.

No product delivery hook or automatic dependency update is installed yet. See
the dependency-ordered next steps in [architecture](docs/architecture.md).
