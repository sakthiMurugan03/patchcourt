# Security Policy

All security findings are adjudicated before merge.

- Secrets (passwords, tokens, API keys) must be loaded from the environment or a
  secret manager. Hardcoded credentials are never acceptable. Placeholder and
  example values (`changeme`, `example`, `dummy`, `your_key`) are not secrets.
- SQL must be executed with parameterized queries. String concatenation of
  values into a query is prohibited even when the current input looks trusted.
- Shell invocation must avoid `shell=true`. Prefer an argument list so untrusted
  input cannot inject commands.
- Network calls must use HTTPS. Plaintext `http://` endpoints are prohibited in
  application code.
- Deserialization must use a safe loader; `pickle` and `yaml.load` with a full
  loader are prohibited for untrusted input.
- A reported finding is only actionable when the unsafe pattern is actually
  present on the flagged line; a scanner match that cannot be reproduced in the
  code is treated as context that must be verified, not accepted blindly.
