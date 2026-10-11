# Coding Standards

- Keep functions small and their cyclomatic complexity low. Refactor complex
  functions into smaller units with clear names.
- Remove unused imports, variables, and dead declarations; they hide mistakes
  and add review noise.
- Prefer explicit error handling over bare `except` clauses.
- Every behavioural change requires a corresponding test.
- Maintainability concerns such as complexity or dead code are tracked, but a
  code smell does not by itself establish a runtime defect. Distinguish
  maintainability from correctness when prioritising a finding.
