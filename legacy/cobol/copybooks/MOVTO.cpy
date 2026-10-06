      *================================================================*
      * COPYBOOK : MOVTO                                               *
      * RESUMO MENSAL DE SERVICOS POR CONTA - LRECL 80                 *
      *================================================================*
       01  REG-MOVTO.
           05 MV-AGENCIA             PIC 9(04).
           05 MV-CONTA               PIC 9(08).
           05 MV-ANO-MES             PIC 9(06).
           05 MV-QTD-SAQUES          PIC 9(03).
           05 MV-QTD-EXTRATOS        PIC 9(03).
           05 MV-QTD-TED             PIC 9(03).
           05 MV-QTD-PIX             PIC 9(04).
           05 FILLER                 PIC X(49).
