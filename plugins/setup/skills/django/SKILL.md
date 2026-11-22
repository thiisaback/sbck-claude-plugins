---
name: django
description: Faz o setup inicial de um projeto Django no diretório atual — ambiente virtual .venv, Django 6 (psycopg, python-dotenv) com o banco escolhido no .env pela DJANGO_DB_ENGINE (PostgreSQL já existente, com testes de conexão, ou SQLite; sem Docker), .gitignore, repositório git, projeto Django "core" com o settings.py lendo o .env e a estrutura do frontend em HTML, CSS e JavaScript puros. Use quando o usuário pedir para criar, configurar ou inicializar um projeto Django ("setup do Django", "criar um projeto Django", "inicializar o projeto Django") ou chamar /setup:django.
---

# setup:django

Prepara a **raiz do projeto** (o diretório de trabalho atual) com um ambiente virtual Python, Django e a estrutura do frontend em HTML, CSS e JavaScript puros. O banco é escolhido no `.env` pela `DJANGO_DB_ENGINE`: um PostgreSQL **já existente** (padrão, credenciais no `.env`) ou o SQLite padrão do Django.

O setup **não instala nem sobe** o PostgreSQL, e **não usa Docker**: o usuário informa no `.env` as credenciais de um servidor que ele já tem (instalado na máquina ou remoto).

**Fale com o usuário em português do Brasil (pt-BR)** durante todo o setup, inclusive no relatório final.

## Estrutura a criar

```
<raiz do projeto>/
├── .venv/                 (ambiente virtual Python)
├── requirements.txt       (Django + psycopg + python-dotenv, versões fixadas)
├── .env.example           (modelo das variáveis: Django e PostgreSQL)
├── .env                   (DJANGO_SECRET_KEY aleatória + credenciais do PostgreSQL a preencher)
├── .gitignore
├── .git/                  (repositório git, branch main)
├── manage.py              (django-admin startproject core .)
├── core/                  (settings.py lendo o .env; urls.py como o startproject criou)
├── templates/             (frontend: HTML com templates do Django)
│   └── base.html          (layout para as páginas estenderem: carrega style.css e app.js)
└── static/
    ├── css/style.css      (CSS puro)
    └── js/app.js          (JavaScript puro)
```

O setup **não cria** o `CLAUDE.md`, a pasta `.claude/` nem nada de Spec Driven Development (isso fica para skills próprias).

Também **não cria página inicial nem rota**: o `core/urls.py` fica como o `startproject` criou, então o `python manage.py runserver` mostra em `/` a página padrão do Django ("A instalação foi bem sucedida!", em português por causa do `LANGUAGE_CODE = 'pt-br'`). Essa página só aparece com `DJANGO_DEBUG=True` e enquanto o projeto não tiver uma rota para `/`.

## Regra geral

**Nunca sobrescreva** um arquivo ou pasta que já exista. Se existir, deixe como está e avise o usuário no relatório final.

## Como executar

Os passos 1 a 8 estão automatizados num **script Python único**, `scripts/setup.py`, que funciona igual no Windows, Linux e macOS, em qualquer shell. Rode-o **a partir da raiz do projeto**, com o Python do sistema, onde `<BASE>` é o diretório base da skill informado quando ela foi carregada ("Base directory for this skill"). A skill pode estar no projeto, na pasta do usuário ou sincronizada da conta, então use sempre o caminho absoluto, entre aspas:

```
python "<BASE>/scripts/setup.py"
```

- Use o interpretador disponível: `python` (ou `py` no Windows; `python3` no Linux/macOS). O `.venv` é criado com esse mesmo Python. Se nenhum for encontrado, avise o usuário e pare.
- **Versões mínimas: Python 3.12 e Django 6.0** (o Django 6 exige Python 3.12+). Se o `python` padrão for mais antigo e houver outro instalado, use-o (Windows: `py -3.12`, `py -3.13`...; Linux/macOS: `python3.12`...). Se não houver nenhum 3.12+, avise o usuário e pare.

Observações:

