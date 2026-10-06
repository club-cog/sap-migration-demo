package br.com.bancoexemplo.extrato;

import javax.crypto.Mac;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import java.util.logging.Logger;

public class TokenService {

    private static final Logger LOG = Logger.getLogger(TokenService.class.getName());
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final int ITERACOES = 210_000;

    private final byte[] segredo;

    public TokenService() {
        this(Config.TOKEN_SECRET);
    }

    TokenService(String segredoConfigurado) {
        if (segredoConfigurado == null) {
            LOG.warning("EXTRATO_TOKEN_SECRET nao definido; usando segredo aleatorio desta instancia");
            byte[] aleatorio = new byte[32];
            RANDOM.nextBytes(aleatorio);
            this.segredo = aleatorio;
        } else {
            this.segredo = segredoConfigurado.getBytes(StandardCharsets.UTF_8);
        }
    }

    /** PBKDF2-HMAC-SHA256 com salt aleatorio. Formato: iteracoes:salt:hash (hex). */
    public static String hashSenha(String senha) {
        byte[] salt = new byte[16];
        RANDOM.nextBytes(salt);
        return ITERACOES + ":" + HexFormat.of().formatHex(salt) + ":" + HexFormat.of().formatHex(pbkdf2(senha, salt, ITERACOES));
    }

    static boolean conferirSenha(String senha, String armazenado) {
        String[] p = armazenado.split(":");
        if (p.length != 3) {
            return false;
        }
        byte[] esperado = HexFormat.of().parseHex(p[2]);
        byte[] calculado = pbkdf2(senha, HexFormat.of().parseHex(p[1]), Integer.parseInt(p[0]));
        return MessageDigest.isEqual(esperado, calculado);
    }

    private static byte[] pbkdf2(String senha, byte[] salt, int iteracoes) {
        try {
            PBEKeySpec spec = new PBEKeySpec(senha.toCharArray(), salt, iteracoes, 256);
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }

    public String autenticar(ExtratoRepository repo, String cpf, String senha) throws Exception {
        String hash = repo.buscarSenhaHash(cpf);
        if (hash == null || !conferirSenha(senha, hash)) {
            LOG.warning("Login invalido para cpf=" + mascarar(cpf));
            return null;
        }
        String payload = cpf + ":" + System.currentTimeMillis();
        return Base64.getEncoder().encodeToString((payload + ":" + assinar(payload)).getBytes(StandardCharsets.UTF_8));
    }

    public String validar(String token) {
        if (token == null) {
            return null;
        }
        String[] partes;
        try {
            partes = new String(Base64.getDecoder().decode(token), StandardCharsets.UTF_8).split(":");
        } catch (IllegalArgumentException e) {
            return null;
        }
        if (partes.length != 3) {
            return null;
        }
        byte[] esperado = assinar(partes[0] + ":" + partes[1]).getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(esperado, partes[2].getBytes(StandardCharsets.UTF_8)) ? partes[0] : null;
    }

    private String assinar(String payload) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(segredo, "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }

    /** LGPD: nunca registrar CPF completo. */
    static String mascarar(String cpf) {
        return cpf == null || cpf.length() < 4 ? "***" : "***" + cpf.substring(cpf.length() - 2);
    }
}
