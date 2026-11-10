"""Render machine-readable dependency scan results as a human-readable Markdown report."""

import html
import re
from collections import Counter


def cell(value):
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", "<br>")


def findings_table(sarif):
    rows = []
    levels = Counter()
    for run in sarif.get("runs", []):
        for result in run.get("results", []):
            level = result.get("level", "warning")
            levels[level] += 1
            message = result.get("message", {})
            text = (
                message.get("text") or message.get("markdown") or "No message provided"
            )
            rows.append(
                "| "
                + " | ".join(
                    cell(value)
                    for value in (result.get("ruleId", "Unknown"), level, text)
                )
                + " |"
            )
    header = ["| Rule / vulnerability | SARIF level | Details |", "| --- | --- | --- |"]
    return levels, header + rows


def inventory_table(lock, manifest):
    requirements = list(manifest["project"].get("dependencies", []))
    for dependencies in manifest.get("dependency-groups", {}).values():
        requirements.extend(dependencies)
    direct = {re.split(r"[ (]", item, maxsplit=1)[0].lower() for item in requirements}
    rows = [
        "| Package | Locked version | Poetry groups | Dependency |",
        "| --- | --- | --- | --- |",
    ]
    packages = sorted(lock["package"], key=lambda item: (item["name"], item["version"]))
    for package in packages:
        kind = "Direct" if package["name"].lower() in direct else "Transitive"
        groups = ", ".join(package.get("groups", [])) or "Not specified"
        rows.append(
            "| "
            + " | ".join(
                cell(value)
                for value in (package["name"], package["version"], groups, kind)
            )
            + " |"
        )
    return rows


def render_summary(lock, manifest, sarif, metadata):
    levels, findings = findings_table(sarif)
    lines = [
        "# Dependency security report",
        "",
        f"- Generated (UTC): {cell(metadata['generated_at_utc'])}",
        f"- Scope: {cell(metadata['scope'])}",
        f"- Locked packages: **{metadata['packages']}**",
        f"- SARIF findings: **{metadata['sarif_findings']}**",
        f"- Scanner: `{metadata['scanner_image']}`",
        f"- Lockfile SHA-256: `{metadata['lock_sha256']}`",
        "",
        "## Vulnerability findings",
        "",
    ]
    if levels:
        lines.append(
            "SARIF levels: "
            + ", ".join(
                f"{cell(level)}: {count}" for level, count in sorted(levels.items())
            )
            + "."
        )
        lines.extend(["", *findings])
    else:
        lines.append("No vulnerability findings were reported by this scan.")
    lines.extend(
        [
            "",
            "## Dependency inventory",
            "",
            *inventory_table(lock, manifest),
            "",
            "## Source artifacts and scope",
            "",
            "- [CycloneDX SBOM](sbom.cdx.json): complete locked dependency inventory.",
            "- [SARIF findings](dependencies.sarif): machine-readable vulnerability results.",
            "- [Scan metadata](scan-metadata.json): scan identity and dependency fingerprint.",
            "",
            "This report covers all locked Python groups, including optional notebook and quality dependencies. "
            "It does not inventory container OS packages or browser binaries. Direct/transitive labels are "
            "relative to declarations across all project groups. SARIF levels are scanner result levels, "
            "not necessarily CVSS severity categories. Findings depend on advisory data available at scan time.",
            "",
        ]
    )
    return "\n".join(lines)
