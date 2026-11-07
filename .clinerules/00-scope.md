# 00 — Scope (hard rule)

- Your **only** working directory is:
  `/home/joaquin/proyectos/cad-agent-test`
- You may **read and write only inside that folder**.
- **Forbidden:** writing, moving, or deleting anything outside it.
- **Forbidden:** `sudo`, `pacman`, `flatpak`, `pip install`, `npm install`,
  `curl`, `wget`, `git clone`, and any change to `~/.config`, `~/.local`,
  `~/Applications`, `~/models`, `~/build`, or other projects.
- **Forbidden:** reading personal files outside the project (Documents,
  Downloads, Desktop, etc.).
- **Forbidden:** reading `~/.cline/data/settings/providers.json` or any file with
  API keys or credentials. If `usage.py` needs session data, read only
  `~/.cline/data/sessions/` (metrics, not credentials).
- If you need something outside scope: **stop and ask for permission**.

## Files not to touch without explicit permission

`caba_rules.json`, `plan.py`, `check.py`, `run.sh`, `AGENTS.md`, `.clinerules/`,
`docs/CABA_RULES.md`, `schemas/spec.schema.json`, `tools/validate_spec.py`,
`tools/usage.py`, `sheet_lib.py`, `blocks_build.py`, and `CAD_Blocks/`.

## Environment

- Linux, bash. Python 3.10+ with `ezdxf` and `matplotlib`.
- `cadcraft-cli` is optional and only needed for PNG/DWG/PDF.
- Work in **English** for documents, comments, and user-facing messages.
