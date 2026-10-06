package br.com.bancoexemplo.extrato;

import java.math.BigDecimal;
import java.time.LocalDate;

public record Lancamento(LocalDate data, String historico, BigDecimal valor) {
}
