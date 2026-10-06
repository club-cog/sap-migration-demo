      *================================================================*
      * PROGRAMA : CCTARIF                                             *
      * SISTEMA  : CC - CONTA CORRENTE                                 *
      * OBJETIVO : COBRANCA MENSAL DE PACOTES E TARIFAS AVULSAS.       *
      *            PASSO 020 DO CCBATCH (RODA APOS O CCJUROS)          *
      * AUTOR    : J.MARQUES                         DATA: 02/09/1996  *
      *----------------------------------------------------------------*
      * ALTERACOES                                                     *
      *  2010-04 A.LIMA    SERVICOS ESSENCIAIS GRATUITOS (VAREJO)      *
      *  2017-08 M.COSTA   TETO MENSAL VAREJO PF (ACORDO 2017/112)     *
      *  2020-11 F.ALVES   PIX GRATUITO PARA PESSOA FISICA             *
      *  2022-03 F.ALVES   SUSPENDE TARIFA DE CONTA EM PREJUIZO        *
      *================================================================*
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CCTARIF.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ARQ-CONTAS   ASSIGN TO 'CONTAS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-CONTAS.
           SELECT ARQ-MOVTOS   ASSIGN TO 'MOVTOS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-MOVTOS.
           SELECT ARQ-TARIFAS  ASSIGN TO 'TARIFAS'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-TARIFAS.
           SELECT ARQ-REJEITOS ASSIGN TO 'REJTARIF'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS  IS WS-FS-REJEITOS.

       DATA DIVISION.
       FILE SECTION.
       FD  ARQ-CONTAS.
           COPY CONTA.
       FD  ARQ-MOVTOS.
           COPY MOVTO.
       FD  ARQ-TARIFAS.
       01  REG-TARIFA                PIC X(100).
       FD  ARQ-REJEITOS.
       01  REG-REJEITO               PIC X(80).

       WORKING-STORAGE SECTION.
       01  WS-FS-CONTAS              PIC X(02).
       01  WS-FS-MOVTOS              PIC X(02).
       01  WS-FS-TARIFAS             PIC X(02).
       01  WS-FS-REJEITOS            PIC X(02).
       01  WS-FIM-CONTAS             PIC X(01) VALUE 'N'.
           88 FIM-CONTAS                       VALUE 'S'.
       01  WS-FIM-MOVTOS             PIC X(01) VALUE 'N'.
           88 FIM-MOVTOS                       VALUE 'S'.

      *    TABELA DE CONTAS CARREGADA EM MEMORIA
       01  WS-QTD-CONTAS             PIC 9(05) VALUE ZERO.
       01  WS-TAB-CONTAS.
           05 WS-CONTA OCCURS 1 TO 5000 TIMES
                       DEPENDING ON WS-QTD-CONTAS
                       INDEXED BY IX-CONTA.
              10 TB-AGENCIA          PIC 9(04).
              10 TB-NUMERO           PIC 9(08).
              10 TB-TIPO-PESSOA      PIC X(01).
              10 TB-SEGMENTO         PIC X(02).
              10 TB-SITUACAO         PIC X(01).
              10 TB-DIAS-ATRASO      PIC X(03).
              10 TB-ISENCAO          PIC X(01).
       01  WS-ACHOU                  PIC X(01).
           88 CONTA-ENCONTRADA                 VALUE 'S'.

      *    TABELA DE TARIFAS (VIGENCIA 2024-01)
       01  WS-TARIFAS-VAREJO.
           05 WS-VA-MENSALIDADE      PIC 9(03)V99 VALUE 0.
           05 WS-VA-FRANQ-SAQUES     PIC 9(03)    VALUE 4.
           05 WS-VA-FRANQ-EXTRATOS   PIC 9(03)    VALUE 2.
           05 WS-VA-FRANQ-TED        PIC 9(03)    VALUE 0.
           05 WS-VA-VLR-SAQUE        PIC 9(03)V99 VALUE 2.80.
           05 WS-VA-VLR-EXTRATO      PIC 9(03)V99 VALUE 2.10.
           05 WS-VA-VLR-TED          PIC 9(03)V99 VALUE 10.90.
           05 WS-VA-TETO-PF          PIC 9(03)V99 VALUE 150.00.
       01  WS-TARIFAS-ALTA-RENDA.
           05 WS-AL-MENSALIDADE      PIC 9(03)V99 VALUE 59.90.
           05 WS-AL-FRANQ-TED        PIC 9(03)    VALUE 10.
           05 WS-AL-VLR-TED          PIC 9(03)V99 VALUE 5.50.
       01  WS-TARIFAS-EMPRESAS.
           05 WS-EM-MENSALIDADE      PIC 9(03)V99 VALUE 89.00.
           05 WS-EM-FRANQ-SAQUES     PIC 9(03)    VALUE 10.
           05 WS-EM-VLR-SAQUE        PIC 9(03)V99 VALUE 3.00.
           05 WS-EM-FRANQ-TED        PIC 9(03)    VALUE 20.
           05 WS-EM-VLR-TED          PIC 9(03)V99 VALUE 6.90.
       01  WS-TARIFAS-PIX-PJ.
           05 WS-PJ-FRANQ-PIX        PIC 9(04)    VALUE 30.
           05 WS-PJ-VLR-PIX          PIC 9(03)V99 VALUE 1.45.

       01  WS-CALCULO.
           05 WS-MENSALIDADE         PIC 9(07)V99 COMP-3.
           05 WS-AVULSAS             PIC 9(07)V99 COMP-3.
           05 WS-TOTAL               PIC 9(07)V99 COMP-3.
           05 WS-EXCEDENTE           PIC S9(05)   COMP-3.
       01  WS-STATUS                 PIC X(09).
       01  WS-MOTIVO                 PIC X(40).

       01  WS-TOTAIS.
           05 WS-QTD-LIDOS           PIC 9(07) VALUE ZERO.
           05 WS-QTD-TARIFADAS       PIC 9(07) VALUE ZERO.
           05 WS-QTD-REJEITADAS      PIC 9(07) VALUE ZERO.
           05 WS-SOMA-TOTAL          PIC 9(11)V99 VALUE ZERO.

       01  WS-LINHA-TARIFA.
           05 LT-AGENCIA             PIC 9(04).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-CONTA               PIC 9(08).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-ANO-MES             PIC 9(06).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-MENSALIDADE         PIC 9(07).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-AVULSAS             PIC 9(07).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-TOTAL               PIC 9(07).99.
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LT-STATUS              PIC X(09).

       01  WS-LINHA-TRAILER.
           05 FILLER                 PIC X(08) VALUE 'TRAILER;'.
           05 LTR-QTD                PIC 9(07).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LTR-TOTAL              PIC 9(11).99.

       01  WS-LINHA-REJEITO.
           05 LR-AGENCIA             PIC X(04).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LR-CONTA               PIC X(08).
           05 FILLER                 PIC X(01) VALUE ';'.
           05 LR-MOTIVO              PIC X(40).

       PROCEDURE DIVISION.
       0000-PRINCIPAL.
           PERFORM 1000-CARREGAR-CONTAS
           PERFORM 1500-ABRIR-MOVTOS
           PERFORM 2000-PROCESSAR-MOVTO UNTIL FIM-MOVTOS
           PERFORM 9000-FINALIZAR
           STOP RUN.

       1000-CARREGAR-CONTAS.
           OPEN INPUT ARQ-CONTAS
           IF WS-FS-CONTAS NOT = '00'
              DISPLAY 'CCTARIF - ERRO NA ABERTURA DE CONTAS. FS='
                      WS-FS-CONTAS
              MOVE 12 TO RETURN-CODE
              STOP RUN
           END-IF
           PERFORM UNTIL FIM-CONTAS
              READ ARQ-CONTAS
                 AT END
                    SET FIM-CONTAS TO TRUE
                 NOT AT END
                    ADD 1 TO WS-QTD-CONTAS
                    MOVE CT-AGENCIA     TO TB-AGENCIA(WS-QTD-CONTAS)
                    MOVE CT-NUMERO      TO TB-NUMERO(WS-QTD-CONTAS)
                    MOVE CT-TIPO-PESSOA TO TB-TIPO-PESSOA(WS-QTD-CONTAS)
                    MOVE CT-SEGMENTO    TO TB-SEGMENTO(WS-QTD-CONTAS)
                    MOVE CT-SITUACAO    TO TB-SITUACAO(WS-QTD-CONTAS)
                    MOVE CT-DIAS-ATRASO TO TB-DIAS-ATRASO(WS-QTD-CONTAS)
                    MOVE CT-ISENCAO     TO TB-ISENCAO(WS-QTD-CONTAS)
              END-READ
           END-PERFORM
           CLOSE ARQ-CONTAS.

       1500-ABRIR-MOVTOS.
           OPEN INPUT ARQ-MOVTOS
           IF WS-FS-MOVTOS NOT = '00'
              DISPLAY 'CCTARIF - ERRO NA ABERTURA DE MOVTOS. FS='
                      WS-FS-MOVTOS
              MOVE 12 TO RETURN-CODE
              STOP RUN
           END-IF
           OPEN OUTPUT ARQ-TARIFAS
           OPEN OUTPUT ARQ-REJEITOS
           PERFORM 1600-LER-MOVTO.

       1600-LER-MOVTO.
           READ ARQ-MOVTOS
              AT END
                 SET FIM-MOVTOS TO TRUE
              NOT AT END
                 ADD 1 TO WS-QTD-LIDOS
           END-READ.

       2000-PROCESSAR-MOVTO.
           PERFORM 2100-LOCALIZAR-CONTA
           EVALUATE TRUE
              WHEN NOT CONTA-ENCONTRADA
                 MOVE 'CONTA NAO CADASTRADA' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN TB-SITUACAO(IX-CONTA) = 'E'
                 MOVE 'CONTA ENCERRADA' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN TB-DIAS-ATRASO(IX-CONTA) IS NUMERIC
               AND TB-DIAS-ATRASO(IX-CONTA) NOT < '060'
                 MOVE 'PREJUIZO - TARIFA SUSPENSA' TO WS-MOTIVO
                 PERFORM 8000-REJEITAR
              WHEN OTHER
                 PERFORM 3000-CALCULAR-TARIFAS
                 PERFORM 4000-GRAVAR-TARIFA
           END-EVALUATE
           PERFORM 1600-LER-MOVTO.

       2100-LOCALIZAR-CONTA.
           MOVE 'N' TO WS-ACHOU
           SET IX-CONTA TO 1
           SEARCH WS-CONTA
              AT END
                 MOVE 'N' TO WS-ACHOU
              WHEN TB-AGENCIA(IX-CONTA) = MV-AGENCIA
               AND TB-NUMERO(IX-CONTA)  = MV-CONTA
                 MOVE 'S' TO WS-ACHOU
           END-SEARCH.

       3000-CALCULAR-TARIFAS.
           INITIALIZE WS-CALCULO
           MOVE 'NORMAL' TO WS-STATUS
           EVALUATE TB-SEGMENTO(IX-CONTA)
              WHEN 'AL'
                 PERFORM 3200-PACOTE-ALTA-RENDA
              WHEN 'EM'
                 PERFORM 3300-PACOTE-EMPRESAS
              WHEN OTHER
                 PERFORM 3100-PACOTE-VAREJO
           END-EVALUATE
      *    PIX: GRATUITO PARA PF. PJ PAGA ACIMA DA FRANQUIA
           IF TB-TIPO-PESSOA(IX-CONTA) = 'J'
              COMPUTE WS-EXCEDENTE = MV-QTD-PIX - WS-PJ-FRANQ-PIX
              IF WS-EXCEDENTE > ZERO
                 COMPUTE WS-AVULSAS = WS-AVULSAS
                                    + WS-EXCEDENTE * WS-PJ-VLR-PIX
              END-IF
           END-IF
           IF TB-SITUACAO(IX-CONTA) = 'B'
              MOVE ZERO TO WS-MENSALIDADE
              MOVE 'BLOQUEADA' TO WS-STATUS
           END-IF
           IF TB-ISENCAO(IX-CONTA) = 'S'
              MOVE ZERO TO WS-MENSALIDADE WS-AVULSAS
              MOVE 'ISENTO' TO WS-STATUS
           END-IF
           COMPUTE WS-TOTAL = WS-MENSALIDADE + WS-AVULSAS
           IF TB-SEGMENTO(IX-CONTA) = 'VA'
              AND TB-TIPO-PESSOA(IX-CONTA) = 'F'
              AND WS-TOTAL > WS-VA-TETO-PF
              MOVE WS-VA-TETO-PF TO WS-TOTAL
              MOVE 'TETO' TO WS-STATUS
           END-IF.

       3100-PACOTE-VAREJO.
           MOVE WS-VA-MENSALIDADE TO WS-MENSALIDADE
           COMPUTE WS-EXCEDENTE = MV-QTD-SAQUES - WS-VA-FRANQ-SAQUES
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-VA-VLR-SAQUE
           END-IF
           COMPUTE WS-EXCEDENTE =
                   MV-QTD-EXTRATOS - WS-VA-FRANQ-EXTRATOS
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-VA-VLR-EXTRATO
           END-IF
           COMPUTE WS-EXCEDENTE = MV-QTD-TED - WS-VA-FRANQ-TED
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-VA-VLR-TED
           END-IF.

       3200-PACOTE-ALTA-RENDA.
           MOVE WS-AL-MENSALIDADE TO WS-MENSALIDADE
           COMPUTE WS-EXCEDENTE = MV-QTD-TED - WS-AL-FRANQ-TED
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-AL-VLR-TED
           END-IF.

       3300-PACOTE-EMPRESAS.
           MOVE WS-EM-MENSALIDADE TO WS-MENSALIDADE
           COMPUTE WS-EXCEDENTE = MV-QTD-SAQUES - WS-EM-FRANQ-SAQUES
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-EM-VLR-SAQUE
           END-IF
           COMPUTE WS-EXCEDENTE = MV-QTD-TED - WS-EM-FRANQ-TED
           IF WS-EXCEDENTE > ZERO
              COMPUTE WS-AVULSAS = WS-AVULSAS
                                 + WS-EXCEDENTE * WS-EM-VLR-TED
           END-IF.

       4000-GRAVAR-TARIFA.
           MOVE MV-AGENCIA     TO LT-AGENCIA
           MOVE MV-CONTA       TO LT-CONTA
           MOVE MV-ANO-MES     TO LT-ANO-MES
           MOVE WS-MENSALIDADE TO LT-MENSALIDADE
           MOVE WS-AVULSAS     TO LT-AVULSAS
           MOVE WS-TOTAL       TO LT-TOTAL
           MOVE WS-STATUS      TO LT-STATUS
           WRITE REG-TARIFA FROM WS-LINHA-TARIFA
           ADD 1 TO WS-QTD-TARIFADAS
           ADD WS-TOTAL TO WS-SOMA-TOTAL.

       8000-REJEITAR.
           MOVE MV-AGENCIA TO LR-AGENCIA
           MOVE MV-CONTA   TO LR-CONTA
           MOVE WS-MOTIVO  TO LR-MOTIVO
           WRITE REG-REJEITO FROM WS-LINHA-REJEITO
           ADD 1 TO WS-QTD-REJEITADAS.

       9000-FINALIZAR.
           MOVE WS-QTD-TARIFADAS TO LTR-QTD
           MOVE WS-SOMA-TOTAL    TO LTR-TOTAL
           WRITE REG-TARIFA FROM WS-LINHA-TRAILER
           DISPLAY 'CCTARIF - LIDOS......: ' WS-QTD-LIDOS
           DISPLAY 'CCTARIF - TARIFADAS..: ' WS-QTD-TARIFADAS
           DISPLAY 'CCTARIF - REJEITADAS.: ' WS-QTD-REJEITADAS
           CLOSE ARQ-MOVTOS ARQ-TARIFAS ARQ-REJEITOS
           IF WS-QTD-REJEITADAS > ZERO
              MOVE 4 TO RETURN-CODE
           END-IF.
