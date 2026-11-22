# sbck-claude-plugins

Marketplace de plugins do Claude Code com as skills e os agents do usuário. Fale com o usuário em **português do Brasil**.

## Estrutura

- `.claude-plugin/marketplace.json`: catálogo dos plugins. Todo plugin novo precisa entrar aqui (`"source": "./plugins/<plugin>"`).
- `plugins/<plugin>/`: um plugin por tema, com `.claude-plugin/plugin.json`, `skills/<skill>/SKILL.md` e `agents/<agent>.md`.
- Testes e ferramentas de desenvolvimento ficam **fora** de `plugins/`: a pasta do plugin é copiada inteira para quem o instala.
- **Versão:** cada plugin tem `version` (semver) no `plugin.json` (nunca também no `marketplace.json`) e um `CHANGELOG.md` em `plugins/<plugin>/`. Quem instala só recebe uma mudança quando a `version` aumenta.
- **Toda mudança em `plugins/<plugin>/` precisa de:**
  - uma versão nova no `plugin.json` (MAIOR muda o que existia, MENOR acrescenta, CORREÇÃO corrige);
  - uma entrada no `CHANGELOG.md` do plugin;
  - a versão atualizada na tabela **Versões** do `README.md`.

  Junte várias mudanças da mesma sessão numa só versão. Ao publicar, crie a tag `<plugin>-v<versão>` (ex.: `setup-v1.1.0`), mas só quando o usuário pedir o commit.
- Depois de mudar qualquer `plugin.json` ou o `marketplace.json`, rode `claude plugin validate .` e confira se termina com `Validation passed`.

## Onde editar

- Edite sempre aqui, em `plugins/`.
- **Não edite** `~/.claude/skills/synced/` (cópia das skills da conta do claude.ai) nem o cache de plugins do Claude Code: as alterações se perdem.
- Skills de plugin são chamadas com o nome do plugin na frente (ex.: `/setup:django`).
- O zip para o claude.ai (`python scripts/build.py <skill>`) só é preciso para usar uma skill no chat do claude.ai.

## Como testar

- **Nunca rode o `setup.py` de uma skill na raiz deste repositório**: ele cria `.venv`, `.env`, `manage.py`, `core/`, `.git`... Use uma pasta dentro de `sandbox/` (ignorada pelo git) ou uma pasta temporária.
- Rode os scripts com `py -3.12 -B` (o `-B` evita criar `__pycache__` dentro da skill).
- Com `DJANGO_DB_ENGINE=sqlite` no ambiente, o setup do Django roda completo sem PostgreSQL.
- Depois de alterar, teste também uma segunda execução na mesma pasta: o setup tem de ser idempotente.
- Para testar o PostgreSQL sem instalá-lo: `pip install pgserver` num `.venv` separado dentro de `sandbox/`. O PostgreSQL do `pgserver` vem sem a pasta `share/postgresql/timezone`: copie para lá o `zoneinfo` do pacote `tzdata`, senão o `migrate` falha com `TimeZone "UTC"`.

## Convenções da skill django (`/setup:django`)

- Faz só o setup do Django, sem menu: o `SKILL.md` tem as instruções completas, e os scripts e templates ficam em `scripts/` e `templates/`, ao lado dele.
- Tudo o que o usuário lê é em pt-BR. A saída dos scripts é só em ASCII (o console do Windows nem sempre exibe acentos), com os marcadores `[criado]`, `[ja existia]`, `[ok]`, `[aviso]`, `[erro]`, `[configurado]` e `[removido]`.
- Os scripts só usam a biblioteca padrão do Python e funcionam no Windows, no Linux e no macOS.
- Nunca sobrescrever o que já existe; rodar de novo tem de ser seguro.
- Templates que começam com ponto ficam salvos sem o ponto (`gitignore`, `env.example`).
- Sem Docker. O banco é um PostgreSQL já existente ou o SQLite (`DJANGO_DB_ENGINE`). A senha do banco nunca passa pelo chat.
- Python 3.12+ e Django 6.0+.
- Não cria `CLAUDE.md` nem nada de Spec Driven Development (isso vai para skills próprias).
- Ao mudar o comportamento de um script, atualize também o `SKILL.md`.
