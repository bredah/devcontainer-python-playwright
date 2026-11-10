"""Combine independent suite artifacts into a local HTML dashboard and CI summary."""

import argparse
import html
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

COUNTS = ("tests", "failures", "errors", "skipped")
SUITES = ("api", "web", "e2e")


def load_suite(directory, suite, output):
    result = {
        "suite": suite,
        "status": "missing",
        "report": "",
        **dict.fromkeys(COUNTS, 0),
    }
    status_path = directory / "status.json"
    xml_path = directory / f"{suite}.xml"
    try:
        status = json.loads(status_path.read_text())
        if not isinstance(status, dict):
            raise ValueError("Invalid suite status metadata")
        root = ET.parse(xml_path).getroot()
        nodes = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        if not nodes:
            raise ValueError("JUnit report has no test suites")
        for key in COUNTS:
            result[key] = sum(int(node.get(key, "0")) for node in nodes)
        failed = (
            status.get("TEST_OUTCOME") != "success"
            or status.get("BUILD_OUTCOME") != "success"
        )
        result["status"] = (
            "failed" if failed or result["failures"] or result["errors"] else "passed"
        )
        if not result["tests"]:
            result["status"] = "empty"
        source = directory / f"{suite}.html"
        if source.is_file():
            shutil.copyfile(source, output / source.name)
            result["report"] = status.get("REPORT_URL") or source.name
        else:
            result["status"] = "missing"
        shutil.copyfile(xml_path, output / xml_path.name)
    except (OSError, ValueError, ET.ParseError) as error:
        result["status"] = "missing"
        result["detail"] = str(error)
    return result


def render(results, totals):
    heading = [
        "Suite",
        "Status",
        "Tests",
        "Passed",
        "Failures",
        "Errors",
        "Skipped",
        "Report",
    ]
    rows = []
    markdown = [
        "## Consolidated test results",
        "",
        "| " + " | ".join(heading) + " |",
        "|" + " --- |" * len(heading),
    ]
    for result in results:
        passed = (
            result["tests"] - result["failures"] - result["errors"] - result["skipped"]
        )
        values = [
            result["suite"],
            result["status"],
            result["tests"],
            passed,
            result["failures"],
            result["errors"],
            result["skipped"],
        ]
        link = result["report"]
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in values)
        report = (
            f'<a href="{html.escape(link, quote=True)}">HTML report</a>'
            if link
            else "Unavailable"
        )
        rows.append(f"<tr>{cells}<td>{report}</td></tr>")
        markdown.append(
            "| "
            + " | ".join(map(str, values))
            + f" | {'[HTML report](' + link + ')' if link else 'Unavailable'} |"
        )
    summary = f"Total: {totals['tests']} tests, {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped."
    markup = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Test results</title>'
    markup += "<style>body{font:16px system-ui;margin:3rem;color:#172033}table{border-collapse:collapse}th,td{padding:.7rem;border:1px solid #ccd3dd;text-align:left}th{background:#edf1f8}</style>"
    markup += "<h1>Consolidated test results</h1><p>" + html.escape(summary) + "</p>"
    markup += (
        "<table><tr>"
        + "".join(f"<th>{name}</th>" for name in heading)
        + "</tr>"
        + "".join(rows)
        + "</table>"
    )
    markup += "<p>Missing, empty and failed suites make the overall run fail. Download the combined bundle to keep all individual reports.</p></html>"
    return markup, "\n".join(markdown) + "\n\n" + summary + "\n"


def aggregate(source, output, suites):
    output.mkdir(parents=True, exist_ok=True)
    results = [
        load_suite(source / f"{suite}-results", suite, output) for suite in suites
    ]
    totals = {key: sum(result[key] for result in results) for key in COUNTS}
    markup, markdown = render(results, totals)
    (output / "index.html").write_text(markup)
    (output / "summary.md").write_text(markdown)
    (output / "summary.json").write_text(
        json.dumps({"suites": results, "totals": totals}, indent=2)
    )
    return int(any(result["status"] != "passed" for result in results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suites", default=",".join(SUITES))
    args = parser.parse_args()
    suites = args.suites.split(",")
    if not suites or any(suite not in SUITES for suite in suites):
        parser.error("--suites must contain api, web and/or e2e, comma-separated")
    return aggregate(args.input, args.output, suites)


if __name__ == "__main__":
    raise SystemExit(main())
