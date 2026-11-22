"""Testa a conexão com o PostgreSQL passo a passo, com uma dica em pt-BR para cada falha.

Uso (a partir da raiz do projeto, com o Python do .venv, que tem o psycopg e o Django):
    python <pasta da skill>/scripts/check_db.py

Usa os mesmos valores que o Django (ambiente do sistema > .env; veja check_env.py) e para no
primeiro teste que falhar:
  1. Endereco    - o POSTGRES_HOST existe (DNS)?
  2. Porta       - o servidor responde em POSTGRES_HOST:POSTGRES_PORT?
  3. Login       - o usuário e a senha são aceitos?
  4. Banco       - o POSTGRES_DB existe?
  5. Acesso      - o usuário consegue conectar no POSTGRES_DB?
  6. Versao      - o PostgreSQL é novo o bastante para o Django instalado?
  7. Tabelas     - o usuário pode criar tabelas (o migrate precisa)?
  8. Codificacao - o banco é UTF-8? (só aviso, não impede o migrate)
Os testes 1 a 4 não dependem do idioma das mensagens do servidor: o diagnóstico vem da rede e de
consultas, não do texto do erro.

Sai com código 0 se o banco está pronto para o migrate, 1 se não. Nunca mostra a senha.
As mensagens para o usuário são em pt-BR, só com caracteres ASCII.
"""

import re
import socket
import sys
import unicodedata

sys.dont_write_bytecode = True   # não cria __pycache__ dentro da pasta da skill ao importar o check_env
from check_env import REQUIRED_DB, db_engine, effective_env, validate  # noqa: E402

TIMEOUT = 5   # segundos para a rede e para o login, para um host errado não travar o setup
TOTAL = 8
# Bancos que todo servidor PostgreSQL tem: usados para testar o login quando o banco do projeto falha
MAINTENANCE_DBS = ("postgres", "template1")


def ascii_text(text) -> str:
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()


def ok(n, m):   print(f"[ok]          {n}/{TOTAL} {m}", flush=True)
def fail(n, m): print(f"[erro]        {n}/{TOTAL} {m}", flush=True)
def warn(n, m): print(f"[aviso]       {n}/{TOTAL} {m}", flush=True)
def tip(m):     print(f"              dica: {m}", flush=True)


def detail(exc):
    """Última linha útil da mensagem do servidor ou do libpq (ex.: 'FATAL: password authentication failed')."""
    lines = [line.strip() for line in str(exc).strip().splitlines() if line.strip()]
    print(f"              erro: {ascii_text(lines[-1] if lines else type(exc).__name__)}", flush=True)


def ident(name: str) -> str:
    """Nome pronto para um comando SQL (entre aspas se tiver maiúsculas ou caracteres especiais)."""
    return name if re.fullmatch(r"[a-z_][a-z0-9_]*", name) else '"' + name.replace('"', '""') + '"'


def django_minimum():
    """Versão mínima do PostgreSQL exigida pelo Django instalado (lida do próprio Django) e a versão do Django."""
    try:
        import django
        from django.db.backends.postgresql.features import DatabaseFeatures
        return tuple(DatabaseFeatures.minimum_database_version), django.get_version()
    except Exception:
        return None, None


def check_network(host: str, port: int) -> bool:
    if host.startswith("/"):
        ok("1-2", f"endereco e porta: socket local {host} (teste de rede nao se aplica)")
        return True
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        fail(1, f"endereco: '{host}' nao encontrado")
        tip("confira POSTGRES_HOST no .env (ex.: 127.0.0.1 para um PostgreSQL nesta maquina)")
        return False
    ok(1, f"endereco: {host} encontrado")
    try:
        socket.create_connection((host, port), timeout=TIMEOUT).close()
    except ConnectionRefusedError:
        fail(2, f"porta: {host}:{port} recusou a conexao")
        tip("o PostgreSQL esta parado ou usa outra porta. Inicie o servico (Windows: services.msc > postgresql) "
            "ou confira POSTGRES_PORT. Em servidor remoto, ele pode estar aceitando so conexoes locais "
            "(listen_addresses no postgresql.conf)")
        return False
    except TimeoutError:
        fail(2, f"porta: {host}:{port} nao respondeu em {TIMEOUT} s")
        tip("um firewall pode estar bloqueando a porta, ou o endereco esta errado")
        return False
    except OSError as e:
        fail(2, f"porta: nao consegui chegar a {host}:{port} ({ascii_text(e.strerror or e)})")
        tip("confira POSTGRES_HOST e POSTGRES_PORT no .env e a conexao de rede")
        return False
    ok(2, f"porta: o servidor responde em {host}:{port}")
    return True


