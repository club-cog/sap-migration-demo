# Roteiro da demo: Devin no Banco Safra (COBOL, vulnerabilidades e Devin Review)

**Duração:** 15 a 20 minutos. **Mensagem:** o Devin entende o legado, migra com paridade comprovada, fecha o backlog
de segurança e revisa cada PR. O time do banco decide e aprova; o Devin faz o trabalho de engenharia.

Todos os dados são fictícios ("Banco Exemplo"). Nenhum código ou dado do Safra é usado.

## Antes da reunião
- Repo indexado no DeepWiki e conectado ao Devin, com GnuCOBOL, Java 17 e Maven no ambiente.
- Playbook `docs/playbook-migracao-cobol.md` cadastrado no Devin (anotar o `playbook-<id>`).
- Devin Review ligado no repositório.
- Backup: branch `safra/cobol-demo-concluida`, com a migração e as correções já feitas, e sessões concluídas abertas
  em outra aba.

## Cena 1 - Entender o legado (Ask Devin, ~3 min)
> Explique o que o batch CCBATCH faz e como são calculados juros, IOF e tarifas. Liste as regras de negócio que só existem no código COBOL.

**O que mostrar:** as regras que ninguém documentou:
- Teto de 8% a.m. para pessoa física, mesmo que o cadastro tenha taxa maior.
- Estouro de limite cobrado a 12% a.m. (chamado 31877).
- Carência de 10 dias para Alta Renda, que vale só para os juros do limite: o estouro continua sendo cobrado.
- Funcionário isento de juros, mas paga IOF.
- IOF truncado, não arredondado, e IOF adicional de 0,38% só no 1º dia.
- Conta com 60 dias ou mais vai para cobrança e tem a tarifa suspensa.
- Teto de R$ 150 de tarifa no varejo PF e PIX gratuito para PF.

**Fala:** "Esse inventário costuma levar semanas de consultoria e depende de quem ainda conhece o código."

## Cena 2 - Plano e riscos (Ask Devin, ~3 min)
> Monte um plano para migrar CCJUROS e CCTARIF para Java 17 com paridade contra legacy/saidas_referencia. Aponte os riscos e os comportamentos do legado que o negócio precisa validar.

**O que mostrar:**
- Ordem: CCJUROS e depois CCTARIF, como no JCL.
- Risco de arredondamento: a taxa diária é truncada em 8 casas antes dos juros, e o estouro usa precisão cheia.
- Comportamento para o negócio decidir: a conta 10001918 é rejeitada no CCJUROS (registro inválido) mas é tarifada
  no CCTARIF.

## Cena 3 - Migrar (sessão Devin com playbook, ~5 min ao vivo + backup)
> Execute o plano com @playbook:playbook-<id> e abra um PR com a rastreabilidade COBOL → Java e o resultado da conciliação. Não corrija comportamentos do legado; liste-os para o negócio validar.

**O que mostrar:** os testes de paridade com 100% das linhas iguais ao COBOL e o PR com a tabela de rastreabilidade.

## Cena 4 - Vulnerabilidades (sessão Devin, ~3 min)
> Corrija os achados de docs/seguranca/achados-scanner.md na api-extrato, com um teste para cada achado, e abra um PR.

**O que mostrar:** SQL parametrizado, checagem de dono da conta (IDOR), segredos via variável de ambiente, PBKDF2 e
HMAC no lugar de MD5, logs sem CPF e um teste para cada achado.

## Cena 5 - Devin Review (~2 min)
Abrir os dois PRs no Devin Review: resumo do PR, comentários e o que o revisor humano ainda precisa aprovar.

**Fala de fechamento:**
- "Aqui foram 2 programas."
- "Num banco são milhares, e o mesmo playbook roda numa frota de Devins em paralelo, cada um com seu PR e sua conciliação."
- "Segurança deixa de ser backlog: cada achado do scanner vira um PR com teste."

## Perguntas de discovery
- Quantos programas COBOL e JCLs vocês têm, e quem mantém esse código?
- Como é o fluxo hoje entre o scanner de segurança e a correção? Quanto tempo leva?
- O que precisa acontecer para um PR gerado por IA ser aprovado no Safra (revisão, segregação de função, auditoria)?
