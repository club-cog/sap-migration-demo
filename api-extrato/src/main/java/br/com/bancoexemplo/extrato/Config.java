package br.com.bancoexemplo.extrato;

public final class Config {

    public static final String DB_URL = env("EXTRATO_DB_URL", "jdbc:h2:mem:extrato;DB_CLOSE_DELAY=-1");
    public static final String DB_USER = env("EXTRATO_DB_USER", "sa");
    public static final String DB_PASSWORD = env("EXTRATO_DB_PASSWORD", "");
    public static final String TOKEN_SECRET = env("EXTRATO_TOKEN_SECRET", null);
    public static final int PORTA = Integer.parseInt(env("EXTRATO_PORTA", "8080"));

    private Config() {
    }

    private static String env(String nome, String padrao) {
        String v = System.getenv(nome);
        return v == null || v.isBlank() ? padrao : v;
    }
}
