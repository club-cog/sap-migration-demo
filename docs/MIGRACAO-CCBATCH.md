# Migração CCBATCH (COBOL) → batch-java (Java 17)

Conciliação: **100% das linhas iguais** em `ENCARGOS.DAT`, `REJJUROS.DAT`, `TARIFAS.DAT` e `REJTARIF.DAT`,
inclusive os trailers (`ParidadeTest`).

## Rastreabilidade
| COBOL | Regra | Java |
|---|---|---|
| CCJUROS `2000-PROCESSAR-CONTA` | Rejeita registro inválido e conta encerrada; ignora saldo ≥ 0; rejeita ≥ 60 dias (prejuízo) | `CcJuros.processar` |
| CCJUROS `3000-CALCULAR-JUROS` | Teto 8% a.m. PF; taxa diária = taxa/30/100 truncada em 8 casas; juros HALF_UP | `CcJuros.calcularEncargos` |
| CCJUROS `3000` (chamado 31877) | Estouro acima do limite a 12% a.m., precisão cheia, HALF_UP | `CcJuros.jurosDeEstouro` |
| CCJUROS `3000` (aditivo 07) | Alta Renda até 10 dias: sem juros do limite, mas estouro cobrado | `CcJuros.calcularEncargos` |
| CCJUROS `3000` | Funcionário isento de juros | `CcJuros.calcularEncargos` |
| CCJUROS `3500-CALCULAR-IOF` | IOF 0,0082% PF / 0,0041% PJ ao dia, truncado; +0,38% só no 1º dia; vale para isentos | `CcJuros.calcularIof` |
| CCTARIF `3100/3200/3300` | Pacotes Varejo, Alta Renda e Empresas com franquias | `CcTarif.calcularTarifas` |
| CCTARIF `3000` | PIX grátis PF; PJ paga acima de 30; bloqueada sem mensalidade; funcionário isento; teto R$ 150 varejo PF | `CcTarif.calcularTarifas` |
| CCTARIF `2000` | Conta não cadastrada, encerrada ou em prejuízo é rejeitada | `CcTarif.processar` |
| JCL `COND=(4,LT)` | STEP020 só roda se STEP010 terminar com RC ≤ 4 | `CcBatch.executar` |

## Pontos para o negócio validar (mantidos como no legado)
- Conta `1001-10001918` é rejeitada no CCJUROS (saldo inválido) mas é tarifada no CCTARIF.
- Conta PJ no segmento Varejo (`1001-10002192`) recebe o pacote Varejo, com TED sem franquia, e paga PIX como PJ.
- O status `BLOQUEADA` é sobrescrito por `TETO` quando o teto se aplica.
