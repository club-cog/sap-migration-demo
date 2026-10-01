# Playbook: migração de customização ADVPL (Protheus) para serviço Python

> Playbook reutilizável. Uma sessão do Devin migra **uma** rotina por vez; uma frota de sessões
> executa o mesmo playbook em paralelo sobre o inventário de customizações.

## Entradas

- Rotina ADVPL em `legacy/advpl/<ROTINA>.prw`
- Dicionário de dados em `legacy/dicionario/SX3_tabelas.md`
- Extração das tabelas de entrada em `legacy/dados/`
- Saídas de referência do Protheus em `legacy/saidas_referencia/` (o que o legado gravou para a competência 08/2026)

## Escopo

| Origem (Protheus) | Destino (Python) |
|---|---|
| `User Function` de processamento (FATCONV, REPMED) | Função de serviço pura em `servicos/` |
| Ponto de entrada (ZAGEFIN) | Função de serviço + endpoint REST |
| `Pergunte()` / `MV_PARxx` | Parâmetros da função / query string |
| `DbSeek` / `While !Eof()` | Dicionários em memória / list comprehension |
| `RecLock` + gravação SZx/SEx | Dataclass de saída (`servicos/modelos.py`) |
| `Round(x, 2)` | `Decimal.quantize(ROUND_HALF_UP)` |
| `NoRound(x, 2)` | `Decimal.quantize(ROUND_DOWN)` |
| `DataValida(d, .T.)` | Próximo dia útil |
| `MsgStop` / `Return .F.` | Exceção ou retorno tipado |
| `ConOut` com dado pessoal | `logging` **sem** CPF/nome (LGPD) |

**Fora do escopo:** configuração funcional do ERP de destino, desenho de processo, parametrização fiscal.

## Procedimento

1. **Analisar a rotina.** Listar parâmetros, tabelas lidas e gravadas, cada regra de negócio (inclusive as
   "escondidas" em `If` com código fixo e comentários de chamado), arredondamentos e tratamento de erro.
   Registrar no PR uma tabela "regra legada → onde ficou no Python".
2. **Modelar.** Criar ou reutilizar dataclasses em `servicos/modelos.py`. Usar `Decimal`, nunca `float`.
3. **Implementar.** Um módulo por rotina em `servicos/`, com constantes nomeadas para cada regra fixa
   (ex.: `LIMITE_ALTO_CUSTO`), citando o chamado/aditivo de origem.
4. **Preservar o comportamento**, inclusive o que parece estranho (ex.: ISS truncado). Se algo parecer bug,
   **não corrigir**: listar em "Pontos para o negócio validar" no PR.
5. **Testes de paridade.** Gerar as saídas no layout das tabelas do Protheus e comparar campo a campo com
   `legacy/saidas_referencia/`. A migração só está pronta com 100% de paridade.
6. **Testes de regra.** Um teste por regra de negócio identificada no passo 1.
7. **LGPD.** Nenhum log, exceção ou resposta de API pode expor CPF, nome de paciente ou CNPJ.
8. **Qualidade.** `ruff check .`, `ruff format --check .` e `pytest` verdes.
9. **PR.** Abrir PR com: resumo, tabela de rastreabilidade, resultado da conciliação, pontos para o negócio validar.

## Critérios de aceite

- [ ] Paridade 100% com `legacy/saidas_referencia/`
- [ ] Toda regra do legado coberta por teste e rastreável no PR
- [ ] Nenhum dado pessoal em log
- [ ] Lint e testes verdes
