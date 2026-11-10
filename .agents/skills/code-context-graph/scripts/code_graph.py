"""Persistent local code/document search and Python symbol index; standard library only."""

import argparse
import ast
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()


def module_name(path):
    parts = list(Path(path).with_suffix("").parts)
    if parts[0] == "src":
        parts.pop(0)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def symbol_details(node):
    if isinstance(node, ast.ClassDef):
        signature = node.name
        if node.bases:
            signature += "(" + ", ".join(ast.unparse(b) for b in node.bases) + ")"
        return "class", signature
    fixture = any(
        ast.unparse(decorator).split("(")[0].endswith("fixture")
        for decorator in node.decorator_list
    )
    signature = f"{node.name}({ast.unparse(node.args)})"
    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"
    return "fixture" if fixture else "function", signature


def constructor_attributes(node):
    if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
        return {}
    attributes = {}
    for child in ast.walk(node):
        if not isinstance(child, ast.Assign):
            continue
        for target in child.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                attributes[target.attr] = ast.unparse(child.value)[:240]
    return attributes


def function_edges(node, key, kind):
    edges = set()
    if kind == "class":
        return edges
    if kind == "fixture" or node.name.startswith("test_"):
        edges.update((key, arg.arg, "fixture_candidate") for arg in node.args.args)
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            edges.add((key, ast.unparse(child.func), "call_expression"))
        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            edges.add((key, child.id, "name_reference"))
    return edges


