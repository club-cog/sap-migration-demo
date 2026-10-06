package br.com.bancoexemplo.cc;

import java.math.BigDecimal;

/** Copybook CONTA (LRECL 80). Agência e conta ficam como texto para reproduzir os MOVEs do COBOL. */
record Conta(String agencia, String numero, String cpfCnpj, char tipoPessoa, String segmento, char situacao,
             String saldoBruto, String limiteBruto, String taxaBruta, String diasAtrasoBruto, char isencao) {

    static Conta ler(String linha) {
        String r = String.format("%-80s", linha);
        return new Conta(r.substring(0, 4), r.substring(4, 12), r.substring(12, 26), r.charAt(26),
                r.substring(27, 29), r.charAt(29), r.substring(30, 44), r.substring(44, 57), r.substring(57, 63),
                r.substring(63, 66), r.charAt(66));
    }

    /** CT-SALDO PIC S9(11)V99 SIGN LEADING SEPARATE. */
    boolean saldoNumerico() {
        char sinal = saldoBruto.charAt(0);
        return (sinal == '+' || sinal == '-') && Formato.numerico(saldoBruto.substring(1));
    }

    boolean registroValido() {
        return saldoNumerico() && Formato.numerico(limiteBruto) && Formato.numerico(taxaBruta)
                && Formato.numerico(diasAtrasoBruto);
    }

    BigDecimal saldo() {
        BigDecimal v = new BigDecimal(saldoBruto.substring(1)).movePointLeft(2);
        return saldoBruto.charAt(0) == '-' ? v.negate() : v;
    }

    BigDecimal limite() {
        return new BigDecimal(limiteBruto).movePointLeft(2);
    }

    /** CT-TAXA-MES PIC 9(02)V9(04), em % ao mês. */
    BigDecimal taxaMes() {
        return new BigDecimal(taxaBruta).movePointLeft(4);
    }

    int diasAtraso() {
        return Integer.parseInt(diasAtrasoBruto);
    }

    boolean pessoaFisica() {
        return tipoPessoa == 'F';
    }

    boolean altaRenda() {
        return "AL".equals(segmento);
    }

    boolean encerrada() {
        return situacao == 'E';
    }

    boolean funcionario() {
        return isencao == 'S';
    }
}
