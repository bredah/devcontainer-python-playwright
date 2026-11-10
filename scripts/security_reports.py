"""Generate a locked dependency SBOM and vulnerability SARIF using pinned Trivy."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

TRIVY_IMAGE = "aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb"


def normalized(name):
    return name.lower().replace("_", "-").replace(".", "-")


def validate_inventory(lock, sbom):
    expected = {(normalized(p["name"]), p["version"]) for p in lock["package"]}
    actual = {
        (normalized(p["name"]), p.get("version")) for p in sbom.get("components", [])
    }
    missing = expected - actual
    if missing:
        raise ValueError(f"SBOM is missing locked packages: {sorted(missing)}")
    return len(expected)


def validate_pins(manifest, lock):
    requirements = list(manifest["project"].get("dependencies", []))
    for dependencies in manifest.get("dependency-groups", {}).values():
        requirements.extend(dependencies)
    locked = {(normalized(p["name"]), p["version"]) for p in lock["package"]}
    for requirement in requirements:
        match = re.fullmatch(
            r"([A-Za-z0-9_.-]+) \(==([A-Za-z0-9.!+_-]+)\)", requirement
        )
        if not match:
            raise ValueError(f"Dependency must use an exact version: {requirement}")
        if (normalized(match[1]), match[2]) not in locked:
            raise ValueError(
                f"Pinned dependency does not match the lockfile: {requirement}"
            )


def generate(root, output, docker):
    output.mkdir(parents=True, exist_ok=True)
    # A failed new scan must not leave a previous successful completion record.
    for name in ("sbom.cdx.json", "dependencies.sarif", "scan-metadata.json"):
        (output / name).unlink(missing_ok=True)
    cache = root / ".cache" / "trivy"
    cache.mkdir(parents=True, exist_ok=True)
    lock_path = root / "poetry.lock"
    lock = tomllib.loads(lock_path.read_text())
    validate_pins(tomllib.loads((root / "pyproject.toml").read_text()), lock)
    with tempfile.TemporaryDirectory(prefix="dependency-input-") as directory:
        inputs = Path(directory)
        for name in ("pyproject.toml", "poetry.lock"):
            shutil.copyfile(root / name, inputs / name)
        command = [
            docker,
            "run",
            "--rm",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,size=1g",
            "--mount",
            f"type=bind,source={inputs},target=/input,readonly",
            "--mount",
            f"type=bind,source={output},target=/output",
            "--mount",
            f"type=bind,source={cache},target=/cache",
            TRIVY_IMAGE,
        ]
        common = ["--cache-dir", "/cache", "--disable-telemetry", "--timeout", "10m"]
        subprocess.run(
            command
            + [
                "fs",
                *common,
                "--include-dev-deps",
                "--format",
                "cyclonedx",
                "--output",
                "/output/sbom.cdx.json",
                "/input",
            ],
            check=True,
        )
        sbom = json.loads((output / "sbom.cdx.json").read_text())
        count = validate_inventory(lock, sbom)
        subprocess.run(
            command
            + [
                "sbom",
                *common,
                "--format",
                "sarif",
                "--exit-code",
                "0",
                "--output",
                "/output/dependencies.sarif",
                "/output/sbom.cdx.json",
            ],
            check=True,
        )
    sarif = json.loads((output / "dependencies.sarif").read_text())
    if sarif.get("version") != "2.1.0" or not sarif.get("runs"):
        raise ValueError("Scanner did not produce a valid SARIF 2.1.0 run")
    findings = sum(len(run.get("results", [])) for run in sarif["runs"])
    metadata = {
        "scanner_image": TRIVY_IMAGE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "all locked Poetry groups",
        "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "packages": count,
        "sarif_findings": findings,
        "note": "SBOM is inventory; SARIF contains vulnerability findings, not all packages.",
    }
    (output / "scan-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(
        f"Generated SBOM ({count} packages) and SARIF ({findings} findings) in {output}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("reports/security"))
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    generate(args.root.resolve(), args.output.resolve(), args.docker)


if __name__ == "__main__":
    main()
