# AGENTS.md

- Dados fictícios. Não use nem peça dados reais de clientes.
- O COBOL em `legacy/` é a fonte da verdade. Não altere `legacy/` numa migração; o código novo vai em `batch-java/`.
- Paridade: o resultado do código migrado deve bater byte a byte com `legacy/saidas_referencia/` usando os arquivos de `legacy/dados/`.
- Valores monetários sempre em `BigDecimal`. Nunca `double`/`float`. Respeite o arredondamento do COBOL: `COMPUTE ... ROUNDED` é HALF_UP; `COMPUTE` sem `ROUNDED` trunca (DOWN), inclusive em campos intermediários.
- Java 17 + Maven + JUnit 5. Rode `mvn -q test` no módulo alterado antes de abrir o PR.
- Não registre CPF/CNPJ, senha ou token em log (LGPD).
- Documentação, commits e PRs em português.
