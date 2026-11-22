"""setup:django — script único (Windows, Linux e macOS).

Uso (a partir da raiz do projeto, com o Python do sistema):
    python  <pasta da skill>/scripts/setup.py   (Windows: python ou py)
    python3 <pasta da skill>/scripts/setup.py   (Linux/macOS)

- Pode ser rodado mais de uma vez: nunca sobrescreve nada que já exista.
- Só usa a biblioteca padrão. Cria o .venv e, dali em diante, chama o Python do .venv
  diretamente (não precisa ativar o ambiente).
- Antes de criar qualquer coisa, valida as variáveis de ambiente (check_env.py); se algum
  valor for inválido, para sem criar nada.
- Variáveis definidas no ambiente do sistema valem mais que o .env, como no settings.py.
- Um .venv copiado ou movido de outra pasta (o activate aponta para lá) é recriado nesta pasta,
  e os pacotes voltam pelo requirements.txt.
- O banco é escolhido por DJANGO_DB_ENGINE no .env: postgres (padrão) ou sqlite.
- Com sqlite, o migrate roda direto (arquivo db.sqlite3, sem credenciais).
- Com postgres, nada é instalado nem sobe em container: o usuário preenche no .env as
  credenciais de um servidor já existente. Com o .env completo, o script testa a conexão passo
  a passo (check_db.py) e roda o migrate; senão, avisa o que falta. Depois de preencher, basta rodar o script de novo.
- Não cria página inicial: o runserver mostra a página padrão do Django em /.
- Mensagens para o usuário em pt-BR, só com caracteres ASCII (o console do Windows nem sempre
  exibe acentos corretamente).
"""

import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

SETUP_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SETUP_DIR / "scripts"
T = SETUP_DIR / "templates"
ROOT = Path.cwd()

sys.dont_write_bytecode = True   # não cria __pycache__ dentro da pasta da skill
sys.path.insert(0, str(SCRIPTS))
import check_env  # noqa: E402
from check_env import REQUIRED_DB, db_engine, effective_env  # noqa: E402

# Versão mínima do Python: a exigida pelo Django 6 (a do Django fica em install_deps.py)
MIN_PYTHON = (3, 12)
MIN_PYTHON_STR = ".".join(map(str, MIN_PYTHON))

# Evita erro ao imprimir caminhos com caracteres especiais em consoles com codificação limitada,
# e grava linha a linha para a saída não se misturar com a do pip quando for para um arquivo
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace", line_buffering=True)
    except (AttributeError, ValueError):
        pass


def created(m): print(f"[criado]      {m}", flush=True)
def exists(m):  print(f"[ja existia]  {m}", flush=True)
def warn(m):    print(f"[aviso]       {m}", flush=True)
def step(m):    print(f"\n== {m}", flush=True)


def run(cmd, check=True, capture=False, env=None):
    """Roda um comando. check=True interrompe o setup se falhar. Devolve o CompletedProcess."""
    kwargs = {"cwd": ROOT}
    if env:
        kwargs["env"] = {**os.environ, **env}
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    result = subprocess.run([str(c) for c in cmd], **kwargs)
    if check and result.returncode != 0:
        sys.exit(f"falhou: {' '.join(str(c) for c in cmd)}")
    return result


def copy_template(template, dest):
    """Copia um template sem sobrescrever. Os templates com ponto ficam salvos sem ele
    (ex.: gitignore -> .gitignore), porque arquivos ocultos podem se perder ao sincronizar a skill."""
    dest = Path(dest)
    if dest.exists():
        exists(dest.as_posix())
    else:
        shutil.copyfile(T / template, dest)
        created(dest.as_posix())


VENV = ROOT / ".venv"

# Caminho gravado no activate quando o .venv foi criado, ex.: VIRTUAL_ENV='C:\proj\.venv',
# VIRTUAL_ENV="/home/eu/proj/.venv" ou, no Git Bash, VIRTUAL_ENV=$(cygpath 'C:\proj\.venv')
ACTIVATE_PATH = re.compile(r"""^\s*(?:export\s+)?VIRTUAL_ENV=(?:\$\(cygpath\s+)?(["'])(.+?)\1""", re.MULTILINE)
# Linha do pyvenv.cfg (Python 3.11+): command = <python> -m venv [--opcoes] <caminho do .venv>
CFG_COMMAND = re.compile(r"^command\s*=.*?\s-m\s+venv\s+(?:--\S+\s+)*(.+?)\s*$", re.MULTILINE)


