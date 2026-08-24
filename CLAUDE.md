# Personal conventions

Code style, docstrings, and testing follow the code-style skill at
`~/Skills/code-style/`: read `SKILL.md`, `references/shared-principles.md`, and
`references/python-guide.md` before writing or reviewing code.

## Commits
- Atomic commits: each commit is a single concern. Don't bundle unrelated fixes.
- Single-line commit messages by default. Add a body only if I ask for one.
- Make changes, verify with the project's test/lint command, usually `make ci`, then wait for me to say "commit". Never auto-commit.

## Pull requests
- Always rebase and merge. Never create merge commits unless told to do so.
- PR descriptions: terse prose plus bullets when there are many changes. No headers, no "Summary"/"Test plan" scaffolding.
