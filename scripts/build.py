"""Gera o .zip de uma skill em dist/, para subir nas configurações de Skills do Claude (claude.ai).

Só é preciso para usar uma skill no claude.ai (chat). No Claude Code, as skills e os agents são
instalados pelo marketplace deste repositório (veja o README), sem zip.

Uso (a partir da raiz do repositório):
    python scripts/build.py                 # todas as skills de todos os plugins
    python scripts/build.py django          # só uma

- Procura as skills em plugins/<plugin>/skills/<skill>/.
- Cada zip tem a pasta da skill na raiz (ex.: django/SKILL.md), como o Claude espera.
- Deixa de fora __pycache__ e arquivos .pyc.
- Confere se a skill tem SKILL.md e se o "name:" do cabeçalho é igual ao nome da pasta.
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
DIST = ROOT / "dist"


def all_skills() -> dict:
    """{nome da skill: pasta}, de todos os plugins."""
    skills = {}
    for skill in sorted(PLUGINS.glob("*/skills/*")):
        if skill.is_dir():
            if skill.name in skills:
                sys.exit(f"falhou: a skill '{skill.name}' existe em mais de um plugin")
            skills[skill.name] = skill
    return skills


def build(skill: Path) -> Path:
    manifest = skill / "SKILL.md"
    if not manifest.exists():
        sys.exit(f"falhou: {skill.name}/SKILL.md nao encontrado")
    name = re.search(r"^name:\s*(\S+)", manifest.read_text(encoding="utf-8"), re.MULTILINE)
    if not name or name.group(1) != skill.name:
        sys.exit(f"falhou: o 'name:' do {skill.name}/SKILL.md precisa ser '{skill.name}'")

    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill.name}.zip"
    files = sorted(
        p for p in skill.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(skill.parent).as_posix())
    print(f"[criado]      {out.relative_to(ROOT).as_posix()} ({len(files)} arquivos)")
    return out


def main() -> int:
    skills = all_skills()
    for name in sys.argv[1:] or skills:
        if name not in skills:
            sys.exit(f"falhou: skill '{name}' nao encontrada em plugins/*/skills/")
        build(skills[name])
    return 0


if __name__ == "__main__":
    sys.exit(main())
