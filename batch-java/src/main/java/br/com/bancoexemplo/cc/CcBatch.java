package br.com.bancoexemplo.cc;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Equivalente ao JCL CCBATCH: STEP010 (CCJUROS) e STEP020 (CCTARIF, só se STEP010 terminar com RC <= 4).
 * Uso: CcBatch <diretorio-dados> <diretorio-saida>
 */
public final class CcBatch {

    private CcBatch() {
    }

    public static void main(String[] args) throws IOException {
        Path dados = Path.of(args.length > 0 ? args[0] : "../legacy/dados");
        Path saida = Path.of(args.length > 1 ? args[1] : "target/saida");
        System.exit(executar(dados, saida));
    }

    public static int executar(Path dados, Path saida) throws IOException {
        Files.createDirectories(saida);
        List<String> contas = ler(dados.resolve("CONTAS.DAT"));
        Resultado juros = new CcJuros().processar(contas);
        gravar(saida.resolve("ENCARGOS.DAT"), juros.saida());
        gravar(saida.resolve("REJJUROS.DAT"), juros.rejeitos());
        System.out.println("STEP010 CCJUROS RC=" + juros.returnCode());
        if (juros.returnCode() > 4) {
            return juros.returnCode();
        }
        Resultado tarifas = new CcTarif().processar(contas, ler(dados.resolve("MOVTOS.DAT")));
        gravar(saida.resolve("TARIFAS.DAT"), tarifas.saida());
        gravar(saida.resolve("REJTARIF.DAT"), tarifas.rejeitos());
        System.out.println("STEP020 CCTARIF RC=" + tarifas.returnCode());
        return Math.max(juros.returnCode(), tarifas.returnCode());
    }

    static List<String> ler(Path arquivo) throws IOException {
        return Files.readAllLines(arquivo, StandardCharsets.ISO_8859_1).stream().filter(l -> !l.isEmpty()).toList();
    }

    private static void gravar(Path arquivo, List<String> linhas) throws IOException {
        StringBuilder sb = new StringBuilder();
        linhas.forEach(l -> sb.append(l).append('\n'));
        Files.writeString(arquivo, sb.toString(), StandardCharsets.ISO_8859_1);
    }
}
