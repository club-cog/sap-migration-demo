package br.com.bancoexemplo.extrato;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SegurancaTest {

    private static ExtratoRepository repo;

    @BeforeAll
    static void setup() throws Exception {
        repo = new ExtratoRepository();
        App.carregarDadosExemplo(repo);
    }

    @Test
    void sec101SqlInjectionNaoRetornaOutrasContas() throws Exception {
        assertEquals(0, repo.buscarExtrato("1001", "x' OR '1'='1", "2026-09-01", "2026-09-30").size());
        assertNull(repo.buscarSenhaHash("' OR '1'='1"));
    }

    @Test
    void sec102ClienteNaoAcessaContaDeOutro() throws Exception {
        ExtratoHandler handler = new ExtratoHandler(repo, new TokenService("teste"));
        assertTrue(handler.pertenceAoCliente("11122233344", "1001", "10000137"));
        assertFalse(handler.pertenceAoCliente("11122233344", "1001", "10000274"));
    }

    @Test
    void sec103SegredosVemDoAmbiente() {
        assertEquals("", Config.DB_PASSWORD);
        assertNull(Config.TOKEN_SECRET);
    }

    @Test
    void sec104SenhaComPbkdf2ETokenComHmac() {
        String hash = TokenService.hashSenha("senha123");
        assertTrue(hash.startsWith("210000:"));
        assertFalse(hash.equals(TokenService.hashSenha("senha123")));
        assertTrue(TokenService.conferirSenha("senha123", hash));
        assertNull(new TokenService("outro-segredo").validar(
                java.util.Base64.getEncoder().encodeToString("11122233344:1:abc".getBytes())));
    }

    @Test
    void sec105CpfMascaradoNoLog() {
        assertEquals("***44", TokenService.mascarar("11122233344"));
    }
}
