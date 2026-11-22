# Changelog do plugin setup

Todas as mudanças do plugin `setup` são registradas aqui. A versão segue o [versionamento semântico](https://semver.org/lang/pt-BR/):

- **MAIOR** (2.0.0): muda o que já existia (ex.: renomear uma skill, mudar a estrutura do projeto gerado).
- **MENOR** (1.1.0): acrescenta algo sem quebrar o que existe (ex.: uma skill nova, um teste novo).
- **CORREÇÃO** (1.0.1): corrige um erro sem mudar o comportamento esperado.

## [1.0.0] - 2026-11-22

Primeira versão publicada.

### Skill `django` (`/setup:django`)

Faz o setup inicial de um projeto Django no diretório atual:

- Ambiente virtual `.venv` com Python 3.12 ou mais novo. Um `.venv` copiado ou movido de outra pasta é detectado e recriado.
- Django 6, `psycopg` e `python-dotenv`, com as versões fixadas no `requirements.txt`.
- `.env.example` e `.env` com uma `DJANGO_SECRET_KEY` aleatória. As variáveis são validadas antes de criar qualquer coisa, e as definidas no ambiente do sistema valem mais que o `.env`.
- Banco escolhido pela `DJANGO_DB_ENGINE`: PostgreSQL já existente (sem Docker) ou SQLite.
- Com PostgreSQL, 8 testes de conexão (endereço, porta, login, banco, acesso, versão, permissão para criar tabelas e codificação), com uma dica em pt-BR para cada falha. O `migrate` só roda se todos passarem.
- `.gitignore` e repositório git (branch `main`).
- Projeto Django `core`: `settings.py` lendo o `.env`, em pt-BR e no fuso `America/Sao_Paulo`, com `STATIC_ROOT` para o `collectstatic`.
- Estrutura do frontend em HTML, CSS e JavaScript puros (`templates/base.html`, `static/css/style.css`, `static/js/app.js`). Sem página inicial: o `runserver` mostra a página padrão do Django.
- Pode ser rodado de novo com segurança: nunca sobrescreve o que já existe.