def main() -> int:
    try:
        sys.stdout.reconfigure(errors="replace", line_buffering=True)
    except (AttributeError, ValueError):
        pass

    values, from_os = effective_env()
    errors = validate(values, from_os)
    for key, problem in errors:
        print(f"[erro]        {key}: {problem}")
    if errors:
        return 1
    if db_engine(values) == "sqlite":
        print("[ok]          DJANGO_DB_ENGINE=sqlite: banco em arquivo (db.sqlite3), nada a testar")
        return 0
    blank = [k for k in REQUIRED_DB if not values.get(k)]
    if blank:
        print(f"[erro]        preencha no .env: {', '.join(blank)}")
        return 1
    try:
        import psycopg
    except ImportError:
        print("[erro]        psycopg nao instalado neste Python: rode este script com o Python do .venv")
        return 1

    host, port, db, user = values["POSTGRES_HOST"], int(values["POSTGRES_PORT"]), values["POSTGRES_DB"], values["POSTGRES_USER"]

    def connect(dbname):
        return psycopg.connect(host=host, port=port, dbname=dbname, user=user,
                               password=values["POSTGRES_PASSWORD"], connect_timeout=TIMEOUT, autocommit=True)

    # 1-2. Rede
    if not check_network(host, port):
        return 1

    # 3-5. Login, banco e acesso. Primeiro tenta o banco do projeto; se falhar, descobre o motivo
    # entrando num banco que todo servidor tem e consultando a lista de bancos.
    try:
        conn = connect(db)
    except psycopg.Error as target_error:
        maint = None
        for name in MAINTENANCE_DBS:
            if name != db:
                try:
                    maint = connect(name)
                    break
                except psycopg.Error:
                    pass
        if maint is None:
            fail(3, f"login: o servidor recusou o usuario '{user}'")
            detail(target_error)
            tip("confira POSTGRES_USER e POSTGRES_PASSWORD no .env. Se estiverem certos, o pg_hba.conf do "
                "servidor pode nao permitir esse usuario a partir deste computador")
            return 1
        ok(3, f"login: usuario '{user}' aceito")
        with maint:
            exists = maint.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,)).fetchone()
            row = maint.execute("SELECT rolcreatedb OR rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()
        if not exists:
            fail(4, f"banco: '{db}' nao existe no servidor")
            if row and row[0]:
                tip(f"o usuario '{user}' pode cria-lo: CREATE DATABASE {ident(db)};")
            else:
                tip(f"peca a um administrador do PostgreSQL (ex.: usuario postgres) para rodar: "
                    f"CREATE DATABASE {ident(db)} OWNER {ident(user)};")
            return 1
        ok(4, f"banco: '{db}' existe")
        fail(5, f"acesso: o usuario '{user}' nao conseguiu conectar no banco '{db}'")
        detail(target_error)
        tip(f"um administrador pode liberar com: GRANT CONNECT ON DATABASE {ident(db)} TO {ident(user)};")
        return 1

    with conn:
        ok(3, f"login: usuario '{user}' aceito")
        ok(4, f"banco: '{db}' existe")
        ok(5, f"acesso: conectado no banco '{db}'")

        # 6. Versão mínima, lida do Django instalado (muda a cada versão do Django)
        server = conn.info.server_version          # ex.: 160004 = 16.4
        version = (server // 10000, server % 10000)
        shown = f"{version[0]}.{version[1]}"
        minimum, django_version = django_minimum()
        if minimum and version < minimum:
            need = ".".join(map(str, minimum))
            fail(6, f"versao: PostgreSQL {shown}; o Django {django_version} exige {need} ou mais novo")
            tip(f"atualize o PostgreSQL para {need}+ ou use DJANGO_DB_ENGINE=sqlite")
            return 1
        ok(6, f"versao: PostgreSQL {shown}" + (f" (minimo do Django {django_version}: {'.'.join(map(str, minimum))})" if minimum else ""))

        # 7. Permissão para criar tabelas no schema onde o Django vai criá-las
        schema, can_create = conn.execute(
            "SELECT current_schema(), has_schema_privilege(current_schema(), 'CREATE')").fetchone()
        if schema is None:
            fail(7, "tabelas: nenhum schema do search_path existe neste banco")
            tip(f"um administrador pode criar o schema: CREATE SCHEMA public AUTHORIZATION {ident(user)};")
            return 1
        if not can_create:
            fail(7, f"tabelas: o usuario '{user}' nao pode criar tabelas no schema '{schema}' (o migrate precisa)")
            tip("desde o PostgreSQL 15, so o dono do banco cria tabelas no schema public. Um administrador pode "
                f"resolver com: ALTER DATABASE {ident(db)} OWNER TO {ident(user)};  ou, conectado no banco "
                f"'{db}': GRANT CREATE ON SCHEMA {ident(schema)} TO {ident(user)};")
            return 1
        ok(7, f"tabelas: o usuario pode criar tabelas no schema '{schema}'")

        # 8. Codificação (só aviso)
        encoding = conn.execute(
            "SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()").fetchone()[0]
        if encoding == "UTF8":
            ok(8, "codificacao: UTF8")
        else:
            warn(8, f"codificacao: o banco usa {encoding}, nao UTF8; textos com caracteres que nao existem "
                    "nessa codificacao (ex.: emojis) vao dar erro ao salvar")
            tip(f"se o banco ainda esta vazio, recrie-o em UTF-8: CREATE DATABASE {ident(db)} "
                "ENCODING 'UTF8' TEMPLATE template0;")

    print("[ok]          PostgreSQL pronto para o migrate", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