- A instalação dos pacotes pode demorar: use um timeout de pelo menos 5 minutos.
- O script pode ser rodado mais de uma vez com segurança. A saída é em pt-BR e cada item vem marcado com `[criado]`, `[ja existia]`, `[ok]`, `[aviso]`, `[erro]`, `[configurado]` ou `[removido]`. Use essa saída no relatório do passo 9.
- Se o script falhar no meio (linha `falhou: ...`), leia o erro, corrija a causa e rode de novo.
- Se a validação do início apontar `[erro]` em alguma variável, o script para **sem criar nada**. Mostre ao usuário cada variável inválida, de onde ela veio (`.env`, `.env.example` ou ambiente do sistema) e o que corrigir. Não corrija o `.env` por conta própria: peça ao usuário para ajustar e rode o setup de novo quando ele avisar.
- O `setup.py` orquestra os outros scripts da pasta (`check_env.py`, `make_env.py`, `install_deps.py`, `configure_frontend.py`, `configure_settings.py`, `check_db.py`), que também podem ser rodados sozinhos.
- Os passos abaixo descrevem o que o script faz; siga-os à mão só se ele não puder ser usado.
- Os templates que começam com ponto ficam salvos **sem o ponto** em `templates/` (`env.example`, `gitignore`), porque arquivos ocultos podem se perder ao sincronizar ou compactar a skill. Ao copiar, renomeie para `.env.example` e `.gitignore`.

## Escolha do banco: `DJANGO_DB_ENGINE`

- O `.env` tem a variável `DJANGO_DB_ENGINE`, que escolhe o banco:
  - `postgres` (padrão): PostgreSQL já existente, com as credenciais `POSTGRES_*` (veja abaixo).
  - `sqlite`: o banco padrão do Django, no arquivo `db.sqlite3` na raiz. Não precisa de credenciais, e o `setup.py` já roda o `migrate`.
- O `settings.py` lê a variável a cada execução, então o usuário pode trocar de banco a qualquer momento. Depois de trocar, rode o `setup.py` de novo (ou `python manage.py migrate`) para criar as tabelas no banco escolhido. Os dados **não** são copiados de um banco para o outro.
- Vazia ou ausente, vale `postgres`. Um valor diferente de `postgres` e `sqlite` faz o `setup.py` parar logo no início, sem criar nada, e o Django recusa subir (`ImproperlyConfigured`).
- No relatório final, diga qual banco está em uso e que dá para trocar pela `DJANGO_DB_ENGINE`.

## Prioridade e validação das variáveis

- **Ambiente do sistema > `.env`.** O `settings.py` carrega o `.env` com `load_dotenv` sem sobrescrever: uma variável já definida no ambiente do sistema (ex.: `$env:DJANGO_DB_ENGINE` no PowerShell, `export` no Linux, variável de usuário do Windows) vale mais que a do `.env`. O `setup.py` usa a mesma regra (`check_env.effective_env()`), para o script e o Django sempre escolherem o mesmo banco e as mesmas credenciais. Quando alguma variável vem do ambiente do sistema, o script avisa no início; mencione isso no relatório.
- **Validação antes de criar qualquer coisa** (`scripts/check_env.py`). Se o `.env` ainda não existe, valida o arquivo de onde ele será criado (`.env.example`, ou o modelo da skill). Regras:
  - `DJANGO_DB_ENGINE`: `postgres` ou `sqlite` (vazia = `postgres`).
  - `DJANGO_DEBUG`: `True`/`False` (também `1`/`0`, `yes`/`no`; vazia = `False`).
  - `DJANGO_ALLOWED_HOSTS`: domínios separados por vírgula, **sem** `http://`, caminho, espaços nem porta (ex.: `localhost`, não `localhost:8000`).
  - `DJANGO_SECRET_KEY`: vazia ou com o valor de exemplo só é erro se vier do ambiente do sistema; a do `.env` o `make_env.py` troca sozinho por uma aleatória.
  - Com `postgres`: `POSTGRES_PORT` é um número de 1 a 65535; `POSTGRES_HOST` é só o endereço (sem `postgres://`, espaços ou `:porta`).
  - Credenciais do PostgreSQL **em branco não são erro**: o setup cria tudo e só pula a conexão e o `migrate` (veja abaixo).

## Credenciais do PostgreSQL

- **Nunca peça a senha do banco no chat** nem a escreva no `.env` por conta própria: o usuário preenche o `.env` no editor dele.
- Na primeira execução, o `.env` sai com `POSTGRES_HOST=127.0.0.1` e `POSTGRES_PORT=5432` (padrões de um PostgreSQL instalado na máquina) e com `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` em branco. O script avisa o que falta e pula a conexão e o `migrate`.
- No relatório final, peça ao usuário para preencher essas variáveis e lembre que o banco (`POSTGRES_DB`) precisa **já existir** no servidor.
- Quando o usuário avisar que preencheu, **rode o `setup.py` de novo**: ele não recria nada, roda os testes de conexão e, se todos passarem, o `migrate`.
- Não tente adivinhar outras credenciais.

## Testes de conexão com o PostgreSQL (`scripts/check_db.py`)

