package br.com.bancoexemplo.cc;

/** Copybook MOVTO (LRECL 80): resumo mensal de serviços por conta. */
record Movto(String agencia, String conta, String anoMes, int saques, int extratos, int teds, int pix) {

    static Movto ler(String linha) {
        String r = String.format("%-80s", linha);
        return new Movto(r.substring(0, 4), r.substring(4, 12), r.substring(12, 18),
                Integer.parseInt(r.substring(18, 21)), Integer.parseInt(r.substring(21, 24)),
                Integer.parseInt(r.substring(24, 27)), Integer.parseInt(r.substring(27, 31)));
    }
}
