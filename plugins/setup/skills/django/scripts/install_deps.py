"""Instala as dependências do projeto no .venv e cria o requirements.txt.

Uso (a partir da raiz do projeto, com o Python do .venv):
    python <pasta da skill>/scripts/install_deps.py

- Se o requirements.txt já existir: instala exatamente o que ele pede (pip install -r), sem trocar
  as versões fixadas. Se faltar nele Django, psycopg ou python-dotenv, instala o que faltar no .venv
  e avisa quais linhas adicionar (o arquivo não é alterado).
- Se não existir: instala Django, psycopg[binary] e python-dotenv e cria o requirements.txt com as
  versões instaladas fixadas.
- Confere a versão mínima do Django (MIN_DJANGO): numa instalação nova, pede ao pip Django>=MIN_DJANGO;
  se o requirements.txt fixar uma versão mais antiga, para com erro (o arquivo não é alterado).

As mensagens para o usuário são em pt-BR.
"""

import re
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

# Versão mínima do Django suportada pelo setup (o Django 6 exige Python 3.12 ou mais novo)
MIN_DJANGO = (6, 0)
MIN_DJANGO_STR = ".".join(map(str, MIN_DJANGO))

# (nome no pip / requirements.txt, módulo importado, nome da distribuição)
REQUIRED = [
    ("Django", "django", "Django"),
    ("psycopg[binary]", "psycopg", "psycopg"),
    ("python-dotenv", "dotenv", "python-dotenv"),
]
REQ = Path("requirements.txt")


def pip_spec(name: str) -> str:
    """Nome para o pip install; o Django vai com a versão mínima (ex.: Django>=6.0)."""
    return f"{name}>={MIN_DJANGO_STR}" if name == "Django" else name


def version_tuple(version: str) -> tuple:
    m = re.match(r"(\d+)\.(\d+)", version)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def pip(*args: str) -> None:
    if subprocess.call([sys.executable, "-m", "pip", *args]) != 0:
        sys.exit(f"falhou: pip {' '.join(args)}")


def installed_versions() -> dict:
    # Roda num processo novo para enxergar o que o pip acabou de instalar
    code = (
        "from importlib.metadata import version\n"
        f"for d in {[d for _, _, d in REQUIRED]!r}: print(version(d))"
    )
    out = subprocess.check_output([sys.executable, "-c", code], text=True).split()
    return {name: v for (name, _, _), v in zip(REQUIRED, out)}


def main() -> int:
    pip("install", "--upgrade", "pip", "-q")

    missing = []
    if REQ.exists():
        pip("install", "-q", "-r", str(REQ))
        missing = [name for name, module, _ in REQUIRED if find_spec(module) is None]
        if missing:
            pip("install", "-q", *[pip_spec(m) for m in missing])
    else:
        pip("install", "-q", *[pip_spec(name) for name, _, _ in REQUIRED])

    versions = installed_versions()
    # Saída só em ASCII: o console do Windows nem sempre exibe bem caracteres especiais
    print(", ".join(f"{name.split('[')[0]} {v}" for name, v in versions.items()))

    if version_tuple(versions["Django"]) < MIN_DJANGO:
        sys.exit(f"falhou: Django {versions['Django']} instalado (pelo requirements.txt), mas o minimo e "
                 f"{MIN_DJANGO_STR}. Ajuste a linha do Django no requirements.txt (ex.: Django>={MIN_DJANGO_STR}) "
                 "e rode o setup de novo.")
    print(f"[ok]          Django {versions['Django']} (minimo {MIN_DJANGO_STR})")

    pins = {name: f"{name}=={v}" for name, v in versions.items()}
    if not REQ.exists():
        REQ.write_text("\n".join(pins.values()) + "\n", encoding="utf-8", newline="\n")
        print("[criado]      requirements.txt")
    elif missing:
        print("[ja existia]  requirements.txt (instalado com pip install -r)")
        print(f"[aviso]       requirements.txt nao tem {', '.join(missing)}; instalei no .venv. Adicione: {', '.join(pins[m] for m in missing)}")
    else:
        print("[ja existia]  requirements.txt (instalado com pip install -r)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
