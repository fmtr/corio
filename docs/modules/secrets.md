# secrets
`from corio import sec`

`secrets` builds on `encrypt` + `sets` to provide repo-oriented secret file workflows.

Main model:

- `Config`: reads `.secrets.yml` and its file definitions
- `Encrypt` command: writes encrypted `<raw>.black.yml` files from `<raw>.red.yml` files
- `Decrypt` command: writes `<raw>.red.yml` files back from `<raw>.black.yml` when allowed

Install:

```bash
pip install "corio[secrets]" --upgrade
```

## High-level behavior

1. Define raw file globs and encrypted nodes in `.secrets.yml`; the `.red.yml` suffix is implicit.
2. Run encrypt mode to produce `*.black.yml`.
3. Run decrypt mode to restore the encrypted files when needed.

Any `*.red.yml` file under the current directory not covered by a definition is still encrypted. All of its fields are encrypted and a warning is
logged.

Encryption deletes each red file by default after its black counterpart has been written or verified. Pass
`--delete false` to retain red files. Decryption writes red files by default; pass `--restore true` to write each value
to its original filename and format instead. Pass `--force true` to overwrite every target regardless of its age or
current contents, and `--preserve true` to copy the black file's permissions and ownership to the decrypted target.

## Minimal `.secrets.yml` shape

```yaml
definitions:
  - files:
      - "apps/cedar/config.yaml"
    nodes:
      - "credentials/token"
```

## CLI

Entry point:

```bash
corio secrets encrypt
corio secrets decrypt
```

Optional flags:

```bash
corio secrets encrypt --delete false
corio secrets decrypt --source ./encrypted --target ./restored
corio secrets decrypt --restore true
```

Encryption loads `.secrets.yml` from the repo root, but only processes files in the current directory tree. Configured file
patterns remain repo-root-relative. Decryption defaults `--source` and `--target` to the current directory and recursively
processes black files under `--source`.

For example, the definition path `apps/cedar/config.yaml` matches
`apps/cedar/config.yaml.red.yml`. Encryption writes
`apps/cedar/config.yaml.black.yml`, and decryption restores the red file when the encrypted side is newer or changed.
