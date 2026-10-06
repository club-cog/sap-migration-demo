package br.com.bancoexemplo.cc;

import java.util.List;

/** Linhas gravadas por um passo do batch: arquivo principal (com trailer) e rejeitos. */
record Resultado(List<String> saida, List<String> rejeitos) {

    int returnCode() {
        return rejeitos.isEmpty() ? 0 : 4;
    }
}
