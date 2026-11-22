"""Configura o frontend em HTML, CSS e JavaScript puros, usando templates e arquivos estáticos do Django.

Uso (a partir da raiz do projeto, depois do startproject):
    python <pasta da skill>/scripts/configure_frontend.py

- Copia os modelos sem sobrescrever: templates/base.html (layout para as páginas estenderem),
  static/css/style.css e static/js/app.js.
- core/settings.py: TEMPLATES 'DIRS' -> [BASE_DIR / 'templates'], STATICFILES_DIRS = [BASE_DIR / 'static']
  e STATIC_ROOT = BASE_DIR / 'staticfiles' (pasta do collectstatic, usada ao publicar o site).
- Não cria rota nem página inicial: o core/urls.py fica como o startproject criou, para o
  runserver mostrar a página padrão do Django ("A instalação foi bem sucedida!") em /.
Cada ajuste só é feito se o arquivo ainda estiver como o startproject criou; se já estiver
configurado, não faz nada; se foi personalizado, deixa como está e apenas avisa.

As mensagens para o usuário são em pt-BR.
"""

import re
import shutil
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "frontend"

# modelo da skill -> destino no projeto
FILES = {
    "base.html": Path("templates/base.html"),
    "style.css": Path("static/css/style.css"),
    "app.js": Path("static/js/app.js"),
}

# (arquivo, nome do ajuste, padrão do startproject, substituto, marca de que já está feito)
EDITS = [
    (
        Path("core/settings.py"),
        "TEMPLATES DIRS",
        re.compile(r"^(\s+)'DIRS': \[\],\n", re.MULTILINE),
        r"\1'DIRS': [BASE_DIR / 'templates'],\n",
        "BASE_DIR / 'templates'",
    ),
    (
        Path("core/settings.py"),
        "STATICFILES_DIRS",
        re.compile(r"^STATIC_URL = 'static/'\n", re.MULTILINE),
        "STATIC_URL = 'static/'\nSTATICFILES_DIRS = [BASE_DIR / 'static']\n",
        "STATICFILES_DIRS",
    ),
    (
        # Pasta para onde o "python manage.py collectstatic" junta todos os arquivos estáticos
        # (do projeto e do admin) para publicar o site. Ajuste separado do anterior para que
        # projetos criados por versões antigas da skill também o recebam.
        Path("core/settings.py"),
        "STATIC_ROOT",
        re.compile(r"^STATICFILES_DIRS = \[BASE_DIR / 'static'\]\n", re.MULTILINE),
        "STATICFILES_DIRS = [BASE_DIR / 'static']\n"
        "# Pasta onde o collectstatic junta os arquivos estaticos para publicar o site\n"
        "STATIC_ROOT = BASE_DIR / 'staticfiles'\n",
        "STATIC_ROOT",
    ),
]


def main() -> int:
    for src, dest in FILES.items():
        if dest.exists():
            print(f"[ja existia]  {dest.as_posix()}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TEMPLATES / src, dest)
            print(f"[criado]      {dest.as_posix()}")

    for path, name, default, replacement, done in EDITS:
        if not path.exists():
            print(f"[aviso]       {path.as_posix()} nao encontrado; pulei: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        if done in text:
            print(f"[ja existia]  {name} ({path.as_posix()})")
        elif default.search(text):
            path.write_text(default.sub(replacement, text, count=1), encoding="utf-8", newline="\n")
            print(f"[configurado] {name} ({path.as_posix()})")
        else:
            print(f"[aviso]       {path.as_posix()} foi personalizado; nao alterei: {name}. Configure a mao.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