Rodados pelo `setup.py` (com o Python do `.venv`) quando `DJANGO_DB_ENGINE=postgres` e as credenciais estão preenchidas. Também podem ser rodados sozinhos, da raiz do projeto: `.venv/Scripts/python.exe "<BASE>/scripts/check_db.py"` (Linux/macOS: `.venv/bin/python`). Usam os mesmos valores que o Django (ambiente do sistema > `.env`), param no primeiro teste que falhar e mostram uma `dica:` em pt-BR. Rede e login têm limite de 5 segundos.

| # | Teste | Se falhar, o que significa |
|---|---|---|
| 1 | Endereço: o `POSTGRES_HOST` existe (DNS)? | Host digitado errado. |
| 2 | Porta: o servidor responde em `POSTGRES_HOST:POSTGRES_PORT`? | Recusou: PostgreSQL parado, porta errada ou servidor remoto aceitando só conexões locais. Sem resposta: firewall ou endereço errado. |
| 3 | Login: usuário e senha aceitos? (entra no banco `postgres` ou `template1`, que todo servidor tem) | Usuário ou senha errados, ou o `pg_hba.conf` não permite esse usuário a partir desta máquina. |
| 4 | Banco: o `POSTGRES_DB` existe? (consulta `pg_database`) | Banco não criado. A dica traz o `CREATE DATABASE` e diz se o próprio usuário pode criá-lo. |
| 5 | Acesso: o usuário conecta no `POSTGRES_DB`? | Sem permissão de `CONNECT` no banco. |
| 6 | Versão do PostgreSQL | Mais antiga que o mínimo do Django instalado (o mínimo é lido do próprio Django). |
| 7 | Tabelas: o usuário pode criar tabelas no schema? | Desde o PostgreSQL 15, só o dono do banco cria tabelas no schema `public`: o `migrate` falharia. |
| 8 | Codificação UTF8? | Só aviso: com `WIN1252`/`LATIN1`, caracteres fora da codificação (ex.: emojis) dão erro ao salvar. |

Os testes 1 a 4 não dependem do idioma do servidor (um PostgreSQL em português responde "não existe", e não "does not exist"): o diagnóstico vem da rede e de consultas, não do texto do erro.

Quando um teste falhar, mostre ao usuário qual foi, o erro e a dica. Os comandos SQL das dicas (`CREATE DATABASE`, `GRANT`, `ALTER DATABASE`) normalmente exigem um administrador do PostgreSQL: **mostre-os, mas não os rode** por conta própria. Depois que o usuário resolver, rode o `setup.py` de novo.

## Passos

1. Confirme que o diretório de trabalho atual é a raiz do projeto (ex.: onde está o `manage.py`). Se não houver `manage.py`, avise o usuário, mas continue usando o diretório atual como raiz.
   - Se o `.venv` ainda não existe, confira **antes de criar qualquer coisa** que o Python é 3.12 ou mais novo; se não for, pare sem criar nada.
   - Ainda antes de criar qualquer coisa, valide as variáveis de ambiente com `scripts/check_env.py` (veja **Prioridade e validação das variáveis**). Se houver `[erro]`, pare sem criar nada.
2. Crie o ambiente virtual Python em `.venv/`.
   - Se `.venv/` já existir e for desta pasta, **não recrie nem apague**.
   - **Exceção: `.venv` copiado ou movido de outra pasta.** Um ambiente virtual guarda o caminho absoluto de onde foi criado (no `activate` e no `pyvenv.cfg`, e dentro do `pip.exe` e do `django-admin.exe`). Se esse caminho não for o `.venv` da pasta atual, o `activate` ativaria o ambiente da outra pasta e o `pip`/`django-admin` falhariam. Nesse caso o setup:
     1. Confere, antes de criar qualquer coisa, que o Python que roda o setup é 3.12+ (é ele que vai criar o novo `.venv`).
     2. Anota os pacotes instalados no `.venv` antigo (`pip freeze`).
     3. Renomeia o `.venv` antigo para `.venv-antigo-<número>` e o apaga. Se algum arquivo estiver em uso (terminal com o ambiente ativo, VS Code, `runserver`), a pasta renomeada fica para trás com um aviso, o setup segue e tenta apagá-la de novo na próxima execução. Se nem a renomeação for possível, o setup para sem apagar nada: peça ao usuário para fechar o que estiver usando o `.venv` e rode de novo.
     4. Cria o `.venv` novo nesta pasta. Os pacotes voltam pelo `requirements.txt` no passo 5, e o script avisa quais pacotes do `.venv` antigo não estão no `requirements.txt`. Mostre esse aviso ao usuário.
   - Se não der para saber onde o `.venv` foi criado (ex.: criado por outra ferramenta, sem `activate` nem a linha `command` no `pyvenv.cfg`), ele é mantido.
   - Use o mesmo Python que roda o `setup.py` (`python -m venv .venv`).
   - Confirme o executável `.venv/Scripts/python.exe` (Windows) ou `.venv/bin/python` (Linux/macOS) e mostre a versão.
   - Se o Python do `.venv` for anterior ao 3.12 (ex.: `.venv` antigo), pare e oriente o usuário a apagar o `.venv` e rodar o setup de novo com Python 3.12+. Não apague o `.venv` por conta própria.
