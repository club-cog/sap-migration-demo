# Roteiro da demo: migração de customizações do Protheus com o Devin

**Duração:** 12 a 15 minutos. **Público:** CTO e Founder.
**Mensagem:** o custo de migrar ERP está nas customizações, integrações e testes. O Devin entende o legado,
migra com paridade comprovada e aponta riscos de LGPD, e o time só revisa.

Todos os dados são fictícios ("Rede Clínica Exemplo"). Nenhum código ou dado da Dr. Consulta é usado.

## Antes da reunião

- Repo indexado no DeepWiki e conectado ao Devin.
- Playbook `docs/playbook-migracao-advpl.md` cadastrado no Devin (anotar o `playbook-<id>`).
- Abrir com antecedência uma sessão de backup já concluída (branch `drconsulta/protheus-demo-concluida`), para o caso
  da sessão ao vivo demorar.

## Cena 1 - Entender o legado (Ask Devin, ~3 min)

> Explique como funciona o faturamento de convênio e o repasse médico neste repositório, incluindo as regras de glosa. Liste as regras de negócio que estão fixas no código e não aparecem no dicionário de dados.

**O que mostrar:** o Devin encontra as regras "escondidas" que só estão no código:
- RM acima de R$ 1.000 exige senha mesmo quando o convênio não exige (chamado 48211).
- 10% de desconto em consultas da Saúde Mais (aditivo 2021/04).
- Adicional de plantão de +5 pontos no pronto atendimento.
- Exames de laboratório próprio sem repasse.
- ISS truncado (`NoRound`), não arredondado.

**Fala:** "Isso é o que normalmente leva semanas de consultoria para inventariar."

## Cena 2 - Escopo e riscos (Ask Devin, ~3 min)

> Monte um plano para migrar FATCONV, REPMED e ZAGEFIN para serviços Python com paridade comprovada contra `legacy/saidas_referencia`. Aponte riscos de migração e de LGPD que o time precisa validar antes.

**O que mostrar:**
- Ordem de dependência: FATCONV → REPMED, porque o repasse lê o lote.
- Riscos de arredondamento (`Round` vs `NoRound`).
- CPF em `ConOut`, um problema de LGPD.
- Comportamentos para o negócio decidir: o atendimento A0030 é rejeitado no financeiro mas entra no repasse.

## Cena 3 - Executar (sessão Devin, ~5 min + revisão)

> Execute o plano usando @playbook:playbook-<id> e abra um PR com a tabela de rastreabilidade e o resultado da conciliação. Não corrija comportamentos do legado; liste-os para o negócio validar.

**O que mostrar:**
- Os testes de paridade passando com 100% de conciliação contra o Protheus.
- O PR com a rastreabilidade de cada regra do legado até o Python.
- O Devin Review comentando o PR.
- Os logs sem CPF.

**Fala de fechamento:**
- "Aqui foram 3 rotinas."
- "Numa migração real são centenas, e o mesmo playbook roda numa frota de Devins em paralelo."
- "O time da Dr. Consulta decide o ERP e valida o negócio. O Devin faz o trabalho de engenharia."

## Perguntas de discovery para fechar

- Qual ERP vocês usam e quantas customizações próprias existem?
- Quem mantém esse código hoje? É time interno ou integrador?
- Quais integrações dependem do ERP: PEP, agenda, convênios, bancos, BI?
