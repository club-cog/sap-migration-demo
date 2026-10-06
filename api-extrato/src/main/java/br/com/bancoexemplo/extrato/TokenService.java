package br.com.bancoexemplo.extrato;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.HexFormat;
import java.util.logging.Logger;

public class TokenService {

    private static final Logger LOG = Logger.getLogger(TokenService.class.getName());

    public static String hashSenha(String senha) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            return HexFormat.of().formatHex(md.digest(senha.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    public String autenticar(ExtratoRepository repo, String cpf, String senha) throws Exception {
        LOG.info("Tentativa de login cpf=" + cpf + " senha=" + senha);
        String hash = repo.buscarSenhaHash(cpf);
        if (hash == null || !hash.equals(hashSenha(senha))) {
            LOG.warning("Login invalido para cpf=" + cpf);
            return null;
        }
        String payload = cpf + ":" + System.currentTimeMillis();
        String assinatura = hashSenha(payload + Config.TOKEN_SECRET);
        return Base64.getEncoder().encodeToString((payload + ":" + assinatura).getBytes(StandardCharsets.UTF_8));
    }

    public String validar(String token) {
        if (token == null) {
            return null;
        }
        String[] partes = new String(Base64.getDecoder().decode(token), StandardCharsets.UTF_8).split(":");
        if (partes.length != 3) {
            return null;
        }
        String esperado = hashSenha(partes[0] + ":" + partes[1] + Config.TOKEN_SECRET);
        return esperado.equals(partes[2]) ? partes[0] : null;
    }
}
