# Persistent project context

Run from the repository root, on the host or in the devcontainer. No dependencies:

```bash
python3 .agents/skills/code-context-graph/scripts/code_graph.py search "Jupyter authentication token" --limit 5
python3 .agents/skills/code-context-graph/scripts/code_graph.py search "submit contact form" --path src/ --limit 3
python3 .agents/skills/code-context-graph/scripts/code_graph.py find ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py find DemoApp.__init__
python3 .agents/skills/code-context-graph/scripts/code_graph.py find TasksAPI.create
python3 .agents/skills/code-context-graph/scripts/code_graph.py find conftest.app
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs app.contact
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs tasks_api --limit 8
```

`find` returns matching symbol names, signatures, docstrings, paths and line spans.
Constructor entries include public attributes such as `contact = ContactForm(page)`
and locators. `refs` returns candidate callers, name references, imports and fixture
parameters. For `app.contact.fill`, query `refs app.contact` rather than expecting
`refs ContactForm` to resolve dynamic fixture attributes automatically.

Use `find ContactForm` and `find DemoApp.__init__` to understand a component's public
surface, then `find conftest.app`/`refs DemoApp` to discover fixture construction.
Reuse this metadata when writing tests. Read source only for missing semantics,
errors, or edits; summaries and expressions are not complete behavior contracts.
Docstrings come directly from source; this tool does not invent semantic summaries.

Queries read file bytes to check SHA-256 hashes but reparse only changed files.
That I/O does not put full source into the model's context. Deleted files are removed.
The SQLite cache at `.agents/skills/code-context-graph/graph.sqlite` survives chats and can be deleted
and rebuilt with `python3 .agents/skills/code-context-graph/scripts/code_graph.py refresh`.

Scope: Python under `src/`, `tests/` and `scripts/`, plus an explicit allowlist
of repository documentation and configuration (see SKILL.md). External libraries,
.env files, notebooks and generated reports are not indexed. All references are static syntactic candidates; aliases,
reflection, dynamic dispatch and fixture overrides may require source inspection.
Results default to 12 rows (maximum 100); narrow the term when results are truncated.
Syntax errors abort refresh and queries without serving the previous stale index.

`search` ranks local lexical matches across 24-line chunks, including source
comments, docstrings and signatures. Tokens split CamelCase/snake_case; common
English question words are ignored. Results show up to six lines (600 characters)
with paths, matched terms and relevance scores. Scores are ordering aids, not
probabilities. Queries are not evaluated as SQL/FTS syntax. No semantic model or
translation is involved; use English keywords present in this repository.
The cache contains local source text, so keep it ignored and private.
