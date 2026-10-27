"""Synthetic registry transitions and real Git transactions on local test repos.

No product application, model, network remote or product E2E is executed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import registry as r


class RegistryFixture:
    def setUp(self):
        self.schema = r.decode((r.ROOT / r.SCHEMA).read_bytes())
        self.state = r.decode((r.ROOT / "registry.json").read_bytes())
        self.files = {ref["path"]: (r.ROOT / ref["path"]).read_bytes()
                      for event in self.state["history"] for ref in event["evidence"]}

    def validate(self, state=None):
        return r.validate(self.state if state is None else state, self.schema, self.files.__getitem__)

    def seal(self, event, suffix):
        proof = {"kind": "native_activation", "status": "SUCCEEDED",
                 "subject_sha256": r.subject_hash(event), "native_reference": "test://synthetic-only",
                 "native_evidence": {"fixture": suffix, "not_product_evidence": True}}
        path = f"evidence/test-{suffix}.json"
        self.files[path] = r.encode(proof)
        event["evidence"] = [{"path": path, "sha256": r.sha256(self.files[path])}]
        event["event_id"] = r.event_id(event)
        return event

    def event(self, suffix="next", state=None, product="booktext"):
        state = self.state if state is None else state
        previous = state["products"][product]["current"]
        old = next(e for e in state["history"] if e["event_id"] == previous) if previous else None
        event = {"product": product, "generation": old["generation"] + 1 if old else 1,
                 "predecessor": previous, "action": "activate", "rollback_of": None,
                 "target": "local-primary", "activated_at": "2026-10-27T12:00:00Z",
                 "recorded_at": "2026-10-27T12:01:00Z", "dependencies": [],
                 "release": {"native_ref": "test://synthetic-only", "version": suffix, "build": "test",
                             "source_commit": r.sha256(suffix.encode())[:40],
                             "artifacts": [{"role": "test-artifact", "location": "/test/not-installed",
                                            "source_commit": None,
                                            "digest": {"algorithm": "sha256-file", "value": "a" * 64}}]}}
        return self.seal(event, suffix)

    def apply(self, event, state=None):
        return r.transition(self.state if state is None else state, event, self.schema, self.files.__getitem__)

class RegistryTests(RegistryFixture, unittest.TestCase):
    def test_initial_state_and_explicit_unregistered(self):
        self.validate()
        self.assertEqual(len(self.state["history"]), 2)
        for name in ("seminartext", "integra"):
            self.assertIsNone(self.state["products"][name]["current"])
            self.assertTrue(self.state["products"][name]["unregistered_reason"])

    def test_successful_activation_and_immutable_input(self):
        before = deepcopy(self.state)
        event = self.event()
        updated, changed = self.apply(event)
        self.assertTrue(changed)
        self.assertEqual(updated["products"]["booktext"]["current"], event["event_id"])
        self.assertEqual(self.state, before)
        self.assertEqual(updated["history"][:-1], before["history"])

    def test_exact_duplicate_is_noop_even_after_later_activation(self):
        first = self.event("first")
        state, _ = self.apply(first)
        later = self.event("later", state)
        state, _ = self.apply(later, state)
        retry, changed = self.apply(first, state)
        self.assertFalse(changed)
        self.assertEqual(retry, state)

    def test_altered_content_cannot_reuse_event_identity(self):
        event = self.event()
        event["release"]["version"] = "tampered"
        with self.assertRaisesRegex(r.Rejected, "identity"):
            self.apply(event)

    def test_missing_failed_and_wrong_subject_receipts(self):
        for change in ("missing", "failed", "subject", "native_payload", "reference"):
            with self.subTest(change=change):
                event = self.event(change)
                path = event["evidence"][0]["path"]
                proof = r.decode(self.files[path])
                if change == "missing": proof["kind"] = "build"
                if change == "failed": proof["status"] = "FAILED"
                if change == "subject": proof["subject_sha256"] = "0" * 64
                if change == "native_payload": proof["native_evidence"] = {}
                if change == "reference": proof["native_reference"] = ""
                self.files[path] = r.encode(proof)
                event["evidence"][0]["sha256"] = r.sha256(self.files[path])
                event["event_id"] = r.event_id(event)
                with self.assertRaises(r.Rejected): self.apply(event)

    def test_evidence_tampering_is_rejected(self):
        event = self.event()
        self.files[event["evidence"][0]["path"]] += b" "
        with self.assertRaisesRegex(r.Rejected, "evidence byte"):
            self.apply(event)

    def test_wrong_predecessor_and_generation(self):
        for key, value in [("predecessor", None), ("generation", 1), ("generation", 10)]:
            with self.subTest(key=key, value=value):
                event = self.event()
                event[key] = value
                self.seal(event, "bad-chain")
                with self.assertRaises(r.Rejected): self.apply(event)

    def test_schema_rejects_unknown_fields_paths_dates_and_digest_lengths(self):
        changes = [lambda e: e.update(extra=True),
                   lambda e: e.update(recorded_at="yesterday"),
                   lambda e: e["evidence"][0].update(path="../outside.json"),
                   lambda e: e["release"]["artifacts"][0]["digest"].update(value="a" * 40)]
        for change in changes:
            event = self.event()
            change(event)
            event["event_id"] = r.event_id(event)
            with self.assertRaises(r.Rejected): self.apply(event)

    def test_invented_booktext_dependency_is_rejected(self):
        event = self.event()
        event["dependencies"] = deepcopy(self.state["history"][0]["dependencies"])
        self.seal(event, "invented-edge")
        with self.assertRaisesRegex(r.Rejected, "verified graph"):
            self.apply(event)

    def test_missing_videotext_dependency_is_rejected(self):
        event = self.event("video", product="videotext")
        with self.assertRaisesRegex(r.Rejected, "verified graph"):
            self.apply(event)

    def test_s2_activation_preserves_v1_s1_and_reports_update(self):
        original = deepcopy(self.state["history"][0])
        s2 = self.event("s2", product="seminartext")
        state, _ = self.apply(s2)
        self.assertEqual(state["history"][0], original)
        self.assertEqual(state["products"]["videotext"]["current"], original["event_id"])
        edge = r.dependency_status(state)[0]
        self.assertEqual(edge["status"], "UPDATE_REQUIRED")
        self.assertEqual(edge["actual_source"], original["dependencies"][0]["source_commit"])
        self.assertEqual(edge["registered_source"], s2["release"]["source_commit"])

    def test_rollback_is_new_event_and_preserves_history(self):
        original = next(e for e in self.state["history"] if e["product"] == "booktext")
        newer = self.event()
        state, _ = self.apply(newer)
        rollback = self.event("rollback", state)
        rollback.update(action="rollback", rollback_of=original["event_id"],
                        release=deepcopy(original["release"]), dependencies=deepcopy(original["dependencies"]))
        self.seal(rollback, "rollback")
        restored, changed = self.apply(rollback, state)
        self.assertTrue(changed)
        self.assertEqual(restored["history"][:-1], state["history"])
        self.assertEqual(rollback["generation"], 3)
        self.assertNotEqual(rollback["event_id"], original["event_id"])
        delayed = self.event("delayed", state)
        with self.assertRaisesRegex(r.Rejected, "predecessor"):
            self.apply(delayed, restored)

    def test_rollback_rejects_changed_bytes_wrong_product_and_reused_proof(self):
        target = next(e for e in self.state["history"] if e["product"] == "booktext")
        state, _ = self.apply(self.event())
        for defect in ("bytes", "product", "proof"):
            event = self.event("rollback", state)
            event.update(action="rollback", rollback_of=target["event_id"], release=deepcopy(target["release"]))
            if defect == "bytes": event["release"]["version"] = "different"
            if defect == "product": event["rollback_of"] = state["history"][0]["event_id"]
            self.seal(event, "rollback-invalid")
            if defect == "proof":
                event["evidence"] = deepcopy(target["evidence"])
                event["event_id"] = r.event_id(event)
            with self.assertRaises(r.Rejected): self.apply(event, state)

    def test_current_and_historical_mutations_fail(self):
        bad = deepcopy(self.state)
        bad["products"]["booktext"]["current"] = bad["products"]["videotext"]["current"]
        with self.assertRaises(r.Rejected): self.validate(bad)
        bad = deepcopy(self.state)
        bad["history"][0]["target"] = "other"
        with self.assertRaises(r.Rejected): self.validate(bad)
        with self.assertRaises(r.Rejected): r.append_only(self.state, {"history": []})

    def test_ambiguous_json_is_rejected(self):
        for payload in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(r.Rejected): r.decode(payload)

    def test_nonobject_and_rollback_to_current_are_rejected(self):
        with self.assertRaisesRegex(r.Rejected, "object"):
            self.apply([])
        event = self.event()
        event.update(action="rollback", rollback_of=event["predecessor"])
        self.seal(event, "same-current")
        with self.assertRaisesRegex(r.Rejected, "already current"):
            self.apply(event)

    def test_rollback_cannot_change_embedded_dependency(self):
        target = self.state["history"][0]
        newer = self.event("v2", product="videotext")
        newer["dependencies"] = deepcopy(target["dependencies"])
        self.seal(newer, "v2")
        state, _ = self.apply(newer)
        rollback = self.event("rollback-video", state, "videotext")
        rollback.update(action="rollback", rollback_of=target["event_id"],
                        release=deepcopy(target["release"]), dependencies=deepcopy(target["dependencies"]))
        rollback["dependencies"][0]["source_commit"] = "0" * 40
        self.seal(rollback, "rollback-video")
        with self.assertRaisesRegex(r.Rejected, "historical dependencies"):
            self.apply(rollback, state)


class PublicationTests(RegistryFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="four-product-registry-test-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote, self.client = root / "remote.git", root / "client"
        r.git(root, "init", "--bare", "-b", "main", str(self.remote))
        r.git(root, "clone", str(self.remote), str(self.client))
        r.git(self.client, "config", "user.name", "Registry Test")
        r.git(self.client, "config", "user.email", "registry-test@example.invalid")
        (self.client / "schemas").mkdir()
        (self.client / r.SCHEMA).write_bytes(r.encode(self.schema))
        (self.client / "registry.json").write_bytes(r.encode(self.state))
        self.write_files(self.client)
        r.git(self.client, "add", ".")
        r.git(self.client, "commit", "-m", "Test baseline")
        r.git(self.client, "push", "origin", "main")
        self.head = r.git(self.client, "rev-parse", "HEAD").decode().strip()

    def write_files(self, client):
        (client / "evidence").mkdir(exist_ok=True)
        for path, data in self.files.items(): (client / path).write_bytes(data)

    def remote_state(self):
        return r.decode(r.git(self.remote, "show", "main:registry.json"))

    def test_real_git_publication_is_atomic_and_retry_is_idempotent(self):
        event = self.event()
        self.write_files(self.client)
        before = (self.client / "registry.json").read_bytes()
        result = r.publish(self.client, event, self.head)
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(r.git(self.remote, "rev-parse", "main^").decode().strip(), self.head)
        state = self.remote_state()
        r.validate(state, self.schema, lambda path: r.git(self.remote, "show", f"main:{path}"))
        self.assertEqual(state["history"][-1], event)
        retry = r.publish(self.client, event, self.head)
        self.assertEqual(retry["status"], "ALREADY_PUBLISHED")
        self.assertEqual(retry["head"], result["head"])
        self.assertEqual((self.client / "registry.json").read_bytes(), before)

    def test_stale_expected_head_is_rejected(self):
        event = self.event(); self.write_files(self.client)
        with self.assertRaisesRegex(r.Rejected, "stale expected"):
            r.publish(self.client, event, "0" * 40)
        self.assertEqual(self.remote_state(), self.state)

    def test_existing_evidence_path_cannot_be_overwritten(self):
        event = self.event()
        old_path = self.state["history"][0]["evidence"][0]["path"]
        new_data = self.files[event["evidence"][0]["path"]]
        self.files[old_path] = new_data
        event["evidence"] = [{"path": old_path, "sha256": r.sha256(new_data)}]
        event["event_id"] = r.event_id(event)
        self.write_files(self.client)
        with self.assertRaisesRegex(r.Rejected, "overwrite history"):
            r.publish(self.client, event, self.head)
        self.assertEqual(self.remote_state(), self.state)

    def test_push_failure_preserves_remote_and_receipt(self):
        event = self.event(); self.write_files(self.client)
        original = r.git
        def failed(repo, *args, **kwargs):
            if args[0] == "push": raise subprocess.CalledProcessError(1, ["git", "push"])
            return original(repo, *args, **kwargs)
        with patch.object(r, "git", side_effect=failed):
            with self.assertRaisesRegex(r.Rejected, "PUBLICATION_PENDING"):
                r.publish(self.client, event, self.head)
        self.assertEqual(self.remote_state(), self.state)
        self.assertTrue((self.client / event["evidence"][0]["path"]).exists())
        self.assertEqual(r.publish(self.client, event, self.head)["status"], "PUBLISHED")

    def test_lost_success_response_is_recovered_by_readback(self):
        event = self.event(); self.write_files(self.client)
        original = r.git
        def ambiguous(repo, *args, **kwargs):
            result = original(repo, *args, **kwargs)
            if args[0] == "push": raise subprocess.CalledProcessError(1, ["git", "push"])
            return result
        with patch.object(r, "git", side_effect=ambiguous):
            self.assertEqual(r.publish(self.client, event, self.head)["status"], "PUBLISHED")
        self.assertEqual(self.remote_state()["history"][-1], event)

    def test_concurrent_writers_only_one_wins_cas(self):
        other = self.client.parent / "other"
        r.git(self.client.parent, "clone", str(self.remote), str(other))
        r.git(other, "config", "user.name", "Registry Test")
        r.git(other, "config", "user.email", "registry-test@example.invalid")
        first, second = self.event("first"), self.event("second")
        self.write_files(self.client); self.write_files(other)
        barrier = threading.Barrier(2)
        original = r.git
        def synchronized(repo, *args, **kwargs):
            if args[0] == "push": barrier.wait(timeout=10)
            return original(repo, *args, **kwargs)
        def attempt(client, event):
            try: return r.publish(client, event, self.head)["status"]
            except r.Rejected: return "REJECTED"
        with patch.object(r, "git", side_effect=synchronized), ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(attempt, self.client, first)
            two = pool.submit(attempt, other, second)
            self.assertCountEqual([one.result(), two.result()], ["PUBLISHED", "REJECTED"])
        self.assertEqual(len(self.remote_state()["history"]), len(self.state["history"]) + 1)


if __name__ == "__main__":
    unittest.main()
