package br.com.bancoexemplo.cc;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertLinesMatch;

/** Roda o batch Java com os mesmos dados do COBOL e compara com as saídas do GnuCOBOL. */
class ParidadeTest {

    private static final Path LEGADO = Path.of("..", "legacy");

    @Test
    void saidasIguaisAoCobol(@TempDir Path saida) throws Exception {
        assertEquals(4, CcBatch.executar(LEGADO.resolve("dados"), saida));
        for (String arquivo : new String[] {"ENCARGOS.DAT", "REJJUROS.DAT", "TARIFAS.DAT", "REJTARIF.DAT"}) {
            assertLinesMatch(Files.readAllLines(LEGADO.resolve("saidas_referencia").resolve(arquivo)),
                    Files.readAllLines(saida.resolve(arquivo)), arquivo);
        }
    }
}
