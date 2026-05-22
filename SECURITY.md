# Security Policy

## Reporting vulnerabilities

Report security issues privately to the maintainer rather than opening a public issue.

Maintainer: Martyn Forryan

## Supported versions

BookMem is pre-1.0. Security fixes will generally be made against the latest release.

## Sensitive data

Do not commit:

```text
private books
API keys
HF_TOKEN
OpenAI keys
BookMem API keys
local `.env` files
generated indexes containing private content
```

Use `.gitignore`, Docker secrets, environment variables or a local secret manager.
