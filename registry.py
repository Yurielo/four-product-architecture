#!/usr/bin/env python3
"""Validate and atomically publish activation records; never deploy products."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA = "schemas/registry.schema.json"
PRODUCTS = ("seminartext", "videotext", "booktext", "integra")
# The verified graph, not a presumed linear product hierarchy.
PROVIDERS = {"seminartext": set(), "booktext": set(),
             "videotext": {"seminartext"},
             "integra": {"seminartext", "videotext", "booktext"}}


class Rejected(ValueError):
    pass


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Rejected(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise Rejected(f"non-JSON number: {value}")
    return json.loads(data, object_pairs_hook=unique, parse_constant=invalid)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def event_id(event):
    return "sha256:" + sha256(canonical({k: v for k, v in event.items() if k != "event_id"}))


def subject_hash(event):
    return sha256(canonical({k: v for k, v in event.items() if k not in {"event_id", "evidence"}}))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise Rejected(message)


def schema_check(value, schema):
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
    if errors:
        error = errors[0]
        raise Rejected(f"schema {list(error.absolute_path)}: {error.message}")


def validate(state, schema, read_evidence):
    schema_check(state, schema)
    seen = {}
    latest = {product: None for product in PRODUCTS}
    for event in state["history"]:
        identity, product = event["event_id"], event["product"]
        require(identity == event_id(event), "event content identity mismatch")
        require(identity not in seen, "duplicate history event")
        previous = latest[product]
        require(event["predecessor"] == previous, "wrong predecessor")
        generation = seen[previous]["generation"] + 1 if previous else 1
        require(event["generation"] == generation, "non-monotonic generation")
        require(bool(event["release"]["artifacts"]), "missing installed artifact identity")
        dependencies = event["dependencies"]
        require({d["provider"] for d in dependencies} == PROVIDERS[product],
                "dependency providers differ from the verified graph")
        roles = [(d["provider"], d["role"]) for d in dependencies]
        require(len(roles) == len(set(roles)), "duplicate dependency role")
        for artifacts in [event["release"]["artifacts"]] + [d["artifacts"] for d in dependencies]:
            require(len({a["role"] for a in artifacts}) == len(artifacts), "duplicate artifact role")
            for artifact in artifacts:
                digest = artifact["digest"]
                length = 40 if digest["algorithm"] == "git-sha1-tree" else 64
                require(len(digest["value"]) == length, "digest length does not match algorithm")
        if event["action"] == "rollback":
            target = seen.get(event["rollback_of"])
            require(target is not None and target["product"] == product,
                    "rollback must reference an earlier activation of this product")
            require(event["rollback_of"] != previous, "rollback target is already current")
            for field in ("release", "dependencies", "target"):
                require(event[field] == target[field], f"rollback changed historical {field}")
        else:
            require(event["rollback_of"] is None, "activate cannot specify rollback_of")
        activation_proven = False
        for ref in event["evidence"]:
            data = read_evidence(ref["path"])
            require(sha256(data) == ref["sha256"], "evidence byte identity mismatch")
            proof = decode(data)
            if isinstance(proof, dict) and proof.get("kind") == "native_activation":
                require(proof.get("status") == "SUCCEEDED", "native activation did not succeed")
                require(proof.get("subject_sha256") == subject_hash(event), "activation evidence subject mismatch")
                require(isinstance(proof.get("native_reference"), str) and bool(proof["native_reference"]),
                        "missing native activation reference")
                require(isinstance(proof.get("native_evidence"), dict) and bool(proof["native_evidence"]),
                        "missing retained native evidence")
                activation_proven = True
        require(activation_proven, "no successful native activation evidence")
        seen[identity] = event
        latest[product] = identity
    for product, record in state["products"].items():
        require(record["repository"] == f"Yurielo/{product}", "incorrect repository identity")
        require(record["current"] == latest[product], "current must point to the latest activation")
        require((record["unregistered_reason"] is None) == (latest[product] is not None),
                "unregistered products need a reason; registered products cannot have one")
    return state


def transition(state, event, schema, read_evidence):
    validate(state, schema, read_evidence)
    require(isinstance(event, dict), "event must be an object")
    require(event.get("event_id") == event_id(event), "event content identity mismatch")
    for historical in state["history"]:
        if historical["event_id"] == event["event_id"]:
            require(historical == event, "event identity reused for different content")
            return deepcopy(state), False
    updated = deepcopy(state)
    require(event.get("product") in PRODUCTS, "unknown product")
    updated["history"].append(deepcopy(event))
    updated["products"][event["product"]]["current"] = event["event_id"]
    updated["products"][event["product"]]["unregistered_reason"] = None
    validate(updated, schema, read_evidence)
    return updated, True


def git(repo, *arguments, data=None):
    return subprocess.run(["git", "-C", str(repo), *arguments], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def remote_head(repo):
    line = git(repo, "ls-remote", "--exit-code", "origin", "refs/heads/main").decode().strip()
    parts = line.split()
    require(len(parts) == 2 and parts[1] == "refs/heads/main", "ambiguous remote main")
    head = parts[0]
    git(repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "origin", head)
    return head


def at(repo, commit, path):
    return git(repo, "show", f"{commit}:{path}")


def append_only(previous, current):
    history = previous["history"]
    require(current["history"][:len(history)] == history, "historical records changed or removed")


def dependency_status(state):
    events = {event["event_id"]: event for event in state["history"]}
    result = []
    for consumer, record in state["products"].items():
        if record["current"] is None:
            continue
        for dependency in events[record["current"]]["dependencies"]:
            provider = state["products"][dependency["provider"]]["current"]
            source = events[provider]["release"]["source_commit"] if provider else None
            status = ("PROVIDER_UNREGISTERED" if provider is None else
                      "COMPARISON_UNAVAILABLE" if source is None else
                      "SOURCE_PIN_MATCH" if source == dependency["source_commit"] else "UPDATE_REQUIRED")
            result.append({"provider": dependency["provider"], "consumer": consumer,
                           "role": dependency["role"], "actual_source": dependency["source_commit"],
                           "registered_source": source, "status": status})
    return result


def publish(repo, event, expected_head):
    """Commit registry + new evidence together; CAS-update exactly remote main.

    No checkout, index, product, or local registry file is overwritten. Git
    objects are prepared before the remote ref update. Failed publication
    leaves the remote current state unchanged; input receipts remain retryable.
    """
    require(isinstance(event, dict), "event must be an object")
    head = remote_head(repo)
    schema = decode(at(repo, head, SCHEMA))
    current = decode(at(repo, head, "registry.json"))
    committed = lambda path: at(repo, head, path)
    validate(current, schema, committed)
    require(event.get("event_id") == event_id(event), "event content identity mismatch")
    if any(e == event for e in current["history"]):
        return {"status": "ALREADY_PUBLISHED", "head": head, "event_id": event["event_id"],
                "current": current["products"][event["product"]]["current"]}
    require(head == expected_head, "stale expected main; inspect and reconcile before retry")
    # Validate paths before any local read (schema contains the bounded pattern).
    probe = deepcopy(current)
    probe["history"].append(event)
    schema_check(probe, schema)
    new_files = {}
    for ref in event["evidence"]:
        path = ref["path"]
        exists = bool(git(repo, "ls-tree", head, "--", path).strip())
        if exists:
            payload = committed(path)
        else:
            local = Path(repo) / path
            require(not local.is_symlink() and local.resolve().is_relative_to(Path(repo).resolve()),
                    "evidence must be a regular in-repository file")
            payload = local.read_bytes()
            new_files[path] = payload
        require(sha256(payload) == ref["sha256"], "evidence cannot overwrite history or change identity")
    def read(path):
        return new_files[path] if path in new_files else committed(path)
    updated, changed = transition(current, event, schema, read)
    require(changed, "unexpected duplicate")
    append_only(current, updated)
    # Build Git trees directly without touching the checkout or index.
    # Existing trees and evidence are preserved byte-for-byte.
    def replace_tree(tree, path_parts, blob):
        entries = {}
        for line in git(repo, "ls-tree", "-z", tree).split(b"\0"):
            if line:
                meta, name = line.split(b"\t", 1)
                entries[name.decode()] = meta.decode()
        name = path_parts[0]
        if len(path_parts) == 1:
            entries[name] = f"100644 blob {blob}"
        else:
            child = entries.get(name)
            require(child is None or child.startswith("040000 tree "), "evidence parent is not a tree")
            child_tree = child.split()[2] if child else git(repo, "mktree", data=b"").decode().strip()
            new_child = replace_tree(child_tree, path_parts[1:], blob)
            entries[name] = f"040000 tree {new_child}"
        raw = b"".join(f"{meta}\t{name}".encode() + b"\0" for name, meta in sorted(entries.items()))
        return git(repo, "mktree", "-z", data=raw).decode().strip()
    tree = git(repo, "rev-parse", f"{head}^{{tree}}").decode().strip()
    for path, payload in {**new_files, "registry.json": encode(updated)}.items():
        blob = git(repo, "hash-object", "-w", "--stdin", data=payload).decode().strip()
        tree = replace_tree(tree, path.split("/"), blob)
    message = f"Record {event['product']} {event['action']} generation {event['generation']}\n"
    commit = git(repo, "commit-tree", tree, "-p", head, data=message.encode()).decode().strip()
    try:
        # The commit has exactly the verified old head as parent: this lease
        # cannot rewrite history. It adds exact compare-and-swap semantics.
        git(repo, "push", "--porcelain", f"--force-with-lease=refs/heads/main:{head}",
            "origin", f"{commit}:refs/heads/main")
    except subprocess.CalledProcessError as failure:
        observed = remote_head(repo)
        state = decode(at(repo, observed, "registry.json"))
        validate(state, decode(at(repo, observed, SCHEMA)), lambda path: at(repo, observed, path))
        if event not in state["history"]:
            raise Rejected("PUBLICATION_PENDING: push failed or lost CAS; preserve receipt, inspect remote") from failure
    observed = remote_head(repo)
    state = decode(at(repo, observed, "registry.json"))
    validate(state, decode(at(repo, observed, SCHEMA)), lambda path: at(repo, observed, path))
    require(event in state["history"], "PUBLICATION_PENDING: event absent at read-back")
    return {"status": "PUBLISHED", "head": observed, "event_id": event["event_id"],
            "current": state["products"][event["product"]]["current"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate")
    check.add_argument("--base", help="Verify append-only history against this exact Git commit")
    commands.add_parser("status")
    send = commands.add_parser("publish")
    send.add_argument("--event", type=Path, required=True)
    send.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        if args.command == "publish":
            remote = git(ROOT, "remote", "get-url", "origin").decode().strip().removesuffix(".git")
            require(remote in {"https://github.com/Yurielo/four-product-architecture",
                               "git@github.com:Yurielo/four-product-architecture"}, "unexpected central origin")
            result = publish(ROOT, decode(args.event.read_bytes()), args.expected_head)
        else:
            schema = decode((ROOT / SCHEMA).read_bytes())
            state = validate(decode((ROOT / "registry.json").read_bytes()), schema,
                             lambda path: (ROOT / path).read_bytes())
            if args.command == "validate" and args.base:
                base = git(ROOT, "rev-parse", "--verify", "--end-of-options", f"{args.base}^{{commit}}").decode().strip()
                previous = decode(at(ROOT, base, "registry.json"))
                validate(previous, decode(at(ROOT, base, SCHEMA)), lambda path: at(ROOT, base, path))
                append_only(previous, state)
            result = {"status": "VALID", "events": len(state["history"]), "products": state["products"],
                      "dependency_status": dependency_status(state),
                      "note": "Source comparison only; no assertion of compatibility or global synchronization."}
        print(json.dumps(result, indent=2))
        return 0
    except (Rejected, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"REJECTED / PUBLICATION NOT CONFIRMED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