3. Use o Python do `.venv` em todos os passos seguintes.
   - O `setup.py` chama o executável do `.venv` diretamente, o que equivale a ativar o ambiente.
   - Confirme que `sys.prefix` aponta para `.venv`.
   - Fazendo à mão: cada comando do Claude roda em um shell novo, então a ativação **não persiste** entre comandos. Ative o ambiente no mesmo comando que o utiliza, ou chame o executável do `.venv` diretamente.
4. Crie o `.env.example` e o `.env`:
   - Copie `templates/env.example` para `.env.example` (sem sobrescrever).
   - Crie o `.env` com `scripts/make_env.py` (só biblioteca padrão do Python): copia o `.env.example` e gera uma `DJANGO_SECRET_KEY` **aleatória** (nunca use valor fixo: a chave seria igual em todo projeto). As credenciais do PostgreSQL ficam para o usuário preencher (veja **Credenciais do PostgreSQL**).
   - Se o `.env` já existir, **não troca nenhum valor**: só acrescenta no fim as variáveis do modelo que faltarem (ex.: `.env` criado por uma versão antiga da skill).
   - Única exceção: se a `DJANGO_SECRET_KEY` estiver vazia ou com o valor de exemplo do `.env.example` (`troque-por-uma-chave-aleatoria`), ela é trocada por uma aleatória. Uma chave definida pelo usuário nunca é alterada.
5. Instale no `.venv` o Django, o driver do PostgreSQL e o leitor de `.env`:
   - Feito por `scripts/install_deps.py`, rodado com o Python do `.venv`. O PostgreSQL em si não é instalado; só o driver `psycopg` vai para o venv. O `python-dotenv` permite que o Django leia o `.env`.
   - Se o `requirements.txt` **não existir**: `pip install "Django>=6.0" "psycopg[binary]" python-dotenv` e crie o arquivo com as versões instaladas fixadas (ex.: `Django==X.Y.Z`, `psycopg[binary]==X.Y.Z`, `python-dotenv==X.Y.Z`).
   - Se o `requirements.txt` **já existir**: instale por ele (`pip install -r requirements.txt`), para respeitar as versões fixadas — nunca instale as versões mais novas por cima. Se faltar nele algum dos três pacotes, instale só o que falta no `.venv`, não altere o arquivo e avise o usuário quais linhas adicionar.
   - Confira que o Django instalado é **6.0 ou mais novo**. Se o `requirements.txt` fixar uma versão anterior, pare e oriente o usuário a ajustar a linha do Django (ex.: `Django>=6.0`); não altere o arquivo por conta própria.
6. Crie o `.gitignore` e inicialize o repositório git:
   - Copie `templates/gitignore` para a raiz como `.gitignore`. Se já existir um `.gitignore`, não sobrescreva: avise o usuário e sugira as linhas que faltam (principalmente `.venv/` e `.env`).
   - Se a pasta `.git/` já existir, **não rode `git init` de novo**; apenas avise o usuário.
   - Caso contrário, rode `git init -b main`.
   - Confirme, um por um, com `git check-ignore -q`, que o `.venv` e o `.env` estão ignorados e mostre `git status --short`.
   - **Não faça commit** nem configure um remote, a não ser que o usuário peça.
