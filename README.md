# sbck-claude-plugins

Marketplace de plugins para o [Claude Code](https://claude.com/claude-code), com skills e agents em português do Brasil.

## Plugins

| Plugin | Skills | Agents | O que faz |
|---|---|---|---|
| [setup](plugins/setup) | [django](plugins/setup/skills/django/SKILL.md) | — | Setup inicial de projetos. `/setup:django`: projeto Django com `.venv`, PostgreSQL ou SQLite e git. |

## Instalar

No terminal (ou com `/plugin ...` dentro de uma sessão do Claude Code):

```
claude plugin marketplace add <usuario-do-github>/sbck-claude-plugins
claude plugin install setup@sbck-claude-plugins
```

Depois, use a skill com `/setup:django`. As skills de plugin levam o nome do plugin na frente.

Para receber as atualizações:

```
claude plugin marketplace update sbck-claude-plugins
claude plugin update setup@sbck-claude-plugins
```

Quem instala recebe uma versão nova só quando a `version` do plugin muda (veja **Versões**). O repositório pode ser privado; o Claude Code usa as credenciais de git da máquina (ex.: `gh auth login` e `gh auth setup-git`).

Para fixar uma máquina numa versão, adicione o marketplace apontando para a tag: `claude plugin marketplace add <usuario-do-github>/sbck-claude-plugins@setup-v1.0.0`.

## Versões

Cada plugin tem a sua versão no `plugins/<plugin>/.claude-plugin/plugin.json`, no padrão `MAIOR.MENOR.CORREÇÃO`, e um `CHANGELOG.md` com o que mudou em cada uma. As skills e os agents têm a versão do plugin em que estão.

| Plugin | Versão | Changelog |
|---|---|---|
| setup | 1.0.0 | [CHANGELOG](plugins/setup/CHANGELOG.md) |

Para publicar uma versão:

1. Aumente a `version` no `plugin.json` do plugin:
   - **MAIOR**: muda o que já existia;
   - **MENOR**: acrescenta algo;
   - **CORREÇÃO**: corrige um erro.
2. Registre a mudança no `CHANGELOG.md` do plugin e atualize a tabela acima.
3. Rode `claude plugin validate .`, faça o commit e crie a tag `<plugin>-v<versão>`, por exemplo `git tag setup-v1.1.0`.
4. `git push` e `git push --tags`.

## Estrutura

```
.claude-plugin/
└── marketplace.json            catálogo: lista os plugins deste repositório
plugins/
└── <plugin>/                   um plugin por tema (é o que o usuário instala)
    ├── .claude-plugin/
    │   └── plugin.json         nome, versão e descrição do plugin
    ├── CHANGELOG.md            o que mudou em cada versão
    ├── skills/
    │   └── <skill>/SKILL.md    cada skill, com seus scripts e templates
    └── agents/
        └── <agent>.md          subagents do plugin
scripts/
└── build.py                    gera dist/<skill>.zip, para usar uma skill no claude.ai
sandbox/                        pasta para testar as skills (ignorada pelo git)
dist/                           zips gerados (ignorada pelo git)
```

Testes e ferramentas de desenvolvimento ficam **fora** de `plugins/`: a pasta inteira de um plugin é copiada para quem o instala.

## Desenvolver

- **Validar** o marketplace e os plugins: `claude plugin validate .`
- **Testar um plugin sem instalar:** `claude --plugin-dir plugins/setup`, que abre uma sessão com o plugin carregado direto desta pasta.
- **Testar o setup da skill `django`** numa pasta de teste, **nunca na raiz deste repositório**:

  ```powershell
  New-Item -ItemType Directory -Force sandbox\teste; cd sandbox\teste
  py -3.12 ..\..\plugins\setup\skills\django\scripts\setup.py
  ```

  Com `$env:DJANGO_DB_ENGINE = 'sqlite'` dá para testar o setup completo sem um PostgreSQL. Para recomeçar do zero, apague a pasta `sandbox\teste`.

### Adicionar uma skill ou um agent

- **Num plugin existente:** crie `plugins/<plugin>/skills/<skill>/SKILL.md` ou `plugins/<plugin>/agents/<agent>.md`.
- **Num plugin novo:**
  1. Crie `plugins/<plugin>/.claude-plugin/plugin.json` (só o `name` é obrigatório).
  2. Acrescente o plugin em `plugins` no `.claude-plugin/marketplace.json`, com `"source": "./plugins/<plugin>"`.
  3. Rode `claude plugin validate .`.

## Usar uma skill no claude.ai (opcional)

O claude.ai aceita só skills (não agents), enviadas como zip:

```
python scripts/build.py <skill>
```

Suba o `dist/<skill>.zip` nas configurações de Skills do claude.ai. Uma skill instalada pelos dois caminhos aparece duas vezes no Claude Code (`/<skill>` e `/<plugin>:<skill>`). Por isso, prefira o plugin para skills que só fazem sentido no Claude Code, como a `django` (`/setup:django`), que roda scripts no seu computador.

## Requisitos

- Claude Code.
- Python 3.12 ou mais novo, para a skill `django`, que instala o Django 6.
- Git.
