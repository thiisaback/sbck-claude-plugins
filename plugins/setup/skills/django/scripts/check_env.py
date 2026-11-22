"""Lê e valida as variáveis de ambiente do projeto, do mesmo jeito que o Django vai lê-las.

Uso (a partir da raiz do projeto):
    python <pasta da skill>/scripts/check_env.py

- Prioridade igual à do settings.py (load_dotenv sem override): uma variável já definida no
  ambiente do sistema vale mais que a do .env.
- Se o .env ainda não existe, valida o arquivo de onde ele será criado (.env.example ou o
  modelo da skill), completado com os valores do modelo, como o make_env.py faz.
- Valida DJANGO_DB_ENGINE, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DJANGO_SECRET_KEY (só quando vem
  do ambiente do sistema: a do .env o make_env.py corrige sozinho), POSTGRES_HOST e POSTGRES_PORT.
- Credenciais do PostgreSQL em branco não são erro: o setup cria tudo e só pula a conexão e o
  migrate até o usuário preencher.
- Sai com código 1 se algum valor for inválido.

Só usa a biblioteca padrão do Python (roda antes de o pip instalar qualquer coisa).
As mensagens para o usuário são em pt-BR, só com caracteres ASCII.
"""

import os
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "env.example"
EXAMPLE = Path(".env.example")
ENV = Path(".env")

# Valores aceitos em DJANGO_DB_ENGINE (vazio ou ausente = postgres, como no settings.py)
DB_ENGINES = ("postgres", "sqlite")
# Credenciais que o usuário precisa preencher para o Django conectar ao PostgreSQL
REQUIRED_DB = ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
# Valor de exemplo da DJANGO_SECRET_KEY no modelo (nunca pode ser usado de verdade)
EXAMPLE_SECRET = "troque-por-uma-chave-aleatoria"
# O settings.py considera DEBUG ligado só com estes valores; os demais aceitos significam desligado
DEBUG_TRUE = ("1", "true", "yes")
DEBUG_FALSE = ("0", "false", "no", "")

# Linha "CHAVE=valor", aceitando "export " e espaços em volta do "=", como o python-dotenv
VAR_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$")


def var_pattern(key: str) -> re.Pattern:
    """Regex da linha de uma variável no arquivo (para trocar o valor no lugar)."""
    return re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=.*$", re.MULTILINE)


def parse_value(raw: str) -> str:
    """Valor como o python-dotenv entrega: sem aspas em volta e sem comentário no fim (' #')."""
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        if end != -1:
            return raw[1:end]
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def read_vars(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = VAR_LINE.match(line)
        if m:
            values[m.group(1)] = parse_value(m.group(2))
    return values


def env_source() -> Path:
    """Arquivo de onde vêm os valores: o .env ou, se ainda não existe, de onde ele será criado."""
    return ENV if ENV.exists() else EXAMPLE if EXAMPLE.exists() else TEMPLATE


def effective_env():
    """Valores que o Django vai usar e a lista das variáveis que vêm do ambiente do sistema.

    O .env (ou o arquivo de onde ele será criado) é completado com os valores do modelo, como o
    make_env.py faz, e as variáveis definidas no ambiente do sistema têm prioridade.
    """
    values = {**read_vars(TEMPLATE), **read_vars(env_source())}
    from_os = sorted(k for k in values if k in os.environ)
    values.update({k: os.environ[k].strip() for k in from_os})
    return values, from_os


def db_engine(values: dict) -> str:
    return (values.get("DJANGO_DB_ENGINE") or "postgres").strip().lower()


def validate(values: dict, from_os: list) -> list:
    """Lista de (variável, problema). Vazia se estiver tudo certo."""
    errors = []

    engine = db_engine(values)
    if engine not in DB_ENGINES:
        errors.append(("DJANGO_DB_ENGINE", f"'{values['DJANGO_DB_ENGINE']}' invalido: use postgres ou sqlite"))

    debug = values.get("DJANGO_DEBUG", "").lower()
    if debug not in DEBUG_TRUE + DEBUG_FALSE:
        errors.append(("DJANGO_DEBUG", f"'{values['DJANGO_DEBUG']}' invalido: use True ou False"))

    for host in (h.strip() for h in values.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()):
        if "://" in host or "/" in host:
            errors.append(("DJANGO_ALLOWED_HOSTS", f"'{host}': use so o dominio, sem http:// nem caminho (ex.: meusite.com.br)"))
        elif re.search(r"\s", host):
            errors.append(("DJANGO_ALLOWED_HOSTS", f"'{host}': separe os dominios por virgula"))
        elif re.fullmatch(r"[^:\[\]]+:[0-9]+|\[[^\]]+\]:[0-9]+", host):
            errors.append(("DJANGO_ALLOWED_HOSTS", f"'{host}': use o dominio sem a porta (ex.: localhost, nao localhost:8000)"))

    # A do .env o make_env.py troca sozinho por uma aleatória; a do ambiente do sistema, não
    if "DJANGO_SECRET_KEY" in from_os and values["DJANGO_SECRET_KEY"] in ("", EXAMPLE_SECRET):
        errors.append(("DJANGO_SECRET_KEY", "vazia ou com o valor de exemplo: defina uma chave ou remova a variavel do ambiente do sistema"))

    if engine == "postgres":
        port = values.get("POSTGRES_PORT", "")
        if port and not (re.fullmatch(r"[0-9]+", port) and 1 <= int(port) <= 65535):
            errors.append(("POSTGRES_PORT", f"'{port}' invalida: use um numero de 1 a 65535 (padrao 5432)"))
        host = values.get("POSTGRES_HOST", "")
        if "://" in host:
            errors.append(("POSTGRES_HOST", f"'{host}': use so o endereco do servidor (ex.: 127.0.0.1), sem postgres://"))
        elif re.search(r"\s", host):
            errors.append(("POSTGRES_HOST", f"'{host}': o endereco nao pode ter espacos"))
        elif re.fullmatch(r"[^:/]+:[0-9]+", host):
            errors.append(("POSTGRES_HOST", f"'{host}': tire a porta do host e coloque-a em POSTGRES_PORT"))

    return errors


def origin(key: str, from_os: list) -> str:
    return "ambiente do sistema" if key in from_os else env_source().name


def check():
    """Valida e imprime o resultado. Devolve (valores, origem de cada variável, erros)."""
    values, from_os = effective_env()
    if from_os:
        print(f"[aviso]       definidas no ambiente do sistema (valem mais que o .env): {', '.join(from_os)}", flush=True)
    errors = validate(values, from_os)
    for key, problem in errors:
        print(f"[erro]        {key} ({origin(key, from_os)}): {problem}", flush=True)
    if not errors:
        print(f"[ok]          variaveis de ambiente validas (DJANGO_DB_ENGINE={db_engine(values)}, "
              f"de: {origin('DJANGO_DB_ENGINE', from_os)})", flush=True)
    return values, from_os, errors


def main() -> int:
    # Evita erro ao imprimir valores com caracteres especiais em consoles com codificação limitada
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    return 1 if check()[2] else 0


if __name__ == "__main__":
    sys.exit(main())
