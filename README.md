# Demo: migração de customizações Protheus (ADVPL) com o Devin

> Rede Clínica Exemplo: empresa, pacientes, médicos, convênios e valores **fictícios**.
> Não há dado pessoal real. As regras fiscais são simplificadas para a demo.

Uma rede de clínicas tem 15 anos de customizações ADVPL no Protheus. Antes de migrar de ERP, essas rotinas
precisam virar serviços modernos sem mudar nenhum centavo do resultado. Esta demo mostra o Devin entendendo
o legado, migrando três rotinas representativas e provando a paridade contra as saídas do Protheus.

## Estrutura

```
legacy/
  advpl/               rotinas ADVPL originais
    FATCONV.prw          lote de faturamento de convênio + regras de glosa
    REPMED.prw           repasse médico (PJ) + retenções IRRF/CSRF/ISS
    ZAGEFIN.prw          ponto de entrada: títulos a receber de particulares (PIX/cartão/boleto)
  dicionario/          extrato do SX2/SX3
  dados/               extração das tabelas de entrada (SA1, SZ1..SZ4), competência 08/2026
  saidas_referencia/   o que o Protheus gravou (SZ5..SZ8, SE1, SE2), usado na conciliação
docs/
  DEMO.md                    roteiro da demo (Ask Devin → Ask Devin → sessão Devin)
  playbook-migracao-advpl.md playbook reutilizável de migração
```

A branch `demo/migracao-concluida` tem a migração pronta (`servicos/` + `tests/`), como backup da demo ao vivo.

## Rodar

```bash
pip install -r requirements.txt
pytest            # na branch demo/migracao-concluida
ruff check . && ruff format --check .
```