7. Crie o projeto Django na raiz, com o pacote de configuração chamado `core`, e a estrutura do frontend:
    - Se `manage.py` ou a pasta `core/` já existirem, **não rode** o `startproject`; apenas avise o usuário.
    - Com o `.venv` ativo, rode `django-admin startproject core .` (o `.` cria o `manage.py` na raiz, sem pasta extra).
    - Configure a estrutura do frontend com `scripts/configure_frontend.py`. O frontend é em **HTML, CSS e JavaScript puros**, renderizado pelos templates do Django (sem React, Vue, Tailwind, Bootstrap nem frontend separado):
      - Copia, sem sobrescrever, os modelos de `templates/frontend/` para `templates/base.html` (layout para as páginas estenderem), `static/css/style.css` e `static/js/app.js`.
      - **Não** cria página inicial nem rota, e **não** altera o `core/urls.py`: em `/`, o `runserver` mostra a página padrão do Django.
      - No `core/settings.py`: `TEMPLATES` → `'DIRS': [BASE_DIR / 'templates']`, `STATICFILES_DIRS = [BASE_DIR / 'static']` e `STATIC_ROOT = BASE_DIR / 'staticfiles'`. O `STATIC_ROOT` é a pasta onde o `python manage.py collectstatic` junta todos os arquivos estáticos (do projeto e do admin) para publicar o site; sem ele, o `collectstatic` falha. Não muda nada no desenvolvimento (`runserver`). A pasta `staticfiles/` já está no `.gitignore`.
      - Cada ajuste só é feito se o arquivo ainda estiver como o `startproject` criou; se foi personalizado, deixa como está e avisa.
8. Configure o `core/settings.py` (configuração lida do `.env`, idioma e fuso do Brasil), com `scripts/configure_settings.py`, e, se as credenciais estiverem preenchidas, conecte e aplique as migrações:
    - `DATABASES` (SQLite padrão) → escolhido por `DJANGO_DB_ENGINE`: `postgres` (`django.db.backends.postgresql`, lendo `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`) ou `sqlite` (`db.sqlite3`). O bloco só-PostgreSQL gerado por versões antigas da skill também é atualizado.
    - `SECRET_KEY = 'django-insecure-...'` → `DJANGO_SECRET_KEY` do `.env`. Assim a chave sai do código e não vai para o git.
    - `DEBUG = True` → `DJANGO_DEBUG` do `.env` (se a variável não existir, o padrão é `False`).
    - `ALLOWED_HOSTS = []` → `DJANGO_ALLOWED_HOSTS` do `.env` (lista separada por vírgula). No `.env.example` ela vem **vazia**: com `DEBUG=True` o Django já aceita `localhost`, `127.0.0.1` e `[::1]`; o usuário preenche os domínios quando for publicar.
    - `LANGUAGE_CODE = 'en-us'` → `'pt-br'` e `TIME_ZONE = 'UTC'` → `'America/Sao_Paulo'` (o `USE_TZ = True` continua: o banco guarda as datas em UTC e o Django as converte para o horário de Brasília).
    - Adiciona `import os`, `from dotenv import load_dotenv` e `load_dotenv(BASE_DIR / '.env')`. Variáveis já definidas no ambiente têm prioridade sobre o `.env`.
    - Cada item só é alterado se ainda estiver como o `startproject` criou. Se já está configurado, não faz nada; se foi personalizado, deixa como está e avisa.
    - Confirme com `python manage.py check`.
    - Com `DJANGO_DB_ENGINE=sqlite`, rode o `migrate` direto (cria o `db.sqlite3`).
    - Com `postgres`, se alguma credencial estiver em branco no `.env`, pule a conexão e o `migrate` e avise o usuário.
    - Senão, rode os testes de conexão (`scripts/check_db.py`, veja **Testes de conexão com o PostgreSQL**) e, se todos passarem, rode `python manage.py migrate --noinput` para criar as tabelas iniciais (admin, usuários, sessões). Se algum falhar, pule o `migrate` e mostre ao usuário o teste, o erro e a dica.
    - Com `postgres`, se sobrar um `db.sqlite3` **vazio** (0 bytes), apague. Nunca apague um `db.sqlite3` com dados.
9. Ao terminar, informe ao usuário **em pt-BR** o que foi criado e o que já existia, e também:
    - Qual banco está em uso (`DJANGO_DB_ENGINE`) e que dá para trocar entre `postgres` e `sqlite` no `.env`.
    - Se o banco for `postgres` e as credenciais ainda não foram preenchidas: peça para preencher `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` (e conferir `POSTGRES_HOST`/`POSTGRES_PORT`) no `.env`, lembrando que o banco precisa já existir, e diga que você roda o setup de novo para testar a conexão e aplicar as migrações quando ele avisar.
    - Como ativar o ambiente: PowerShell `.venv\Scripts\Activate.ps1` · Git Bash `source .venv/Scripts/activate` · Linux/macOS `source .venv/bin/activate`.
    - Como rodar o projeto: `python manage.py runserver` e abrir http://127.0.0.1:8000/, que mostra a página padrão do Django. **Não** `django-admin runserver`, que não sabe qual é o `settings` do projeto.
    - Que o `.env` guarda a `SECRET_KEY` e a senha do banco e não deve ir para o controle de versão.
