package br.com.bancoexemplo.extrato;

import com.sun.net.httpserver.HttpServer;

import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.time.LocalDate;

public class App {

    public static void main(String[] args) throws Exception {
        ExtratoRepository repo = new ExtratoRepository();
        carregarDadosExemplo(repo);
        HttpServer server = HttpServer.create(new InetSocketAddress(Config.PORTA), 0);
        server.createContext("/extrato", new ExtratoHandler(repo, new TokenService()));
        server.start();
        System.out.println("api-extrato no ar na porta " + Config.PORTA);
    }

    static void carregarDadosExemplo(ExtratoRepository repo) throws Exception {
        repo.inserirCliente("1001", "10000137", "11122233344", "Cliente Exemplo Um", TokenService.hashSenha("senha123"));
        repo.inserirCliente("1001", "10000274", "55566677788", "Cliente Exemplo Dois", TokenService.hashSenha("abc@2024"));
        repo.inserir("1001", "10000137", new Lancamento(LocalDate.of(2026, 9, 2), "PIX RECEBIDO", new BigDecimal("1500.00")));
        repo.inserir("1001", "10000137", new Lancamento(LocalDate.of(2026, 9, 5), "TED ENVIADA", new BigDecimal("-3200.00")));
        repo.inserir("1001", "10000137", new Lancamento(LocalDate.of(2026, 9, 6), "JUROS CHEQUE ESPECIAL", new BigDecimal("-4.98")));
        repo.inserir("1001", "10000274", new Lancamento(LocalDate.of(2026, 9, 3), "SAQUE 24H", new BigDecimal("-200.00")));
    }
}
