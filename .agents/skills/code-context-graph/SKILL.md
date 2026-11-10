---
name: code-context-graph
description: Search code and documentation locally by keywords, signatures and docstrings, and find Python symbols and dependency candidates through an incremental SQLite index. Use when locating reusable code or identifying relevant source without loading entire files.
---

# Persistent Python code context

In this repository, AGENTS.md requires this skill for every code-content discovery
or search task, including when the user does not name it. Query the index before
opening source implementations or using other content-search tools. Read the
returned source locations as needed before editing. If the tool fails, a narrowed
query has no relevant results, or the target is outside the allowlist, explain the
reason and fall back to a bounded read or targeted search. Do not index secrets.

Use the bundled `scripts/code_graph.py` with Python 3.11 or newer. No third-party
packages, Playwright, Poetry, or specific agent runtime are required.
Resolve the script relative to this skill directory, not an assumed installation path.
Run from the target project root or pass `--root /absolute/project/path` explicitly.

```bash
python3 <skill-directory>/scripts/code_graph.py search "Jupyter authentication token" --limit 5 --root /project
python3 <skill-directory>/scripts/code_graph.py find ContactForm --root /project
python3 <skill-directory>/scripts/code_graph.py refs app.contact --root /project
python3 <skill-directory>/scripts/code_graph.py refresh --root /project
```

For this repository, the skill directory is `.agents/skills/code-context-graph`.
The index lives under the target project's `.agents/skills/code-context-graph/graph.sqlite`.
Keep that generated cache outside version control. Copying this skill to another
project does not require copying its database.

## Retrieve only what is needed

- Query `search "words describing the task" --limit 5` when the relevant symbol is
  unknown. Results contain ranked, bounded excerpts with paths and line ranges.
  Use `--path src/` or `--path docs/` to narrow retrieval. English keywords work
  best for this English codebase; search is lexical, not semantic or multilingual.
- Query `find <symbol>` before opening multiple implementations. It returns names,
  signatures, source docstrings, locations and constructor-defined public handles.
- Query `refs <name-or-expression>` for candidate callers, imports and fixtures.
  Narrow the term before increasing the default 12-result limit.
- Use metadata to reuse existing interfaces. Before editing, read the current
  relevant source lines. Read additional code when metadata lacks behavioral detail.
- Do not dump the database, all sources or all references into model context.
  This skill supplies an external index, not permanent model memory.

Each query hashes the supported code/documentation files, reparses only changes and
removes deleted entries. Updating the extractor invalidates old metadata. Syntax
errors abort the query without returning stale results. On failure, inspect only
relevant source directly and report the index issue.

References are syntactic candidates, not a resolved runtime call graph. Dynamic
attributes, aliases, reflection and fixture overrides may need inspection.
AST symbols are extracted from Python in `src`, `tests` and `scripts`. Text search
also covers README/AGENTS, `docs/**/*.md`, `notes/README.md`, project build/test
configuration, devcontainer/VS Code/workflow files and local SKILL.md files.
The allowlist excludes .env files, notebooks and their outputs, lockfiles, caches,
and arbitrary files outside these locations. Other layouts require adapting it.
Search uses local token frequencies and case/CamelCase normalization; there are
no embeddings, external API calls, file uploads or additional dependencies.
Docstrings are copied from code, not inferred summaries.

For query examples, read [references/queries.md](references/queries.md) as needed.
Validate index behavior with `python3 <skill-directory>/scripts/test_code_graph.py`.
