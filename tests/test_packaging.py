"""Portable export and byte-integrity regressions; never touch bundled originals."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from impact_predictor import paths


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(paths.INVENTORY, self.root / "data/inventory")
        shutil.copytree(paths.PROJECT / "models", self.root / "models")
        shutil.copyfile(paths.PROJECT / "approved_contract.json",
                        self.root / "approved_contract.json")
        self.patches = [
            patch.object(paths, "PROJECT", self.root),
            patch.object(paths, "INVENTORY", self.root / "data/inventory"),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_bundled_package_resolves_without_private_sibling_inputs(self):
        directory, manifest = paths.load_run("run-001")
        self.assertEqual(directory, self.root / "models/run-001")
        self.assertEqual(paths.digest(directory / "model.joblib"),
                         manifest["artifacts"]["model.joblib"])
        self.assertFalse((self.root / "demo-neighborhood").exists())

    def test_inventory_and_model_tampering_fail_before_deserialization(self):
        for relative in (
            "data/inventory/topology.json", "models/run-001/model.joblib",
            "models/run-001/training_manifest.json",
        ):
            target = self.root / relative
            original = target.read_bytes()
            try:
                target.write_bytes(original + b"\n")
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    paths.load_run("run-001")
            finally:
                target.write_bytes(original)

    def test_missing_ambiguous_and_invalid_names_are_rejected(self):
        for name in ("missing", "../run-001", "", "/run-001"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                paths.load_run(name)
        (self.root / "runs/run-001").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            paths.load_run("run-001")

    def test_generated_run_uses_the_bundled_alias_manifest(self):
        directory = self.root / "runs/run-test"
        directory.mkdir(parents=True)
        manifest = {
            "neighborhood_manifest_sha256":
                paths.digest(self.root / "data/inventory/manifest.json"),
        }
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(paths.load_run("run-test"), (directory, manifest))
        manifest["neighborhood_manifest_sha256"] = "0" * 64
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            paths.load_run("run-test")

    def test_artifact_names_cannot_escape_their_directory(self):
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            paths.verify_files(self.root / "models/run-001",
                               {"../../approved_contract.json": "0" * 64})


if __name__ == "__main__":
    unittest.main()
