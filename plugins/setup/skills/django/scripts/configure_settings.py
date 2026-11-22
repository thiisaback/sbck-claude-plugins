"""Ajusta o core/settings.py: configuração lida do .env, idioma e fuso horário do Brasil.

Uso (a partir da raiz do projeto, com o .venv ativo):
    python <pasta da skill>/scripts/configure_settings.py [caminho/do/settings.py]

Cada item é tratado separadamente e só é alterado se ainda estiver como o startproject criou:
- DATABASES (SQLite padrão) -> escolhido por DJANGO_DB_ENGINE no .env: 'postgres' (variáveis POSTGRES_*)
  ou 'sqlite' (db.sqlite3). Também atualiza o bloco só-PostgreSQL gerado por versões antigas da skill.
- SECRET_KEY fixa ('django-insecure-...') -> DJANGO_SECRET_KEY do .env (a chave fixa sai do código e do git).
- DEBUG = True -> DJANGO_DEBUG do .env (padrão False, se a variável não existir).
- ALLOWED_HOSTS = [] -> DJANGO_ALLOWED_HOSTS do .env (lista separada por vírgula).
- LANGUAGE_CODE = 'en-us' -> 'pt-br'.
- TIME_ZONE = 'UTC' -> 'America/Sao_Paulo'.
Se o item já está configurado, não faz nada; se foi personalizado, deixa como está e apenas avisa.

As mensagens para o usuário são em pt-BR.
"""

import re
import sys
from pathlib import Path

SETTINGS = Path(sys.argv[1] if len(sys.argv) > 1 else "core/settings.py")

# Bloco gerado por versões antigas desta skill (só PostgreSQL); é trocado pelo DATABASES_BLOCK
OLD_POSTGRES_BLOCK = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'app'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
"""

DATABASES_BLOCK = """# Banco de dados, escolhido por DJANGO_DB_ENGINE no .env:
#   postgres -> PostgreSQL já existente, com as credenciais POSTGRES_* (padrão)
#   sqlite   -> arquivo db.sqlite3 na raiz do projeto, sem credenciais
DB_ENGINE = (os.environ.get('DJANGO_DB_ENGINE') or 'postgres').strip().lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DB_ENGINE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'app'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        f"DJANGO_DB_ENGINE='{DB_ENGINE}' invalido no .env: use 'postgres' ou 'sqlite'."
    )
"""

# (nome, padrão(ões) a substituir, substituto, marca de que já está configurado)
ITEMS = [
    (
        "DATABASES",
        (
            # Padrão do startproject (SQLite)
            re.compile(
                r"^DATABASES = \{\n"
                r"\s+'default': \{\n"
                r"\s+'ENGINE': 'django\.db\.backends\.sqlite3',\n"
                r"\s+'NAME': BASE_DIR / 'db\.sqlite3',\n"
                r"\s+\}\n"
                r"\}\n",
                re.MULTILINE,
            ),
            # Bloco só-PostgreSQL gerado por versões antigas desta skill
            re.compile("^" + re.escape(OLD_POSTGRES_BLOCK), re.MULTILINE),
        ),
        DATABASES_BLOCK,
        "DJANGO_DB_ENGINE",
    ),
    (
        "SECRET_KEY",
        re.compile(r"^SECRET_KEY = 'django-insecure-.*'\n", re.MULTILINE),
        "SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')\n",
        "os.environ.get('DJANGO_SECRET_KEY'",
    ),
    (
        "DEBUG",
        re.compile(r"^DEBUG = True\n", re.MULTILINE),
        "DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')\n",
        "os.environ.get('DJANGO_DEBUG'",
    ),
    (
        "ALLOWED_HOSTS",
        re.compile(r"^ALLOWED_HOSTS = \[\]\n", re.MULTILINE),
        "ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]\n",
        "os.environ.get('DJANGO_ALLOWED_HOSTS'",
    ),
    (
        "LANGUAGE_CODE",
        re.compile(r"^LANGUAGE_CODE = 'en-us'\n", re.MULTILINE),
        "LANGUAGE_CODE = 'pt-br'\n",
        "LANGUAGE_CODE = 'pt-br'",
    ),
    (
        "TIME_ZONE",
        re.compile(r"^TIME_ZONE = 'UTC'\n", re.MULTILINE),
        "TIME_ZONE = 'America/Sao_Paulo'\n",
        "TIME_ZONE = 'America/Sao_Paulo'",
    ),
]

IMPORTS = "import os\nfrom pathlib import Path\n\nfrom dotenv import load_dotenv\n"
BASE_DIR_LINE = "BASE_DIR = Path(__file__).resolve().parent.parent\n"
LOAD_ENV = (
    "\n# Carrega o .env da raiz do projeto (variáveis já definidas no ambiente têm prioridade).\n"
    "load_dotenv(BASE_DIR / '.env')\n"
)


def ensure_dotenv(text: str):
    """Garante `import os`, `load_dotenv` e a chamada logo após o BASE_DIR. Devolve None se não achar onde inserir."""
    if "from dotenv import load_dotenv" not in text:
        if "from pathlib import Path\n" not in text or BASE_DIR_LINE not in text:
            return None
        text = text.replace("from pathlib import Path\n", IMPORTS, 1)
        text = text.replace(BASE_DIR_LINE, BASE_DIR_LINE + LOAD_ENV, 1)
    elif "import os\n" not in text:
        text = text.replace("from pathlib import Path\n", "import os\nfrom pathlib import Path\n", 1)
    return text


def main() -> int:
    if not SETTINGS.exists():
        print(f"[aviso]       {SETTINGS} nao encontrado")
        return 1

    original = SETTINGS.read_text(encoding="utf-8")
    text = original
    changed = []

    for name, defaults, replacement, done in ITEMS:
        if not isinstance(defaults, tuple):
            defaults = (defaults,)
        match = next((d for d in defaults if d.search(text)), None)
        if done in text:
            print(f"[ja existia]  {name} ja configurado")
        elif match:
            text = match.sub(lambda _: replacement, text, count=1)
            changed.append(name)
        else:
            print(f"[aviso]       {name} de {SETTINGS} foi personalizado; nao alterei. Configure a mao.")

    if not changed:
        return 0

    text = ensure_dotenv(text)
    if text is None:
        print(f"[aviso]       nao achei 'from pathlib import Path' / BASE_DIR em {SETTINGS}; nao alterei.")
        return 0

    SETTINGS.write_text(text, encoding="utf-8", newline="\n")
    print(f"[configurado] {SETTINGS}: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
