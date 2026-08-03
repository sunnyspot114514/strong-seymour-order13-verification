#!/usr/bin/env python3
"""Regression tests for strict adaptive-certificate audits."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audit_adaptive_certificate import audit_tree, leaf_cnf_sha256, parse_parent_cnf, sha256


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class AdaptiveCertificateAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.parent = self.root / "parent.cnf"
        self.parent.write_text("p cnf 1 0\n", encoding="ascii", newline="\n")
        self.tree = self.root / "adaptive"
        self.round = self.tree / "round_01"
        self.certificate = self.round / "certificate"
        self.certificate.mkdir(parents=True)
        (self.tree / "root.cubes").write_text(
            "a 0\n", encoding="ascii", newline="\n"
        )
        (self.round / "parents.cubes").write_text(
            "a 0\n", encoding="ascii", newline="\n"
        )
        (self.round / "children.cubes").write_text(
            "a -1 0\na 1 0\n", encoding="ascii", newline="\n"
        )
        self.proof = self.certificate / "cube_00000.core.rup.xz"
        self.proof.write_bytes(b"synthetic-compressed-proof")
        self._write_partial_manifests()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_partial_manifests(self) -> None:
        parents = self.round / "parents.cubes"
        children = self.round / "children.cubes"
        coverage_path = self.round / "coverage.json"
        coverage = {
            "verified": True,
            "parents_sha256": sha256(parents),
            "children_sha256": sha256(children),
            "parent_count": 1,
            "child_count": 2,
            "records": [{"parent": 0, "child_count": 2, "covered": True}],
        }
        write_json(coverage_path, coverage)
        parsed_parent = parse_parent_cnf(self.parent)
        certificate_manifest = {
            "base_cnf": str(self.parent),
            "base_cnf_sha256": sha256(self.parent),
            "cubes": str(children),
            "cubes_sha256": sha256(children),
            "complete_partition": True,
            "total_cube_count": 2,
            "cube_depth": 1,
            "shards": 1,
            "shard_index": 0,
            "xz_level": 1,
            "logs_retained": False,
            "solver_kind": "cadical",
            "solver_profile": "default",
            "proof_mode": "rup",
            "solver_seconds_limit": 1,
            "checker_seconds_limit": 1,
            "coverage": str(coverage_path),
            "coverage_sha256": sha256(coverage_path),
            "selected_cube_indices": [0, 1],
            "verified_cube_count": 1,
            "failed_cubes": [{"cube_index": 1, "error": "status 124"}],
            "records": [
                {
                    "cube_index": 0,
                    "literals": [-1],
                    "leaf_cnf_sha256": leaf_cnf_sha256(parsed_parent, (-1,)),
                    "solver_exit": 20,
                    "solver_seconds": 0.1,
                    "raw_proof_bytes": 100,
                    "extraction_exit": 0,
                    "extraction_seconds": 0.1,
                    "core_bytes": 50,
                    "verification_exit": 0,
                    "verification_seconds": 0.1,
                    "compressed_core": self.proof.name,
                    "compressed_core_sha256": sha256(self.proof),
                    "compressed_core_bytes": self.proof.stat().st_size,
                    "proof_mode": "rup",
                    "rat_lemmas": 0,
                    "rup_only": True,
                }
            ],
        }
        certificate_path = self.certificate / "certificate_manifest.json"
        write_json(certificate_path, certificate_manifest)
        (self.round / "failed.cubes").write_text(
            "a 1 0\n", encoding="ascii", newline="\n"
        )
        round_record = {
            "round": 1,
            "mode": "split",
            "split_depth": 1,
            "split_strategy": "cadical-lookahead",
            "parents": "parents.cubes",
            "parents_sha256": sha256(parents),
            "children": "children.cubes",
            "children_sha256": sha256(children),
            "coverage": "coverage.json",
            "coverage_sha256": sha256(coverage_path),
            "certificate_manifest": "certificate/certificate_manifest.json",
            "certificate_manifest_sha256": sha256(certificate_path),
            "parent_count": 1,
            "child_count": 2,
            "verified_count": 1,
            "failed_count": 1,
            "failed_indices": [1],
            "seconds_per_command": 1,
            "solver_kind": "cadical",
            "proof_mode": "rup",
            "checker_seconds_per_command": 1,
        }
        adaptive = {
            "verified": False,
            "reason": "round limit reached",
            "parent_cnf": self.parent.name,
            "parent_cnf_sha256": sha256(self.parent),
            "initial_depth": 1,
            "additional_depth": 1,
            "initial_seconds_per_command": 1,
            "maximum_seconds_per_command": 1,
            "constant_timeout_rounds": 1,
            "retries_before_split": 0,
            "fixed_variable_upper_bound": 0,
            "jobs": 1,
            "xz_level": 1,
            "solver_kind": "cadical",
            "proof_mode": "rup",
            "proof_modes": ["rup"],
            "checker_seconds_per_command": 0,
            "round_count": 1,
            "terminal_refutations": 1,
            "rounds": [round_record],
        }
        write_json(self.tree / "adaptive_manifest.json", adaptive)

    def test_valid_partial_tree_passes(self) -> None:
        report = audit_tree(self.tree, self.parent, require_partial=True)
        self.assertTrue(report["verified"])
        self.assertEqual(report["round_count"], 1)
        self.assertEqual(report["unresolved_cubes"], 1)

    def test_legacy_rup_schema_is_strictly_inferred(self) -> None:
        certificate_path = self.certificate / "certificate_manifest.json"
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate.pop("solver_kind")
        certificate.pop("proof_mode")
        certificate["records"][0].pop("proof_mode")
        write_json(certificate_path, certificate)

        adaptive_path = self.tree / "adaptive_manifest.json"
        adaptive = json.loads(adaptive_path.read_text(encoding="utf-8"))
        adaptive.pop("proof_mode")
        adaptive.pop("proof_modes")
        adaptive["rounds"][0].pop("solver_kind")
        adaptive["rounds"][0].pop("proof_mode")
        adaptive["rounds"][0]["certificate_manifest_sha256"] = sha256(
            certificate_path
        )
        write_json(adaptive_path, adaptive)

        report = audit_tree(
            self.tree,
            self.parent,
            require_partial=True,
            require_rup=True,
        )
        self.assertEqual(report["schema"], "legacy-rup")
        self.assertEqual(report["proof_mode"], "rup")

    def test_valid_complete_tree_passes(self) -> None:
        second_proof = self.certificate / "cube_00001.core.rup.xz"
        second_proof.write_bytes(b"second-synthetic-compressed-proof")
        certificate_path = self.certificate / "certificate_manifest.json"
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        second_record = dict(certificate["records"][0])
        second_record.update(
            {
                "cube_index": 1,
                "literals": [1],
                "leaf_cnf_sha256": leaf_cnf_sha256(
                    parse_parent_cnf(self.parent), (1,)
                ),
                "compressed_core": second_proof.name,
                "compressed_core_sha256": sha256(second_proof),
                "compressed_core_bytes": second_proof.stat().st_size,
            }
        )
        certificate["records"].append(second_record)
        certificate["verified_cube_count"] = 2
        certificate["failed_cubes"] = []
        write_json(certificate_path, certificate)
        (self.round / "failed.cubes").unlink()

        adaptive_path = self.tree / "adaptive_manifest.json"
        adaptive = json.loads(adaptive_path.read_text(encoding="utf-8"))
        adaptive["verified"] = True
        adaptive.pop("reason")
        adaptive["terminal_refutations"] = 2
        adaptive["rounds"][0].update(
            {
                "certificate_manifest_sha256": sha256(certificate_path),
                "verified_count": 2,
                "failed_count": 0,
                "failed_indices": [],
            }
        )
        write_json(adaptive_path, adaptive)

        report = audit_tree(self.tree, self.parent, require_complete=True)
        self.assertEqual(report["tree_state"], "complete")
        self.assertEqual(report["terminal_refutations"], 2)
        self.assertEqual(report["unresolved_cubes"], 0)

    def test_missing_frontier_is_rejected(self) -> None:
        (self.round / "failed.cubes").unlink()
        with self.assertRaisesRegex(ValueError, "failed.cubes"):
            audit_tree(self.tree, self.parent, require_partial=True)

    def test_truncated_proof_is_rejected(self) -> None:
        self.proof.write_bytes(b"truncated")
        with self.assertRaisesRegex(ValueError, "proof size mismatch"):
            audit_tree(self.tree, self.parent, require_partial=True)

    def test_uncommitted_round_is_rejected_or_pruned(self) -> None:
        uncommitted = self.tree / "round_02"
        uncommitted.mkdir()
        with self.assertRaisesRegex(ValueError, "round directories"):
            audit_tree(self.tree, self.parent, require_partial=True)
        report = audit_tree(
            self.tree,
            self.parent,
            require_partial=True,
            prune_uncommitted=True,
        )
        self.assertEqual(report["pruned_uncommitted_rounds"], ["round_02"])
        self.assertFalse(uncommitted.exists())


if __name__ == "__main__":
    unittest.main()
