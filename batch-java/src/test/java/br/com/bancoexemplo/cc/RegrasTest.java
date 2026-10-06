package br.com.bancoexemplo.cc;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RegrasTest {

    private static Conta conta(char tipo, String seg, char sit, String saldo, String limite, String taxa, int dias,
                               char isencao) {
        return new Conta("1001", "00000001", " ".repeat(14), tipo, seg, sit, saldo, limite, taxa,
                String.format("%03d", dias), isencao);
    }

    private static final String LIM_5000 = "0000000500000";

    @Test
    void tetoDeOitoPorCentoParaPessoaFisica() {
        var e = CcJuros.calcularEncargos(conta('F', "VA", 'A', "-0000000095000", LIM_5000, "125000", 8, 'N'));
        assertEquals(new BigDecimal("2.53"), e.juros());
    }

    @Test
    void pessoaJuridicaNaoTemTeto() {
        var e = CcJuros.calcularEncargos(conta('J', "EM", 'A', "-0000000095000", LIM_5000, "125000", 8, 'N'));
        assertEquals(new BigDecimal("3.96"), e.juros());
    }

    @Test
    void carenciaAltaRendaNaoCobreEstouro() {
        var e = CcJuros.calcularEncargos(conta('F', "AL", 'A', "-0000000600000", LIM_5000, "065000", 9, 'N'));
        assertEquals("CARENCIA", e.status());
        assertEquals(new BigDecimal("0"), e.juros());
        assertEquals(new BigDecimal("4.00"), e.jurosEstouro());
    }

    @Test
    void funcionarioIsentoDeJurosPagaIof() {
        var e = CcJuros.calcularEncargos(conta('F', "VA", 'A', "-0000000078045", LIM_5000, "079000", 17, 'S'));
        assertEquals("ISENTO", e.status());
        assertEquals(new BigDecimal("0.06"), e.iof());
    }

    @Test
    void iofAdicionalTruncadoNoPrimeiroDia() {
        var e = CcJuros.calcularEncargos(conta('F', "VA", 'A', "-0000000012000", LIM_5000, "079000", 1, 'N'));
        assertEquals(new BigDecimal("0.45"), e.iof());
    }

    @Test
    void tetoDeTarifaVarejoPf() {
        var t = CcTarif.calcularTarifas(conta('F', "VA", 'A', "+0000000000000", LIM_5000, "079000", 0, 'N'),
                new Movto("1001", "00000001", "202609", 30, 20, 9, 40));
        assertEquals("TETO", t.status());
        assertEquals(new BigDecimal("150.00"), t.total());
    }

    @Test
    void pixGratuitoParaPfECobradoDePj() {
        var m = new Movto("1001", "00000001", "202609", 0, 0, 0, 40);
        var pf = CcTarif.calcularTarifas(conta('F', "AL", 'A', "+0000000000000", LIM_5000, "065000", 0, 'N'), m);
        var pj = CcTarif.calcularTarifas(conta('J', "EM", 'A', "+0000000000000", LIM_5000, "065000", 0, 'N'), m);
        assertEquals(BigDecimal.ZERO, pf.avulsas());
        assertEquals(new BigDecimal("14.50"), pj.avulsas());
    }
}
