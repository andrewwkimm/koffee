# Personal conventions

## Commits
- Atomic commits: each commit is a single concern. Don't bundle unrelated fixes.
- Single-line commit messages by default. Add a body only if I ask for one.
- Make changes, verify with the project's test/lint command, usually `make ci`, then wait for me to say "commit". Never auto-commit.

## Pull requests
- Always rebase and merge. Never create merge commits unless told to do so.
- PR descriptions: terse prose plus bullets when there are many changes. No headers, no "Summary"/"Test plan" scaffolding.

## Code style
- Catch specific exceptions, never blanket `except Exception`.
- Prefer named return variables over long chained return expressions.
- Order private functions by their first appearance in the call chain from the public function. Each function is placed immediately after its caller, followed by any helpers it calls that haven't been defined yet. Shared helpers go after their first caller. Among peers with no caller/callee relationship, order alphabetically. Validation and check functions (`_validate_*`, `_check_*`) always go last — they are support infrastructure, not part of the main logic flow. This is intended to be opinionated and called out in code review.
- Declare variables close to where they are used. Don't bind a name at the top of a function and then reach for it 20 lines later. Inline the expression at the use site, or if it must be named, define it on the line before it is consumed. Same readability motivation as the Stepdown Rule.
- Indentation depth: aim for at most 2 levels of nesting inside a function. Go to 3 only when the loops/conditionals are so tightly coupled that splitting them would obscure the logic. Never beyond 3, and if you're getting there, extract a helper so the reader can name what each layer is doing instead of decoding indentation.
- Don't break functions into smaller ones based on length alone. Prefer keeping logic together unless extraction provides genuine value: either the helper hides real complexity behind a simpler interface (it's "deep" — the interface is meaningfully simpler than what it implements), or it's reusable across multiple call sites. A helper that is invoked once, is a few lines, and exposes roughly as much complexity as it hides adds indirection without benefit — inline it instead.
- When splitting, the two pieces should be independently understandable: someone reading the parent shouldn't need to read the child, and vice versa. If you find yourself flipping between them to understand either one, the split was wrong. A well-extracted helper is typically general-purpose enough to be called elsewhere, not tailor-made for one parent.

## Docstrings
- Module-level docstrings: descriptive (sentence about what the module is/does).
- Function and method docstrings: prefer non-imperative phrasing, eg "Returns the parsed config" not "Return the parsed config", "Tests that X" not "Test that X", "Raises ValueError when..." not "Raise ValueError when...".
- The non-imperative rule isn't absolute: when a noun-phrase reads more naturally, use it (e.g. a Pydantic model class can have `"""Pydantic base model for koffee configuration."""`). The goal is description over command, not blind grammar.
