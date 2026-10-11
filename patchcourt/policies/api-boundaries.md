# API Boundaries and Visibility

This repository treats the externally accessible surface of a module as a
versioned contract. Visibility changes are behavioural changes.

- Internal helper methods and functions must remain `private` (or
  module-private) unless they are part of a documented public API.
- Widening visibility (`private` to `public`, `protected` to `public`) is only
  justified when an external caller actually requires access and the change is
  recorded in the public API contract.
- Do not expose implementation details merely to satisfy a linter or a
  refactoring hint; encapsulation is preferred over convenience.
- Increasing visibility of a method that has no external callers is a
  context-dependent recommendation, not a defect.
- Removing accessibility restrictions can be a breaking change for downstream
  consumers even when the code still compiles.

A static-analysis recommendation to make a member more visible must be
adjudicated against this policy before it is acted upon.
