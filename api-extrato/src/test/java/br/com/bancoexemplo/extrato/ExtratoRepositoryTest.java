package br.com.bancoexemplo.extrato;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

class ExtratoRepositoryTest {

    private static ExtratoRepository repo;

    @BeforeAll
    static void setup() throws Exception {
        repo = new ExtratoRepository();
        App.carregarDadosExemplo(repo);
    }

    @Test
    void retornaExtratoDoPeriodo() throws Exception {
        List<Lancamento> itens = repo.buscarExtrato("1001", "10000137", "2026-09-01", "2026-09-30");
        assertEquals(3, itens.size());
        assertEquals("PIX RECEBIDO", itens.get(0).historico());
    }

    @Test
    void autenticaComSenhaCorreta() throws Exception {
        TokenService tokens = new TokenService();
        String token = tokens.autenticar(repo, "11122233344", "senha123");
        assertNotNull(token);
        assertEquals("11122233344", tokens.validar(token));
        assertNull(tokens.autenticar(repo, "11122233344", "errada"));
    }
}
