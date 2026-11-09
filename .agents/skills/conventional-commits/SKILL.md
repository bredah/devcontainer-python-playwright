---
name: conventional-commits
description: Write or validate commit messages using Conventional Commits. Use whenever preparing, proposing, creating or amending a Git commit in this project.
---

# Conventional Commits

Every commit in this project must use an English Conventional Commit header:

```text
<type>[(scope)][!]: <description>

[optional body]

[optional footers]
```

Use one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
`ci`, `chore`, or `revert`, in lowercase. Choose the type from the actual staged
change. Use a concise imperative description, an optional scope identifying the
changed area, and `!` or a `BREAKING CHANGE:` footer for a breaking public contract.
The lowercase type list is this repository's policy, not a restriction imposed by
the broader Conventional Commits specification.

Examples:

```text
feat(notes): add reusable API exploration notebook
fix(api): handle missing task responses
chore(quality): configure formatting hooks
refactor(components)!: replace the contact form interface
```

Before committing, inspect the staged diff and align the message with its complete
scope. Keep unrelated changes in separate commits when appropriate. Do not stage
unrelated files, amend history, or create a commit unless authorized by the user.
A request to configure this skill does not itself authorize creating a commit.

Validate a message file with the bundled standard-library script:

```bash
python3 .agents/skills/conventional-commits/scripts/check_message.py /path/to/message
```

The installed `commit-msg` hook rejects nonconforming headers, empty descriptions
and bodies without a blank separator. Merge, revert and fixup messages receive no
automatic exemptions; rewrite their headers to this format. It validates syntax,
not whether the message accurately describes the changes. Do not bypass the hook.
For broader rules see https://www.conventionalcommits.org/en/v1.0.0/.
