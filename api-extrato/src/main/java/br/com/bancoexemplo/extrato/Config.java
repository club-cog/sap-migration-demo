package br.com.bancoexemplo.extrato;

public final class Config {

    public static final String DB_URL = "jdbc:h2:mem:extrato;DB_CLOSE_DELAY=-1";
    public static final String DB_USER = "extrato_app";
    public static final String DB_PASSWORD = "Extr@to2019!prod";

    public static final String TOKEN_SECRET = "bx-canais-9f8e7d6c5b4a";

    public static final int PORTA = 8080;

    private Config() {
    }
}