def venv_python(venv=VENV):
    win = venv / "Scripts" / "python.exe"
    return win if win.exists() else venv / "bin" / "python"


def venv_created_for(venv):
    """Pasta para a qual o .venv foi criado (lida do activate ou do pyvenv.cfg), ou None se não der
    para saber. Um .venv não pode ser copiado nem movido: o activate e os executáveis (pip,
    django-admin) guardam o caminho absoluto de onde ele foi criado."""
    for script in (venv / "Scripts" / "activate", venv / "bin" / "activate"):
        if script.exists():
            m = ACTIVATE_PATH.search(script.read_text(encoding="utf-8", errors="replace"))
            if m:
                return m.group(2)
    cfg = venv / "pyvenv.cfg"
    if cfg.exists():
        m = CFG_COMMAND.search(cfg.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return None


def foreign_venv(venv):
    """Se o .venv foi criado para outra pasta (copiado ou movido), devolve essa pasta; senão, None."""
    if not venv.is_dir():
        return None
    origin = venv_created_for(venv)
    if origin is None:
        return None
    same = os.path.normcase(os.path.realpath(origin)) == os.path.normcase(os.path.realpath(venv))
    return None if same else origin


def installed_packages(py):
    """Nomes (normalizados) dos pacotes instalados num .venv, pelo pip freeze. Vazio se não der para ler."""
    if not Path(py).exists():
        return set()
    result = run([py, "-m", "pip", "freeze"], check=False, capture=True)
    if result.returncode != 0:
        return set()
    names = set()
    for line in result.stdout.splitlines():
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", line.strip())
        if m:
            names.add(re.sub(r"[-_.]+", "-", m.group(1)).lower())
    return names


def remove_tree(path):
    """Apaga uma pasta. Devolve False se algum arquivo não pôde ser apagado (ex.: em uso)."""
    def retry_writable(func, p, _exc):
        # No Windows, arquivos somente leitura não são apagados sem tirar o atributo antes
        os.chmod(p, stat.S_IWRITE)
        func(p)

    try:
        shutil.rmtree(path, onexc=retry_writable)
        return True
    except OSError:
        return False


def remove_old_venv(venv):
    """Tira o .venv antigo do caminho e apaga. Primeiro renomeia, para o .venv novo poder ser criado
    mesmo que algum arquivo do antigo esteja em uso e não possa ser apagado agora (a sobra é apagada
    numa próxima execução, por clean_old_venvs)."""
    old = venv.with_name(f".venv-antigo-{int(time.time())}")
    try:
        venv.rename(old)
    except OSError as e:
        sys.exit(f"falhou: nao consegui mover o .venv antigo ({e.strerror or e}). Feche o que estiver usando o "
                 ".venv (terminal com o ambiente ativo, VS Code, runserver) e rode o setup de novo. Nada foi apagado.")
    if remove_tree(old):
        print("[removido]    .venv/ antigo", flush=True)
    else:
        warn(f"nao consegui apagar {old.name}/ por completo (algum arquivo em uso). Ela nao e mais usada; "
             "o setup tenta apagar de novo na proxima execucao, ou apague a mao.")


def clean_old_venvs():
    """Apaga sobras de .venv antigos que não puderam ser apagadas numa execução anterior."""
    for old in sorted(ROOT.glob(".venv-antigo-*")):
        if old.is_dir():
            if remove_tree(old):
                print(f"[removido]    {old.name}/ (sobra de um .venv antigo)", flush=True)
            else:
                warn(f"{old.name}/ ainda esta em uso; feche o que estiver usando e apague a mao, ou rode o setup de novo")


def main():
    # 1. Raiz do projeto
    step(f"Raiz do projeto: {ROOT}")
    if not (ROOT / "manage.py").exists():
        warn("manage.py nao encontrado; usando o diretorio atual como raiz")

    # .venv copiado ou movido de outra pasta: será recriado aqui (passo 2)
    moved_from = foreign_venv(VENV)

    # Versão mínima do Python, conferida antes de criar qualquer coisa. Se o .venv já existe (e é
    # desta pasta), quem vale é o Python dele (conferido no passo 3), não o que roda este script.
    if (moved_from or not VENV.is_dir()) and sys.version_info < MIN_PYTHON:
        sys.exit(f"falhou: Python {sys.version.split()[0]} em {sys.executable}; o minimo e {MIN_PYTHON_STR} "
                 f"(exigido pelo Django 6). Instale o Python {MIN_PYTHON_STR}+ e rode o setup com ele "
                 f"(Windows: py -{MIN_PYTHON_STR} <setup.py>).")

    # Variáveis de ambiente, validadas antes de criar qualquer coisa. Se o .env ainda não existe,
    # valida o arquivo de onde ele será criado (.env.example ou o modelo da skill).
    step("Validacao das variaveis de ambiente")
    if check_env.check()[2]:
        sys.exit("falhou: corrija as variaveis acima (onde indicado entre parenteses) e rode o setup de novo. "
                 "Nada foi criado nem alterado nesta execucao.")

    # 2. Ambiente virtual (com o mesmo Python que está rodando este script)
    # Um .venv copiado ou movido de outra pasta é recriado aqui: o activate, o pip e o django-admin
    # dele apontam para a pasta antiga. Os pacotes voltam pelo requirements.txt (passo 5).
    step("Ambiente virtual")
    clean_old_venvs()
    old_packages = set()
    if moved_from:
        warn(f".venv foi criado para outra pasta ({moved_from}): o activate, o pip e o django-admin "
             "apontam para la. Vou recria-lo nesta pasta.")
        old_packages = installed_packages(venv_python())
        remove_old_venv(VENV)
    if VENV.is_dir():
        exists(".venv/")
    else:
        run([sys.executable, "-m", "venv", ".venv"])
        created(f".venv/ (com {sys.executable})")

    # 3. Daqui em diante usa o Python do .venv diretamente (equivale a ativar o ambiente)
    py = venv_python()
    if not py.exists():
        sys.exit("falhou: Python do .venv nao encontrado")
    run([py, "-c", "import sys; print('sys.prefix =', sys.prefix)"])
    venv_version = run([py, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"], capture=True).stdout.strip()
    if tuple(int(n) for n in venv_version.split(".")[:2]) < MIN_PYTHON:
        sys.exit(f"falhou: o .venv usa Python {venv_version}; o minimo e {MIN_PYTHON_STR} (exigido pelo Django 6). "
                 f"Apague a pasta .venv e rode o setup de novo com Python {MIN_PYTHON_STR}+.")
    print(f"[ok]          Python {venv_version} no .venv (minimo {MIN_PYTHON_STR})")

    # 4. Variáveis de ambiente: DJANGO_SECRET_KEY aleatória e credenciais do PostgreSQL para preencher
    step("Variaveis de ambiente (.env)")
    copy_template("env.example", ".env.example")
    run([py, SCRIPTS / "make_env.py"])

    # 5. Django + psycopg + python-dotenv
    step("Django, psycopg e python-dotenv")
    run([py, SCRIPTS / "install_deps.py"])
    if old_packages:
        missing = sorted(old_packages - installed_packages(py))
        if missing:
            warn(f"o .venv antigo tinha pacotes que nao estao no requirements.txt: {', '.join(missing)}. "
                 "Se o projeto usa algum, adicione ao requirements.txt e rode o setup de novo.")

    # 6. Git
    step("Git")
    if Path(".gitignore").exists():
        exists(".gitignore (confira se ignora .venv/ e .env)")
    else:
        copy_template("gitignore", ".gitignore")
    if not shutil.which("git"):
        warn("git nao encontrado; pulei o git init")
    else:
        if Path(".git").is_dir():
            exists(".git/")
        else:
            run(["git", "init", "-b", "main", "-q"])
            created(".git/ (branch main)")
        # Confere um por um (o check-ignore com vários caminhos dá sucesso se só um deles for ignorado)
        not_ignored = [p for p in (".venv", ".env")
                       if run(["git", "check-ignore", "-q", p], check=False).returncode != 0]
        if not_ignored:
            warn(f"{' e '.join(not_ignored)} NAO {'esta' if len(not_ignored) == 1 else 'estao'} ignorado(s) pelo git; "
                 "adicione ao .gitignore")
        else:
            print("[ok]          .venv e .env ignorados pelo git", flush=True)

    # 7. Projeto Django + frontend (HTML, CSS e JS puros)
    step("Projeto Django")
    if Path("manage.py").exists() or Path("core").exists():
        exists("manage.py / core/ (startproject nao executado)")
    else:
        run([py, "-m", "django", "startproject", "core", "."])
        created("manage.py e core/")
    step("Frontend (HTML, CSS e JavaScript)")
    run([py, SCRIPTS / "configure_frontend.py"])

    # 8. settings.py (.env, banco, idioma e fuso); se o banco estiver pronto, testa a conexão e migra
    # Mesmos valores que o Django vai usar: ambiente do sistema > .env (já validados no início)
    env_vars, from_os = effective_env()
    engine = db_engine(env_vars)
    engine_origin = "no ambiente do sistema" if "DJANGO_DB_ENGINE" in from_os else "no .env"
    step("settings.py")
    run([py, SCRIPTS / "configure_settings.py", "core/settings.py"])
    run([py, "manage.py", "check"])
    db_ok = False
    blank = []
    step(f"Banco de dados ({'SQLite' if engine == 'sqlite' else 'PostgreSQL'}, DJANGO_DB_ENGINE={engine})")
    if engine == "sqlite":
        print("SQLite: banco no arquivo db.sqlite3 (nao precisa de credenciais)")
        db_ok = True
    elif blank := [k for k in REQUIRED_DB if not env_vars.get(k)]:
        # O make_env.py já listou as variáveis em branco
        warn("conexao e migrate pulados: preencha o .env e rode este setup de novo")
    else:
        # Testes de conexão passo a passo (rede, login, banco, acesso, versão, permissão, codificação),
        # com uma dica para cada falha; o migrate só roda se todos passarem
        db_ok = run([py, SCRIPTS / "check_db.py"], check=False).returncode == 0
        if not db_ok:
            warn("migrate pulado: resolva o problema acima e rode este setup de novo")
    if db_ok:
        step("Migracoes")
        if run([py, "manage.py", "migrate", "--noinput"], check=False).returncode == 0:
            print("[configurado] migracoes aplicadas (python manage.py migrate)")
        else:
            warn("o migrate falhou; veja a saida acima")
    # Com PostgreSQL, apaga um db.sqlite3 vazio deixado pelo Django (nunca um com dados)
    sqlite = Path("db.sqlite3")
    if engine == "postgres" and sqlite.exists() and sqlite.stat().st_size == 0:
        sqlite.unlink()
        print("[removido]    db.sqlite3 vazio (o projeto usa PostgreSQL)")

    if shutil.which("git"):
        step("git status")
        run(["git", "status", "--short"], check=False)

    step("Concluido")
    print("Ativar o ambiente: PowerShell .venv\\Scripts\\Activate.ps1 | Git Bash source .venv/Scripts/activate | Linux/macOS source .venv/bin/activate")
    print("Rodar o projeto: python manage.py runserver  (nao use django-admin runserver)")
    print(f"Banco: DJANGO_DB_ENGINE={engine} {engine_origin} (troque para postgres ou sqlite e rode este setup de novo)")
    if blank:
        print("Pendente: preencher as credenciais do PostgreSQL no .env (ou usar DJANGO_DB_ENGINE=sqlite) e rodar este setup de novo.")
    elif not db_ok:
        print("Pendente: conexao com o PostgreSQL (veja o teste que falhou e a dica acima); depois de resolver, rode este setup de novo.")
    print("O .env tem a SECRET_KEY e a senha do banco e nao deve ir para o git.")


if __name__ == "__main__":
    main()
