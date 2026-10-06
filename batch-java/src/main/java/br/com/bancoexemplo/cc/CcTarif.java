package br.com.bancoexemplo.cc;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/** Migração do programa COBOL CCTARIF: pacotes e tarifas mensais. */
public class CcTarif {

    static final BigDecimal VA_MENSALIDADE = new BigDecimal("0.00");
    static final int VA_FRANQ_SAQUES = 4;
    static final int VA_FRANQ_EXTRATOS = 2;
    static final int VA_FRANQ_TED = 0;
    static final BigDecimal VA_VLR_SAQUE = new BigDecimal("2.80");
    static final BigDecimal VA_VLR_EXTRATO = new BigDecimal("2.10");
    static final BigDecimal VA_VLR_TED = new BigDecimal("10.90");
    static final BigDecimal VA_TETO_PF = new BigDecimal("150.00");
    static final BigDecimal AL_MENSALIDADE = new BigDecimal("59.90");
    static final int AL_FRANQ_TED = 10;
    static final BigDecimal AL_VLR_TED = new BigDecimal("5.50");
    static final BigDecimal EM_MENSALIDADE = new BigDecimal("89.00");
    static final int EM_FRANQ_SAQUES = 10;
    static final BigDecimal EM_VLR_SAQUE = new BigDecimal("3.00");
    static final int EM_FRANQ_TED = 20;
    static final BigDecimal EM_VLR_TED = new BigDecimal("6.90");
    static final int PJ_FRANQ_PIX = 30;
    static final BigDecimal PJ_VLR_PIX = new BigDecimal("1.45");

    record Tarifa(BigDecimal mensalidade, BigDecimal avulsas, BigDecimal total, String status) {
    }

    public Resultado processar(List<String> contas, List<String> movtos) {
        List<Conta> tabela = contas.stream().map(Conta::ler).toList();
        List<String> tarifas = new ArrayList<>();
        List<String> rejeitos = new ArrayList<>();
        BigDecimal soma = BigDecimal.ZERO;
        for (String linha : movtos) {
            Movto m = Movto.ler(linha);
            Conta c = localizarConta(tabela, m);
            String motivo = null;
            if (c == null) {
                motivo = "CONTA NAO CADASTRADA";
            } else if (c.encerrada()) {
                motivo = "CONTA ENCERRADA";
            } else if (Formato.numerico(c.diasAtrasoBruto()) && c.diasAtraso() >= CcJuros.DIAS_PREJUIZO) {
                motivo = "PREJUIZO - TARIFA SUSPENSA";
            }
            if (motivo != null) {
                rejeitos.add(Formato.linha(m.agencia() + ";" + m.conta() + ";" + motivo));
                continue;
            }
            Tarifa t = calcularTarifas(c, m);
            tarifas.add(Formato.linha(m.agencia() + ";" + m.conta() + ";" + m.anoMes() + ";"
                    + Formato.decimal(t.mensalidade(), 7) + ";" + Formato.decimal(t.avulsas(), 7) + ";"
                    + Formato.decimal(t.total(), 7) + ";" + t.status()));
            soma = soma.add(t.total());
        }
        tarifas.add("TRAILER;" + Formato.inteiro(tarifas.size(), 7) + ";" + Formato.decimal(soma, 11));
        return new Resultado(tarifas, rejeitos);
    }

    /** 2100-LOCALIZAR-CONTA: SEARCH sequencial, primeira ocorrência. */
    private static Conta localizarConta(List<Conta> tabela, Movto m) {
        for (Conta c : tabela) {
            if (c.agencia().equals(m.agencia()) && c.numero().equals(m.conta())) {
                return c;
            }
        }
        return null;
    }

    /** 3000-CALCULAR-TARIFAS. */
    static Tarifa calcularTarifas(Conta c, Movto m) {
        BigDecimal mensalidade;
        BigDecimal avulsas = BigDecimal.ZERO;
        String status = "NORMAL";
        switch (c.segmento()) {
            case "AL" -> {
                mensalidade = AL_MENSALIDADE;
                avulsas = avulsas.add(excedente(m.teds(), AL_FRANQ_TED, AL_VLR_TED));
            }
            case "EM" -> {
                mensalidade = EM_MENSALIDADE;
                avulsas = avulsas.add(excedente(m.saques(), EM_FRANQ_SAQUES, EM_VLR_SAQUE))
                        .add(excedente(m.teds(), EM_FRANQ_TED, EM_VLR_TED));
            }
            default -> {
                mensalidade = VA_MENSALIDADE;
                avulsas = avulsas.add(excedente(m.saques(), VA_FRANQ_SAQUES, VA_VLR_SAQUE))
                        .add(excedente(m.extratos(), VA_FRANQ_EXTRATOS, VA_VLR_EXTRATO))
                        .add(excedente(m.teds(), VA_FRANQ_TED, VA_VLR_TED));
            }
        }
        if (c.tipoPessoa() == 'J') {
            avulsas = avulsas.add(excedente(m.pix(), PJ_FRANQ_PIX, PJ_VLR_PIX));
        }
        if (c.situacao() == 'B') {
            mensalidade = BigDecimal.ZERO;
            status = "BLOQUEADA";
        }
        if (c.funcionario()) {
            mensalidade = BigDecimal.ZERO;
            avulsas = BigDecimal.ZERO;
            status = "ISENTO";
        }
        BigDecimal total = mensalidade.add(avulsas);
        if ("VA".equals(c.segmento()) && c.pessoaFisica() && total.compareTo(VA_TETO_PF) > 0) {
            total = VA_TETO_PF;
            status = "TETO";
        }
        return new Tarifa(mensalidade, avulsas, total, status);
    }

    private static BigDecimal excedente(int quantidade, int franquia, BigDecimal valor) {
        int exc = quantidade - franquia;
        return exc > 0 ? valor.multiply(BigDecimal.valueOf(exc)) : BigDecimal.ZERO;
    }
}
