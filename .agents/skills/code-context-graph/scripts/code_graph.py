"""Persistent, incremental Python symbol index. Uses only the standard library."""

import argparse
import ast
import hashlib
import json
import sqlite3
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
    """)
    known = dict(db.execute("SELECT path, hash FROM files"))
    extractor_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    previous = db.execute(
        "SELECT value FROM metadata WHERE key = 'extractor_hash'"
    ).fetchone()
    force = previous is None or previous[0] != extractor_hash
    current, changed = set(), []
    # Parse before modifying the database: syntax errors never produce a partial index.
    try:
        for directory in ("src", "tests"):
            for file in sorted((root / directory).rglob("*.py")):
                if "__pycache__" in file.parts:
                    continue
                path = file.relative_to(root).as_posix()
                current.add(path)
                raw = file.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                if force or digest != known.get(path):
                    symbols, edges = extract(path, raw.decode("utf-8"))
                    changed.append((path, digest, symbols, edges))
        removed = set(known) - current
        with db:
            db.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('extractor_hash', ?)",
                (extractor_hash,),
            )
            for path in removed | {item[0] for item in changed}:
                for table in ("files", "symbols", "edges"):
                    db.execute(f"DELETE FROM {table} WHERE path = ?", (path,))
            for path, digest, symbols, edges in changed:
                db.execute("INSERT INTO files VALUES (?, ?)", (path, digest))
                db.executemany(
                    "INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?, ?, ?)", symbols
                )
                db.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", edges)
        return db, {
            "files": len(current),
            "reindexed": len(changed),
            "removed": len(removed),
        }
    except BaseException:
        db.close()
        raise


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
    parser.add_argument("command", choices=["refresh", "find", "refs"])
    parser.add_argument("term", nargs="?")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Project root (default: current directory)",
    )
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if args.command != "refresh" and not args.term:
        parser.error("find/refs require a search term")
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    try:
        db, stats = refresh(args.root.resolve())
        try:
            output = {"index": stats}
            if args.command != "refresh":
                output["results"] = query(db, args.command, args.term, args.limit)
                output["note"] = (
                    "Static AST index; references are candidates, not resolved runtime calls. Results limited; narrow the term if needed."
                )
            print(json.dumps(output, ensure_ascii=False, indent=2))
        finally:
            db.close()
    except (SyntaxError, UnicodeError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"Index unavailable; read relevant source directly: {error}\n")


if __name__ == "__main__":
    main()
