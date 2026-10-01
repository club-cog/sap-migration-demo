# AGENTS.md

- Python 3.10+. Instalar com `pip install -r requirements.txt`.
- Testes: `pytest`. Lint: `ruff check . && ruff format --check .`.
- Valores monetários sempre em `Decimal`. Nunca registrar CPF, nome de paciente ou CNPJ em log.
- `legacy/` é somente leitura: é a referência do Protheus.
- Para migrar uma rotina, siga `docs/playbook-migracao-advpl.md`.
