package br.com.bancoexemplo.extrato;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

/**
 * GET /extrato?agencia=1001&conta=10000137&inicio=2026-09-01&fim=2026-09-30
 * Header: Authorization: Bearer {token}
 */
public class ExtratoHandler implements HttpHandler {

    private static final Logger LOG = Logger.getLogger(ExtratoHandler.class.getName());

    private final ExtratoRepository repo;
    private final TokenService tokens;

    public ExtratoHandler(ExtratoRepository repo, TokenService tokens) {
        this.repo = repo;
        this.tokens = tokens;
    }

    @Override
    public void handle(HttpExchange ex) throws IOException {
        Map<String, String> q = parametros(ex.getRequestURI().getRawQuery());
        String auth = ex.getRequestHeaders().getFirst("Authorization");
        String cpf = tokens.validar(auth == null ? null : auth.replace("Bearer ", ""));
        if (cpf == null) {
            responder(ex, 401, "{\"erro\":\"nao autenticado\"}");
            return;
        }
        try {
            if (!pertenceAoCliente(cpf, q.get("agencia"), q.get("conta"))) {
                LOG.warning("Acesso negado a conta de outro cliente. cpf=" + TokenService.mascarar(cpf));
                responder(ex, 403, "{\"erro\":\"acesso negado\"}");
                return;
            }
            List<Lancamento> itens = repo.buscarExtrato(q.get("agencia"), q.get("conta"), q.get("inicio"), q.get("fim"));
            StringBuilder json = new StringBuilder("[");
            for (int i = 0; i < itens.size(); i++) {
                Lancamento l = itens.get(i);
                if (i > 0) {
                    json.append(',');
                }
                json.append("{\"data\":\"").append(l.data()).append("\",\"historico\":\"").append(l.historico())
                        .append("\",\"valor\":").append(l.valor()).append('}');
            }
            responder(ex, 200, json.append(']').toString());
        } catch (Exception e) {
            LOG.log(java.util.logging.Level.SEVERE, "Erro ao consultar extrato", e);
            responder(ex, 500, "{\"erro\":\"erro interno\"}");
        }
    }

    boolean pertenceAoCliente(String cpf, String agencia, String conta) throws Exception {
        String contaDoCliente = repo.buscarContaDoCliente(cpf);
        return contaDoCliente != null && contaDoCliente.equals(agencia + "-" + conta);
    }

    static Map<String, String> parametros(String query) {
        Map<String, String> m = new HashMap<>();
        if (query == null) {
            return m;
        }
        for (String par : query.split("&")) {
            String[] kv = par.split("=", 2);
            m.put(kv[0], kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
        }
        return m;
    }

    private static void responder(HttpExchange ex, int status, String corpo) throws IOException {
        byte[] bytes = corpo.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(bytes);
        }
    }
}
