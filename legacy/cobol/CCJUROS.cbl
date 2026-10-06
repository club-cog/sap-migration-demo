      *================================================================*
      * PROGRAMA : CCJUROS                                             *
      * SISTEMA  : CC - CONTA CORRENTE                                 *
      * OBJETIVO : CALCULO DIARIO DE ENCARGOS DO CHEQUE ESPECIAL       *
      *            (JUROS + IOF). BATCH NOTURNO, PASSO 010 DO CCBATCH  *
      * AUTOR    : J.MARQUES                         DATA: 14/03/1994  *
      *----------------------------------------------------------------*
      * ALTERACOES                                                     *
      *  1998-07 R.SOUZA   IOF ADICIONAL 0,38% NO 1O DIA DE USO        *
      *  2008-01 A.LIMA    IOF DIARIO PJ 0,0041%                       *
      *  2013-05 M.COSTA   JUROS DE ESTOURO DE LIMITE (CHAMADO 31877)  *
      *  2019-11 F.ALVES   CARENCIA ALTA RENDA (ADITIVO COMERCIAL 07)  *
      *  2020-01 F.ALVES   TETO 8% A.M. PESSOA FISICA                  *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CCJUROS.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ARQ-CONTAS   ASSIGN TO 'CONTAS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-CONTAS.
           SELECT ARQ-ENCARGOS ASSIGN TO 'ENCARGOS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-ENCARGOS.
           SELECT ARQ-REJEITOS ASSIGN TO 'REJJUROS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-REJEITOS.

       DATA DIVISION.
       FILE SECTION.
       FD  ARQ-CONTAS.
           COPY CONTA.
       FD  ARQ-ENCARGOS.
       01  REG-ENCARGO               PIC X(100).
       FD  ARQ-REJEITOS.
       01  REG-REJEITO               PIC X(80).

       WORKING-STORAGE SECTION.
       01  WS-FS-CONTAS              PIC X(02).
       01  WS-FS-ENCARGOS            PIC X(02).
       01  WS-FS-REJEITOS            PIC X(02).
       01  WS-FIM-ARQUIVO            PIC X(01) VALUE 'N'.
           88 FIM-CONTAS                       VALUE 'S'.

       01  WS-PARAMETROS.
           05 WS-TETO-TAXA-PF        PIC 9(02)V9(04) VALUE 8.0000.
           05 WS-TAXA-ESTOURO        PIC 9(02)V9(04) VALUE 12.0000.
           05 WS-IOF-DIA-PF          PIC 9V9(06)     VALUE 0.000082.
           05 WS-IOF-DIA-PJ          PIC 9V9(06)     VALUE 0.000041.
           05 WS-IOF-ADICIONAL       PIC 9V9(06)     VALUE 0.003800.
           05 WS-DIAS-CARENCIA       PIC 9(03)       VALUE 10.
           05 WS-DIAS-PREJUIZO       PIC 9(03)       VALUE 60.

       01  WS-CALCULO.
           05 WS-TAXA-MES            PIC 9(02)V9(04)  COMP-3.
           05 WS-TAXA-DIA            PIC 9V9(08)      COMP-3.
           05 WS-SALDO-DEVEDOR       PIC 9(11)V99     COMP-3.
           05 WS-UTILIZADO           PIC 9(11)V99     COMP-3.
           05 WS-ESTOURO             PIC 9(11)V99     COMP-3.
           05 WS-JUROS               PIC 9(09)V99     COMP-3.
           05 WS-JUROS-ESTOURO       PIC 9(09)V99     COMP-3.
           05 WS-IOF                 PIC 9(09)V99     COMP-3.
           05 WS-TOTAL               PIC 9(09)V99     COMP-3.
       01  WS-STATUS                 PIC X(08).
       01  WS-MOTIVO                 PIC X(40).

       01  WS-TOTAIS.
           05 WS-QTD-LIDOS           PIC 9(07) VALUE ZERO.
           05 WS-QTD-COBRADAS        PIC 9(07) VALUE ZERO.
           05 WS-QTD-REJEITADAS      PIC 9(07) VALUE ZERO.
           05 WS-SOMA-JUROS          PIC 9(11)V99 VALUE ZERO.
           05 WS-SOMA-IOF            PIC 9(11)V99 VALUE ZERO.
           05 WS-SOMA-TOTAL          PIC 9(11)V99 VALUE ZERO.

       01  WS-LINHA-ENCARGO.
           05 LE-AGENCIA             PIC 9(04).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-CONTA               PIC 9(08).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-SALDO-DEVEDOR       PIC 9(11).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-JUROS               PIC 9(09).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-JUROS-ESTOURO       PIC 9(09).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-IOF                 PIC 9(09).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-TOTAL               PIC 9(09).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LE-STATUS              PIC X(08).

       01  WS-LINHA-TRAILER.
           05 FILLER                 PIC X(08) VALUE 'TRAILER;'.
           05 LT-QTD                 PIC 9(07).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-JUROS               PIC 9(11).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-IOF                 PIC 9(11).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-TOTAL               PIC 9(11).99.

       01  WS-LINHA-REJEITO.
           05 LR-AGENCIA             PIC X(04).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LR-CONTA               PIC X(08).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LR-MOTIVO              PIC X(40).

       PROCEDURE DIVISION.
       0000-PRINCIPAL.
           PERFORM 1000-INICIALIZAR
           PERFORM 2000-PROCESSAR-CONTA UNTIL FIM-CONTAS
           PERFORM 9000-FINALIZAR
           STOP RUN.

       1000-INICIALIZAR.
           OPEN INPUT ARQ-CONTAS
           IF WS-FS-CONTAS NOT = '00'
              DISPLAY 'CCJUROS - ERRO NA ABERTURA DE CONTAS. FS='
                      WS-FS-CONTAS
              MOVE 12 TO RETURN-CODE
              STOP RUN
           END-IF
           OPEN OUTPUT ARQ-ENCARGOS
           OPEN OUTPUT ARQ-REJEITOS
           PERFORM 1100-LER-CONTA.

       1100-LER-CONTA.
           READ ARQ-CONTAS
              AT END
                 SET FIM-CONTAS TO TRUE
              NOT AT END
                 ADD 1 TO WS-QTD-LIDOS
           END-READ.

       2000-PROCESSAR-CONTA.
           EVALUATE TRUE
              WHEN CT-SALDO       IS NOT NUMERIC
                OR CT-LIMITE      IS NOT NUMERIC
                OR CT-TAXA-MES    IS NOT NUMERIC
                OR CT-DIAS-ATRASO IS NOT NUMERIC
                 MOVE 'REGISTRO INVALIDO' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN CT-ENCERRADA
                 MOVE 'CONTA ENCERRADA' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN CT-SALDO NOT < ZERO
                 CONTINUE
              WHEN CT-DIAS-ATRASO NOT < WS-DIAS-PREJUIZO
                 MOVE 'PREJUIZO - ENVIAR PARA COBRANCA' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN OTHER
                 PERFORM 3000-CALCULAR-JUROS
                 PERFORM 3500-CALCULAR-IOF
                 PERFORM 4000-GRAVAR-ENCARGO
           END-EVALUATE
           PERFORM 1100-LER-CONTA.

       3000-CALCULAR-JUROS.
           INITIALIZE WS-CALCULO
           MOVE CT-TAXA-MES TO WS-TAXA-MES
      *    TETO DE JUROS DO CHEQUE ESPECIAL PARA PF
           IF CT-PESSOA-FISICA AND WS-TAXA-MES > WS-TETO-TAXA-PF
              MOVE WS-TETO-TAXA-PF TO WS-TAXA-MES
           END-IF
      *    MES COMERCIAL DE 30 DIAS
           COMPUTE WS-TAXA-DIA = WS-TAXA-MES / 30 / 100
           COMPUTE WS-SALDO-DEVEDOR = CT-SALDO * -1
           IF WS-SALDO-DEVEDOR > CT-LIMITE
              MOVE CT-LIMITE TO WS-UTILIZADO
              COMPUTE WS-ESTOURO = WS-SALDO-DEVEDOR - CT-LIMITE
           ELSE
              MOVE WS-SALDO-DEVEDOR TO WS-UTILIZADO
              MOVE ZERO TO WS-ESTOURO
           END-IF
           MOVE 'NORMAL' TO WS-STATUS
           EVALUATE TRUE
              WHEN CT-FUNCIONARIO
                 MOVE ZERO TO WS-JUROS WS-JUROS-ESTOURO
                 MOVE 'ISENTO' TO WS-STATUS
              WHEN CT-ALTA-RENDA
               AND CT-DIAS-ATRASO NOT > WS-DIAS-CARENCIA
                 MOVE ZERO TO WS-JUROS
                 COMPUTE WS-JUROS-ESTOURO ROUNDED =
                         WS-ESTOURO * WS-TAXA-ESTOURO / 30 / 100
                 MOVE 'CARENCIA' TO WS-STATUS
              WHEN OTHER
                 COMPUTE WS-JUROS ROUNDED = WS-UTILIZADO * WS-TAXA-DIA
                 COMPUTE WS-JUROS-ESTOURO ROUNDED =
                         WS-ESTOURO * WS-TAXA-ESTOURO / 30 / 100
           END-EVALUATE
           IF WS-ESTOURO > ZERO AND WS-STATUS = 'NORMAL'
              MOVE 'ESTOURO' TO WS-STATUS
           END-IF.

       3500-CALCULAR-IOF.
      *    IOF INCIDE SOBRE TODO O SALDO DEVEDOR, INCLUSIVE ISENTOS
           IF CT-PESSOA-FISICA
              COMPUTE WS-IOF = WS-SALDO-DEVEDOR * WS-IOF-DIA-PF
           ELSE
              COMPUTE WS-IOF = WS-SALDO-DEVEDOR * WS-IOF-DIA-PJ
           END-IF
           IF CT-DIAS-ATRASO = 1
              COMPUTE WS-IOF = WS-IOF
                             + WS-SALDO-DEVEDOR * WS-IOF-ADICIONAL
           END-IF
           COMPUTE WS-TOTAL = WS-JUROS + WS-JUROS-ESTOURO + WS-IOF.

       4000-GRAVAR-ENCARGO.
           MOVE CT-AGENCIA       TO LE-AGENCIA
           MOVE CT-NUMERO        TO LE-CONTA
           MOVE WS-SALDO-DEVEDOR TO LE-SALDO-DEVEDOR
           MOVE WS-JUROS         TO LE-JUROS
           MOVE WS-JUROS-ESTOURO TO LE-JUROS-ESTOURO
           MOVE WS-IOF           TO LE-IOF
           MOVE WS-TOTAL         TO LE-TOTAL
           MOVE WS-STATUS        TO LE-STATUS
           WRITE REG-ENCARGO FROM WS-LINHA-ENCARGO
           ADD 1 TO WS-QTD-COBRADAS
           ADD WS-JUROS WS-JUROS-ESTOURO TO WS-SOMA-JUROS
           ADD WS-IOF   TO WS-SOMA-IOF
           ADD WS-TOTAL TO WS-SOMA-TOTAL.

       8000-REJEITAR.
           MOVE CT-AGENCIA TO LR-AGENCIA
           MOVE CT-NUMERO  TO LR-CONTA
           MOVE WS-MOTIVO  TO LR-MOTIVO
           WRITE REG-REJEITO FROM WS-LINHA-REJEITO
           ADD 1 TO WS-QTD-REJEITADAS.

       9000-FINALIZAR.
           MOVE WS-QTD-COBRADAS TO LT-QTD
           MOVE WS-SOMA-JUROS   TO LT-JUROS
           MOVE WS-SOMA-IOF     TO LT-IOF
           MOVE WS-SOMA-TOTAL   TO LT-TOTAL
           WRITE REG-ENCARGO FROM WS-LINHA-TRAILER
           DISPLAY 'CCJUROS - LIDOS......: ' WS-QTD-LIDOS
           DISPLAY 'CCJUROS - COBRADAS...: ' WS-QTD-COBRADAS
           DISPLAY 'CCJUROS - REJEITADAS.: ' WS-QTD-REJEITADAS
           CLOSE ARQ-CONTAS ARQ-ENCARGOS ARQ-REJEITOS
           IF WS-QTD-REJEITADAS > ZERO
              MOVE 4 TO RETURN-CODE
           END-IF.
