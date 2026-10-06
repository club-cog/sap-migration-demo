      *================================================================*
      * COPYBOOK : CONTA                                               *
      * REGISTRO MESTRE DE CONTA CORRENTE - LRECL 80                   *
      *================================================================*
       01  REG-CONTA.
           05 CT-AGENCIA             PIC 9(04).
           05 CT-NUMERO              PIC 9(08).
           05 CT-CPF-CNPJ            PIC X(14).
           05 CT-TIPO-PESSOA         PIC X(01).
              88 CT-PESSOA-FISICA              VALUE 'F'.
              88 CT-PESSOA-JURIDICA            VALUE 'J'.
           05 CT-SEGMENTO            PIC X(02).
              88 CT-VAREJO                     VALUE 'VA'.
              88 CT-ALTA-RENDA                 VALUE 'AL'.
              88 CT-EMPRESAS                   VALUE 'EM'.
           05 CT-SITUACAO            PIC X(01).
              88 CT-ATIVA                      VALUE 'A'.
              88 CT-BLOQUEADA                  VALUE 'B'.
              88 CT-ENCERRADA                  VALUE 'E'.
           05 CT-SALDO               PIC S9(11)V99
                                     SIGN LEADING SEPARATE.
           05 CT-LIMITE              PIC 9(11)V99.
           05 CT-TAXA-MES            PIC 9(02)V9(04).
           05 CT-DIAS-ATRASO         PIC 9(03).
           05 CT-ISENCAO             PIC X(01).
              88 CT-FUNCIONARIO                VALUE 'S'.
           05 FILLER                 PIC X(13).
