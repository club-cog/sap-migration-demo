package br.com.bancoexemplo.cc;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

/**
 * Migração do programa COBOL CCJUROS: encargos diários do cheque especial (juros + IOF).
 * Os nomes dos métodos seguem os parágrafos do COBOL.
 */
public class CcJuros {

    static final BigDecimal TETO_TAXA_PF = new BigDecimal("8.0000");
    static final BigDecimal TAXA_ESTOURO = new BigDecimal("12.0000");
    static final BigDecimal IOF_DIA_PF = new BigDecimal("0.000082");
    static final BigDecimal IOF_DIA_PJ = new BigDecimal("0.000041");
    static final BigDecimal IOF_ADICIONAL = new BigDecimal("0.003800");
    static final int DIAS_CARENCIA = 10;
    static final int DIAS_PREJUIZO = 60;

    private static final BigDecimal TRINTA_VEZES_CEM = new BigDecimal(3000);

    /** Encargos calculados para uma conta (campos de WS-CALCULO). */
    record Encargo(BigDecimal saldoDevedor, BigDecimal juros, BigDecimal jurosEstouro, BigDecimal iof,
                   BigDecimal total, String status) {
    }

    public Resultado processar(List<String> contas) {
        List<String> encargos = new ArrayList<>();
        List<String> rejeitos = new ArrayList<>();
        BigDecimal somaJuros = BigDecimal.ZERO;
        BigDecimal somaIof = BigDecimal.ZERO;
        BigDecimal somaTotal = BigDecimal.ZERO;
        for (String linha : contas) {
            Conta c = Conta.ler(linha);
            String motivo = null;
            if (!c.registroValido()) {
                motivo = "REGISTRO INVALIDO";
            } else if (c.encerrada()) {
                motivo = "CONTA ENCERRADA";
            } else if (c.saldo().signum() >= 0) {
                continue;
            } else if (c.diasAtraso() >= DIAS_PREJUIZO) {
                motivo = "PREJUIZO - ENVIAR PARA COBRANCA";
            }
            if (motivo != null) {
                rejeitos.add(Formato.linha(c.agencia() + ";" + c.numero() + ";" + motivo));
                continue;
            }
            Encargo e = calcularEncargos(c);
            encargos.add(gravarEncargo(c, e));
            somaJuros = somaJuros.add(e.juros()).add(e.jurosEstouro());
            somaIof = somaIof.add(e.iof());
            somaTotal = somaTotal.add(e.total());
        }
        encargos.add("TRAILER;" + Formato.inteiro(encargos.size(), 7) + ";" + Formato.decimal(somaJuros, 11) + ";"
                + Formato.decimal(somaIof, 11) + ";" + Formato.decimal(somaTotal, 11));
        return new Resultado(encargos, rejeitos);
    }

    /** 3000-CALCULAR-JUROS + 3500-CALCULAR-IOF. */
    static Encargo calcularEncargos(Conta c) {
        BigDecimal taxaMes = c.taxaMes();
        if (c.pessoaFisica() && taxaMes.compareTo(TETO_TAXA_PF) > 0) {
            taxaMes = TETO_TAXA_PF;
        }
        // WS-TAXA-DIA PIC 9V9(8): COMPUTE sem ROUNDED trunca em 8 casas
        BigDecimal taxaDia = taxaMes.divide(TRINTA_VEZES_CEM, 8, RoundingMode.DOWN);
        BigDecimal saldoDevedor = c.saldo().negate();
        BigDecimal utilizado;
        BigDecimal estouro;
        if (saldoDevedor.compareTo(c.limite()) > 0) {
            utilizado = c.limite();
            estouro = saldoDevedor.subtract(c.limite());
        } else {
            utilizado = saldoDevedor;
            estouro = BigDecimal.ZERO;
        }
        BigDecimal juros;
        BigDecimal jurosEstouro;
        String status = "NORMAL";
        if (c.funcionario()) {
            juros = BigDecimal.ZERO;
            jurosEstouro = BigDecimal.ZERO;
            status = "ISENTO";
        } else if (c.altaRenda() && c.diasAtraso() <= DIAS_CARENCIA) {
            juros = BigDecimal.ZERO;
            jurosEstouro = jurosDeEstouro(estouro);
            status = "CARENCIA";
        } else {
            juros = utilizado.multiply(taxaDia).setScale(2, RoundingMode.HALF_UP);
            jurosEstouro = jurosDeEstouro(estouro);
        }
        if (estouro.signum() > 0 && "NORMAL".equals(status)) {
            status = "ESTOURO";
        }
        BigDecimal iof = calcularIof(c, saldoDevedor);
        BigDecimal total = juros.add(jurosEstouro).add(iof);
        return new Encargo(saldoDevedor, juros, jurosEstouro, iof, total, status);
    }

    /** Estouro usa a taxa cheia na mesma expressão, sem truncar a taxa diária. */
    private static BigDecimal jurosDeEstouro(BigDecimal estouro) {
        return estouro.multiply(TAXA_ESTOURO).divide(TRINTA_VEZES_CEM, 2, RoundingMode.HALF_UP);
    }

    /** 3500-CALCULAR-IOF: incide sobre todo o saldo devedor, inclusive isentos; trunca a cada COMPUTE. */
    static BigDecimal calcularIof(Conta c, BigDecimal saldoDevedor) {
        BigDecimal aliquota = c.pessoaFisica() ? IOF_DIA_PF : IOF_DIA_PJ;
        BigDecimal iof = saldoDevedor.multiply(aliquota).setScale(2, RoundingMode.DOWN);
        if (c.diasAtraso() == 1) {
            iof = iof.add(saldoDevedor.multiply(IOF_ADICIONAL)).setScale(2, RoundingMode.DOWN);
        }
        return iof;
    }

    private static String gravarEncargo(Conta c, Encargo e) {
        return Formato.linha(c.agencia() + ";" + c.numero() + ";" + Formato.decimal(e.saldoDevedor(), 11) + ";"
                + Formato.decimal(e.juros(), 9) + ";" + Formato.decimal(e.jurosEstouro(), 9) + ";"
                + Formato.decimal(e.iof(), 9) + ";" + Formato.decimal(e.total(), 9) + ";" + e.status());
    }
}