def import_edges(tree, module):
    edges = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                edges.add(
                    (
                        module,
                        f"{'.' * node.level}{node.module or ''}.{alias.name}",
                        "import",
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                edges.add((module, alias.name, "import"))
    return edges


def extract(path, source):
    tree = ast.parse(source, filename=path)
    symbols = []
    module = module_name(path)
    edges = import_edges(tree, module)

    def visit(body, scope):
        for node in body:
            if not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            key = f"{scope}.{node.name}"
            kind, signature = symbol_details(node)
            attributes = constructor_attributes(node)
            symbols.append(
                (
                    key,
                    path,
                    node.lineno,
                    node.end_lineno,
                    kind,
                    signature,
                    (ast.get_docstring(node) or "")[:600],
                    json.dumps(attributes),
                )
            )
            # Class references are represented by their methods to avoid duplicate results.
            edges.update(function_edges(node, key, kind))
            visit(node.body, key)

    visit(tree.body, module)
    return symbols, [(path, *edge) for edge in sorted(edges)]


def candidate_files(root):
    patterns = (
        "src/**/*.py",
        "tests/**/*.py",
        "scripts/**/*.py",
        "docs/**/*.md",
        "README.md",
        "AGENTS.md",
        "notes/README.md",
        "pyproject.toml",
        "Makefile",
        "Dockerfile",
        ".pre-commit-config.yaml",
        ".flake8",
        ".devcontainer/Dockerfile",
        ".devcontainer/*.json",
        ".devcontainer/*.yaml",
        ".devcontainer/*.yml",
        ".vscode/*.json",
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".agents/skills/*/SKILL.md",
    )
    files = {file for pattern in patterns for file in root.glob(pattern)}
    return sorted(
        file
        for file in files
        if file.is_file()
        and not file.is_symlink()
        and "__pycache__" not in file.parts
        and file.stat().st_size <= 1_000_000
    )


def text_chunks(path, source):
    lines = source.splitlines()
    return [
        (
            path,
            start + 1,
            min(start + 24, len(lines)),
            "\n".join(lines[start : start + 24]),
        )
        for start in range(0, len(lines), 24)
    ]


def scan_changes(root, known, force):
    current, changed = set(), []
    for file in candidate_files(root):
        path = file.relative_to(root).as_posix()
        current.add(path)
        raw = file.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if not force and digest == known.get(path):
            continue
        source = raw.decode("utf-8")
        symbols, edges = extract(path, source) if file.suffix == ".py" else ([], [])
        changed.append((path, digest, symbols, edges, text_chunks(path, source)))
    return current, changed


def persist_changes(db, changed, removed, extractor_hash):
    with db:
        db.execute(
            "INSERT OR REPLACE INTO metadata VALUES ('extractor_hash', ?)",
            (extractor_hash,),
        )
        for path in removed | {item[0] for item in changed}:
            for table in ("files", "symbols", "edges", "chunks"):
                db.execute(f"DELETE FROM {table} WHERE path = ?", (path,))
        for path, digest, symbols, edges, chunks in changed:
            db.execute("INSERT INTO files VALUES (?, ?)", (path, digest))
            db.executemany(
                "INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?, ?, ?)", symbols
            )
            db.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", edges)
            db.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?)", chunks)


def refresh(root):
    cache = root / ".agents" / "skills" / "code-context-graph"
    cache.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(cache / "graph.sqlite")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, hash TEXT);
        CREATE TABLE IF NOT EXISTS symbols(
            name TEXT PRIMARY KEY, path TEXT, line INTEGER, end_line INTEGER,
            kind TEXT, signature TEXT, summary TEXT, attributes TEXT);
        CREATE TABLE IF NOT EXISTS edges(path TEXT, source TEXT, target TEXT, kind TEXT);
        CREATE TABLE IF NOT EXISTS chunks(path TEXT, line INTEGER, end_line INTEGER,
            content TEXT);
    """)
    try:
        known = dict(db.execute("SELECT path, hash FROM files"))
        extractor_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        previous = db.execute(
            "SELECT value FROM metadata WHERE key = 'extractor_hash'"
        ).fetchone()
        force = previous is None or previous[0] != extractor_hash
        # Parse all changes first: errors never commit a partial or stale index.
        current, changed = scan_changes(root, known, force)
        removed = set(known) - current
        persist_changes(db, changed, removed, extractor_hash)
        return db, {
            "files": len(current),
            "reindexed": len(changed),
            "removed": len(removed),
        }
    except BaseException:
        db.close()
        raise


STOP_WORDS = set(
    "a an and are as at be by do does for from how i in is it of on or the this to we what when where which with".split()
)


def words(text):
    # Split both Python identifiers and prose, including CamelCase and snake_case.
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return [
        word
        for word in re.findall(r"[^\W_]+", text.casefold())
        if word not in STOP_WORDS and len(word) > 1
    ]


def excerpt(content, query_words, first_line):
    lines = content.splitlines()
    match = next(
        (i for i, line in enumerate(lines) if set(words(line)) & query_words), 0
    )
    start = max(0, match - 1)
    selected = lines[start : start + 6]
    return (
        first_line + start,
        first_line + start + len(selected) - 1,
        "\n".join(selected)[:600],
    )


def search(db, term, limit, path_prefix=""):
    query_words = set(words(term))
    if not query_words:
        return []
    rows = db.execute(
        "SELECT * FROM chunks WHERE substr(path, 1, ?) = ? ORDER BY path, line",
        (len(path_prefix), path_prefix),
    ).fetchall()
    documents = [Counter(words(row["content"]) + words(row["path"])) for row in rows]
    frequencies = Counter(word for document in documents for word in document.keys())
    ranked = []
    for row, document in zip(rows, documents):
        matched = query_words & document.keys()
        if not matched:
            continue
        score = (
            sum(
                math.log1p(len(rows) / frequencies[word])
                * (1 + math.log(document[word]))
                for word in matched
            )
            * len(matched)
            / len(query_words)
        )
        line, end_line, snippet = excerpt(row["content"], query_words, row["line"])
        ranked.append(
            {
                "path": row["path"],
                "line": line,
                "end_line": end_line,
                "score": round(score, 4),
                "matched_terms": sorted(matched),
                "snippet": snippet,
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["path"], row["line"]))
    return ranked[:limit]


def query(db, command, term, limit):
    if command == "find":
        rows = db.execute(
            "SELECT * FROM symbols WHERE instr(lower(name), lower(?)) > 0 ORDER BY name LIMIT ?",
            (term, limit),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["attributes"] = json.loads(item["attributes"])
            result.append(item)
        return result
    # Expressions are intentionally not presented as fully resolved runtime dependencies.
    rows = db.execute(
        """SELECT DISTINCT e.source, e.target, e.kind, e.path, s.line
        FROM edges e LEFT JOIN symbols s ON s.name = e.source
        WHERE instr(lower(e.target), lower(?)) > 0
        ORDER BY e.source, e.target LIMIT ?""",
        (term, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["refresh", "find", "refs", "search"])
    parser.add_argument("term", nargs="?")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Project root (default: current directory)",
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--path", default="", help="Restrict search to a relative path prefix"
    )
    args = parser.parse_args()
    if args.command != "refresh" and not args.term:
        parser.error("find/refs/search require a search term")
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    try:
        db, stats = refresh(args.root.resolve())
        try:
            output = {"index": stats}
            if args.command != "refresh":
                output["results"] = (
                    search(db, args.term, args.limit, args.path)
                    if args.command == "search"
                    else query(db, args.command, args.term, args.limit)
                )
                output["note"] = (
                    "Local lexical search and static AST index; no embeddings or runtime call resolution. Results limited; narrow the term if needed."
                )
            print(json.dumps(output, ensure_ascii=False, indent=2))
        finally:
            db.close()
    except (SyntaxError, UnicodeError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Index unavailable; read relevant source directly: {error}\n")


if __name__ == "__main__":
    main()
