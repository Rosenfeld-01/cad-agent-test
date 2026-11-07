# 00 — Alcance (regla dura)

- Tu **único** directorio de trabajo es:
  `/home/joaquin/proyectos/cad-agent-test`
- Solo podés **leer y escribir dentro de esa carpeta**.
- **Prohibido** escribir, mover o borrar cualquier cosa fuera de ella.
- **Prohibido**: `sudo`, `pacman`, `flatpak`, `pip install`, `npm install`,
  `curl`, `wget`, `git clone`, y cualquier cambio en `~/.config`, `~/.local`,
  `~/Applications`, `~/models`, `~/build` u otros proyectos.
- **Prohibido** leer archivos personales fuera del proyecto (Documentos,
  Descargas, Escritorio, etc.).
- **Prohibido** leer `~/.cline/data/settings/providers.json` ni cualquier archivo
  que contenga API keys o credenciales. Si `usage.py` necesita datos de sesiones,
  lee sólo `~/.cline/data/sessions/` (métricas, no credenciales).
- Si necesitás algo que está fuera del alcance: **pará y pedí permiso**.

## Archivos que no se tocan sin permiso explícito

`rules_caba.json`, `plan.py`, `check.py`, `run.sh`, `AGENTS.md`, `.clinerules/`,
`MEDIDAS_CABA.md`, `schemas/spec.schema.json`, `tools/validate_spec.py`,
`tools/usage.py`, `tools/new_case.py`, `tools/qa_laminas.py`,
`tools/qa_geometria.py`.

Podés leerlos siempre. Para modificarlos, pedí permiso primero.

## Archivos de trabajo (sí se editan)

- `casos/<slug>/` — brief, specs, decisiones y metadata del proyecto.
- `briefs/` — entradas de proyectos nuevos.
- `typologies/` — se agregan tipologías; las existentes se editan con criterio y
  se anota el cambio.
- `out/` — salidas generadas (DXF, PNG, reportes). No se editan a mano.
- `docs/` — documentación del método.

## Terminal

- Todos los comandos se ejecutan con `cd /home/joaquin/proyectos/cad-agent-test && ...`
  o con rutas absolutas dentro de esa carpeta.
- Nunca uses `rm -rf`. Solo podés borrar archivos que vos mismo generaste dentro
  de `out/` o de `casos/<slug>/`.
- No instales nada. Las herramientas ya están instaladas.
- No leas archivos enormes con `cat`: usá `grep`, `head`, `tail` o `read`.
