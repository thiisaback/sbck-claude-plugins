"""Cria o .env a partir do .env.example, com uma DJANGO_SECRET_KEY aleatória.

Uso (a partir da raiz do projeto):
    python <pasta da skill>/scripts/make_env.py

- Se o .env não existir: copia o .env.example e gera a DJANGO_SECRET_KEY. As credenciais do
  PostgreSQL (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD) ficam em branco para o usuário
  preencher no editor; a senha nunca passa pelo chat.
- Se o .env já existir: não altera nenhum valor; só acrescenta no fim as variáveis do modelo
  que estiverem faltando, para projetos criados por versões antigas da skill.
- DJANGO_DB_ENGINE escolhe o banco: postgres (padrão) ou sqlite. Com postgres, avisa quais
  credenciais ainda estão em branco; com sqlite, não precisa de credenciais.
- Os avisos consideram os valores que o Django vai usar: variáveis definidas no ambiente do
  sistema valem mais que o .env (veja check_env.py, que também valida os valores).
- Se o .env.example existir mas não tiver alguma variável do modelo, apenas avisa.

Só usa a biblioteca padrão do Python (roda antes de o pip instalar qualquer coisa).
As mensagens para o usuário são em pt-BR.
"""

import secrets
import sys

sys.dont_write_bytecode = True   # não cria __pycache__ dentro da pasta da skill ao importar o check_env
from check_env import (  # noqa: E402
    ENV, EXAMPLE, REQUIRED_DB, TEMPLATE, db_engine, effective_env, read_vars, validate, var_pattern,
)

SECRET_LINE = var_pattern("DJANGO_SECRET_KEY")


def main() -> int:
    model = read_vars(TEMPLATE)
    # token_urlsafe só usa letras, números, '-' e '_': seguro no .env
    secret = secrets.token_urlsafe(50)

    if EXAMPLE.exists():
        missing = [k for k in model if k not in read_vars(EXAMPLE)]
        if missing:
            print(f"[aviso]       .env.example nao tem: {', '.join(missing)} (veja o modelo da skill)")

    created = not ENV.exists()
    if created:
        source = EXAMPLE if EXAMPLE.exists() else TEMPLATE
        text = source.read_text(encoding="utf-8")
        text = SECRET_LINE.sub(f"DJANGO_SECRET_KEY={secret}", text, count=1)
        ENV.write_text(text, encoding="utf-8", newline="\n")

    # Completa o .env com as variáveis do modelo que faltarem (ex.: .env ou .env.example de uma versão antiga).
    # Valores que já existem nunca são trocados.
    current = ENV.read_text(encoding="utf-8")
    missing = [k for k in model if k not in read_vars(ENV)]
    if missing:
        lines = [f"{k}={secret if k == 'DJANGO_SECRET_KEY' else model[k]}" for k in missing]
        sep = "" if current.endswith("\n") or not current else "\n"
        ENV.write_text(current + sep + "\n# Adicionado pelo setup:django\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # A DJANGO_SECRET_KEY é a única variável que não pode ficar vazia nem com o valor de exemplo
    # (ex.: .env copiado à mão do .env.example): nesse caso é trocada por uma aleatória.
    key = read_vars(ENV).get("DJANGO_SECRET_KEY", "")
    regenerated = key in ("", model["DJANGO_SECRET_KEY"])
    if regenerated:
        text = ENV.read_text(encoding="utf-8")
        ENV.write_text(SECRET_LINE.sub(f"DJANGO_SECRET_KEY={secret}", text, count=1), encoding="utf-8", newline="\n")

    if created:
        print("[criado]      .env (DJANGO_SECRET_KEY aleatoria)")
    elif missing:
        print(f"[configurado] .env ja existia; adicionei: {', '.join(missing)}")
    else:
        print("[ja existia]  .env")
    if regenerated and not created:
        print("[configurado] .env: DJANGO_SECRET_KEY estava vazia ou com o valor de exemplo; gerei uma aleatoria")

    # Avisos com os valores que o Django vai usar (ambiente do sistema > .env)
    env_vars, from_os = effective_env()
    for key, problem in validate(env_vars, from_os):
        print(f"[aviso]       {key}: {problem}")
    if db_engine(env_vars) == "postgres":
        blank = [k for k in REQUIRED_DB if not env_vars.get(k)]
        if blank:
            print(f"[aviso]       preencha no .env as credenciais do PostgreSQL: {', '.join(blank)}"
                  " (ou use DJANGO_DB_ENGINE=sqlite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
