"""Portable paths and explicit provenance checks for the alias-only export."""

import hashlib
import json
from pathlib import Path
import re


PROJECT = Path(__file__).resolve().parents[1]
INVENTORY = PROJECT / "data/inventory"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_files(directory, hashes):
    for name, checksum in hashes.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or digest(path) != checksum:
            raise ValueError(f"Artifact checksum mismatch: {name}")


def verify_inventory():
    manifest = read_json(INVENTORY / "manifest.json")
    if manifest["format"] != "alias-only-inventory-v1":
        raise ValueError("Unsupported inventory export")
    verify_files(INVENTORY, manifest["files"])
    return manifest


def load_run(run_name):
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_name) is None:
        raise ValueError("Invalid local model run name")
    candidates = [PROJECT / root / run_name for root in ("models", "runs")]
    existing = [candidate for candidate in candidates if candidate.is_dir()]
    if len(existing) != 1:
        raise ValueError("Model run must exist in exactly one of models/ or runs/")
    directory = existing[0]
    inventory = verify_inventory()
    package_path = directory / "package_manifest.json"
    if package_path.exists():
        package = read_json(package_path)
        if package["format"] != "portable-model-package-v1" or package["run_id"] != run_name:
            raise ValueError("Unsupported model package")
        verify_files(directory, {
            "training_manifest.json": package["training_manifest_sha256"],
            "training_inventory_manifest.json": package["training_inventory_manifest_sha256"],
        })
        manifest = read_json(directory / "training_manifest.json")
        original_inventory = read_json(directory / "training_inventory_manifest.json")
        if (digest(INVENTORY / "manifest.json") != package["inventory_manifest_sha256"]
                or digest(PROJECT / "approved_contract.json") != package["contract_sha256"]
                or package["training_inventory_manifest_sha256"]
                != manifest["neighborhood_manifest_sha256"]):
            raise ValueError("Export provenance chain mismatch")
        original_inputs = {item["path"]: item["sha256"]
                           for item in original_inventory["artifacts"]}
        if any(original_inputs.get(name) != checksum
               for name, checksum in inventory["files"].items()):
            raise ValueError("Exported inventory differs from original training inputs")
        if any(manifest["artifacts"].get(name) != checksum
               for name, checksum in package["files"].items()):
            raise ValueError("Exported model artifacts differ from original training run")
        verify_files(directory, package["files"])
    else:
        manifest = read_json(directory / "manifest.json")
        if digest(INVENTORY / "manifest.json") != manifest["neighborhood_manifest_sha256"]:
            raise ValueError("Training inventory mismatch")
    return directory, manifest
