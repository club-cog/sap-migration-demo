# Banco Exemplo - Conta Corrente (demo)

Repositório de demonstração do Devin para bancos. **Todos os dados, nomes, CPFs e regras são fictícios.**

| Pasta | O que tem |
|---|---|
| `legacy/cobol/` | Batch noturno de conta corrente em COBOL: `CCJUROS` (encargos diários do cheque especial: juros + IOF) e `CCTARIF` (pacotes e tarifas mensais), com copybooks |
| `legacy/jcl/CCBATCH.jcl` | JCL do batch (STEP010 CCJUROS, STEP020 CCTARIF) |
| `legacy/dados/` | Arquivos de entrada de largura fixa (`CONTAS.DAT`, `MOVTOS.DAT`), layout nos copybooks |
| `legacy/saidas_referencia/` | Saídas geradas rodando o COBOL de verdade (GnuCOBOL). É a referência de paridade da migração |
| `api-extrato/` | API Java 17 de extrato usada pelos canais digitais |
| `docs/` | Roteiro da demo, playbook de migração e relatório do scanner de segurança |

## Rodar o batch COBOL

```bash
sudo apt-get install -y gnucobol   # uma vez
legacy/rodar_batch.sh /tmp/saida   # compila, roda STEP010 e STEP020 e grava as saídas
diff -r /tmp/saida legacy/saidas_referencia
```

## Rodar a API de extrato

```bash
cd api-extrato && mvn -q test
```
