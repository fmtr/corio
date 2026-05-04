# `from corio import secrets`

`secrets` builds on `encrypt` + `sets` to provide repo-oriented secret file workflows.

Main model:

- `Config`: reads `.secrets.yml`, definitions, and contexts
- `Encrypt` command: writes encrypted `*.black.yml` files from source files
- `Decrypt` command: writes source files back from `*.black.yml` when allowed

Install:

```bash
pip install "corio[secrets]" --upgrade
```

## High-level behavior

1. Define file globs and encrypted nodes in `.secrets.yml`.
2. Run encrypt mode to produce `*.black.yml`.
3. Run decrypt mode for selected contexts when needed.

## Minimal `.secrets.yml` shape

```yaml
contexts:
  - name: web
    files:
      - "services/web/**/*.yml"

definitions:
  - files:
      - "services/web/**/*.yml"
    nodes:
      - "env/password"
      - "env/token"
```

## CLI

Entry point:

```bash
corio-secrets encrypt --context=web
corio-secrets decrypt --context=web
```

`encrypt` writes `*.black.yml`, and `decrypt` restores cleartext files when the encrypted side is newer/changed.

