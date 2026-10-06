package br.com.bancoexemplo.cc;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Formatos de saída equivalentes aos campos editados do COBOL (PIC 9(n).99 e PIC 9(n)). */
final class Formato {

    private Formato() {
    }

    /** PIC 9(inteiros).99: zeros à esquerda, ponto decimal, sem sinal. */
    static String decimal(BigDecimal valor, int inteiros) {
        String digitos = valor.abs().setScale(2, RoundingMode.DOWN).unscaledValue().toString();
        String preenchido = "0".repeat(Math.max(0, inteiros + 2 - digitos.length())) + digitos;
        preenchido = preenchido.substring(preenchido.length() - (inteiros + 2));
        return preenchido.substring(0, inteiros) + "." + preenchido.substring(inteiros);
    }

    /** PIC 9(tamanho). */
    static String inteiro(long valor, int tamanho) {
        String s = Long.toString(valor);
        return "0".repeat(Math.max(0, tamanho - s.length())) + s;
    }

    /** LINE SEQUENTIAL do GnuCOBOL grava a linha sem os espaços à direita. */
    static String linha(String conteudo) {
        return conteudo.stripTrailing();
    }

    static boolean numerico(String s) {
        return !s.isEmpty() && s.chars().allMatch(c -> c >= '0' && c <= '9');
    }
}
