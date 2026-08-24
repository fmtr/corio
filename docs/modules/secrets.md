# secrets
`from corio import sec`

`secrets` builds on `encrypt` + `sets` to provide repo-oriented secret file workflows.

Main model:

- `Config`: reads `.secrets.yml`, definitions, and contexts
- `Encrypt` command: writes encrypted `<raw>.black.yml` files from `<raw>.red.yml` files
- `Decrypt` command: writes `<raw>.red.yml` files back from `<raw>.black.yml` when allowed

Install:

```bash
pip install "corio[secrets]" --upgrade
```

## High-level behavior

1. Define raw file globs and encrypted nodes in `.secrets.yml`; the `.red.yml` suffix is implicit.
2. Run encrypt mode to produce `*.black.yml`.
3. Run decrypt mode for selected contexts when needed.

Any `*.red.yml` file not covered by a definition is still encrypted. All of its fields are encrypted and a warning is
logged.

Encryption deletes each red file by default after its black counterpart has been written or verified. Pass
`--delete false` to retain red files. Decryption writes red files by default; pass `--restore true` to write each value
to its original filename and format instead. Pass `--force true` to overwrite every target regardless of its age or
current contents, and `--preserve true` to copy the black file's permissions and ownership to the decrypted target.

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
corio secrets encrypt --context=web
corio secrets decrypt --context=web
```

For example, the definition path `services/web/config.yaml` matches
`services/web/config.yaml.red.yml`. Encryption writes
`services/web/config.yaml.black.yml`, and decryption restores the red file when the encrypted side is newer or changed.
