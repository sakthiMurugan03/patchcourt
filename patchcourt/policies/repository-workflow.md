# Repository Workflow

- Pull requests should be small and focused; unrelated refactors are split out.
- Review comments must cite the file, line, rule, and supporting evidence.
- Findings that are technically valid but unnecessary in the current change are
  recorded as acknowledged rather than blocking.
- A recommendation that conflicts with the repository's documented design is
  not treated as a defect; it is escalated as a policy decision.
- Security-sensitive paths (authentication, cryptography, database access) get
  additional review and are prioritised above style findings.
