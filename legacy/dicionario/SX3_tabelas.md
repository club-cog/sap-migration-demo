# Dicionário de dados (extrato do SX2/SX3)

Tabelas customizadas usadas pelas rotinas `FATCONV`, `REPMED` e `ZAGEFIN`.
Datas no formato `AAAAMMDD` (DTOS). Valores com ponto decimal. Todos os dados são fictícios.

| Tabela | Descrição | Chave (índice 1) |
|---|---|---|
| SA1 | Pacientes (clientes) | A1_FILIAL + A1_COD |
| SZ1 | Atendimentos | Z1_FILIAL + Z1_NUMATE |
| SZ2 | Convênios | Z2_FILIAL + Z2_COD |
| SZ3 | Tabela de preços por convênio | Z3_FILIAL + Z3_CONVEN + Z3_PROCED |
| SZ4 | Regras de repasse por médico (PJ) | Z4_FILIAL + Z4_MEDICO |
| SZ5 | Lote de faturamento (cabeçalho) | Z5_FILIAL + Z5_LOTE |
| SZ6 | Itens do lote de faturamento | Z6_FILIAL + Z6_LOTE + Z6_NUMATE |
| SZ7 | Memória de cálculo do repasse | Z7_FILIAL + Z7_COMPET + Z7_MEDICO + Z7_NUMATE |
| SZ8 | Atendimentos rejeitados na integração financeira | Z8_FILIAL + Z8_NUMATE |
| SE1 | Títulos a receber (padrão) | E1_FILIAL + E1_PREFIXO + E1_NUM + E1_PARCELA + E1_TIPO |
| SE2 | Títulos a pagar (padrão) | E2_FILIAL + E2_PREFIXO + E2_NUM + E2_PARCELA + E2_TIPO + E2_FORNECE |

## SZ1 - Atendimentos

| Campo | Tipo | Descrição |
|---|---|---|
| Z1_NUMATE | C 5 | Número do atendimento |
| Z1_DATA | D 8 | Data do atendimento |
| Z1_PACIENT | C 4 | Código do paciente (SA1) |
| Z1_TIPO | C 1 | `C` convênio, `P` particular |
| Z1_CONVEN | C 3 | Convênio (SZ2). `PAR` para particular |
| Z1_PROCED | C 8 | Código do procedimento (padrão TUSS) |
| Z1_MEDICO | C 3 | Médico executante (SZ4) |
| Z1_GUIA | C 10 | Número da guia do convênio |
| Z1_AUTORIZ | C 10 | Senha de autorização da operadora |
| Z1_STATUS | C 1 | `R` realizado, `C` cancelado |
| Z1_FORMPG | C 6 | Particular: `PIX`, `CARTAO`, `BOLETO` |
| Z1_PARCELA | C 2 | Particular cartão: número de parcelas |
| Z1_FATURA | C 6 | Lote em que o atendimento foi faturado (gravado pelo FATCONV) |

## SZ2 - Convênios

| Campo | Tipo | Descrição |
|---|---|---|
| Z2_COD | C 3 | Código |
| Z2_NOME | C 40 | Nome da operadora |
| Z2_PRAZO | N 3 | Prazo de envio da guia, em dias |
| Z2_COPART | N 5,2 | Coparticipação do paciente (%) |
| Z2_EXIGAUT | C 1 | Exige senha de autorização (`S`/`N`) |

## SZ3 - Tabela de preços

| Campo | Tipo | Descrição |
|---|---|---|
| Z3_CONVEN | C 3 | Convênio |
| Z3_PROCED | C 8 | Procedimento |
| Z3_DESCRI | C 40 | Descrição |
| Z3_VALOR | N 12,2 | Valor contratado |
| Z3_COBERTO | C 1 | Coberto pelo plano (`S`/`N`) |

## SZ4 - Regras de repasse

| Campo | Tipo | Descrição |
|---|---|---|
| Z4_MEDICO | C 3 | Código do médico |
| Z4_NOME | C 40 | Razão social (PJ) |
| Z4_CNPJ | C 18 | CNPJ |
| Z4_ESPEC | C 20 | Especialidade |
| Z4_PERC | N 5,2 | Percentual de repasse |
| Z4_MUNISS | C 1 | Município exige retenção de ISS (`S`/`N`) |

## SZ5 / SZ6 - Lote de faturamento

`SZ5`: Z5_LOTE, Z5_CONVEN, Z5_COMPET, Z5_DTENVIO, Z5_QTDGUIA, Z5_VLBRUTO, Z5_VLDESC, Z5_VLCOPAR, Z5_VLFAT, Z5_VLGLOSA.

`SZ6`: Z6_LOTE, Z6_NUMATE, Z6_GUIA, Z6_PROCED, Z6_VLTAB, Z6_VLDESC, Z6_VLCOPAR, Z6_VLFAT, Z6_VLGLOSA, Z6_MOTGLO.

Motivos de glosa (Z6_MOTGLO): `G01` sem autorização, `G02` não coberto, `G03` fora do prazo, `G04` guia duplicada, `G05` sem preço.

## SZ7 - Memória de cálculo do repasse

Z7_COMPET, Z7_MEDICO, Z7_NUMATE, Z7_PROCED, Z7_BASE, Z7_PERC, Z7_VALOR.
