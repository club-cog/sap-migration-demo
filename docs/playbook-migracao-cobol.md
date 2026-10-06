# Playbook: migração de programa batch COBOL para Java 17

## Objetivo
Migrar um ou mais programas de `legacy/cobol/` para um módulo Maven em `batch-java/`, com paridade comprovada contra
`legacy/saidas_referencia/`, sem mudar o comportamento do legado.

## Passos
1. Leia o programa, os copybooks usados e o passo correspondente em `legacy/jcl/CCBATCH.jcl`.
2. Monte o inventário de regras de negócio: cada `IF`/`EVALUATE`/`COMPUTE` relevante vira uma linha com programa,
   parágrafo, regra em português e onde ela fica no Java. Inclua as regras que só existem no código (constantes e
   comentários de alteração).
3. Mapeie cada copybook para um `record` Java com parser de largura fixa (posição e tamanho iguais ao copybook).
   Campos `SIGN LEADING SEPARATE` têm o sinal no primeiro byte.
4. Implemente cada parágrafo como um método com nome equivalente (ex.: `3000-CALCULAR-JUROS` vira `calcularJuros`).
5. Dinheiro em `BigDecimal`. Reproduza a escala de cada campo `PIC` intermediário: `ROUNDED` = `HALF_UP`;
   sem `ROUNDED` = `RoundingMode.DOWN` na escala do campo de destino.
6. Gere as saídas no mesmo formato (`;` como separador, numéricos editados com zeros à esquerda, trailer de controle) e
   os mesmos arquivos de rejeito.
7. Testes:
   - teste de paridade que roda o Java com `legacy/dados/` e compara linha a linha com `legacy/saidas_referencia/`;
   - um teste unitário por regra de negócio do inventário.
8. Não corrija comportamentos estranhos do legado. Liste-os no PR como "pontos para o negócio validar".
9. Abra o PR com: inventário de regras com rastreabilidade COBOL → Java, resultado da conciliação (linhas iguais /
   total) e pontos para validar.

## Critérios de aceite
- `mvn -q test` passa em `batch-java/`.
- 100% das linhas de `ENCARGOS`, `REJJUROS`, `TARIFAS` e `REJTARIF` iguais à referência, inclusive trailers.
- Nenhum `double`/`float` em cálculo monetário.
- Nenhum CPF/CNPJ em log.
