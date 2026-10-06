package br.com.bancoexemplo.extrato;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class ExtratoRepository {

    private final Connection conexao;

    public ExtratoRepository() throws SQLException {
        this.conexao = DriverManager.getConnection(Config.DB_URL, Config.DB_USER, Config.DB_PASSWORD);
        criarTabelas();
    }

    private void criarTabelas() throws SQLException {
        try (Statement st = conexao.createStatement()) {
            st.execute("CREATE TABLE IF NOT EXISTS lancamento ("
                    + "agencia VARCHAR(4), conta VARCHAR(8), data DATE, historico VARCHAR(60), valor DECIMAL(15,2))");
            st.execute("CREATE TABLE IF NOT EXISTS cliente ("
                    + "agencia VARCHAR(4), conta VARCHAR(8), cpf VARCHAR(14), nome VARCHAR(60), senha_hash VARCHAR(64))");
        }
    }

    public void inserir(String agencia, String conta, Lancamento l) throws SQLException {
        try (Statement st = conexao.createStatement()) {
            st.executeUpdate("INSERT INTO lancamento VALUES ('" + agencia + "','" + conta + "','"
                    + l.data() + "','" + l.historico() + "'," + l.valor() + ")");
        }
    }

    public void inserirCliente(String agencia, String conta, String cpf, String nome, String senhaHash)
            throws SQLException {
        try (Statement st = conexao.createStatement()) {
            st.executeUpdate("INSERT INTO cliente VALUES ('" + agencia + "','" + conta + "','" + cpf + "','"
                    + nome + "','" + senhaHash + "')");
        }
    }

    public List<Lancamento> buscarExtrato(String agencia, String conta, String inicio, String fim)
            throws SQLException {
        String sql = "SELECT data, historico, valor FROM lancamento WHERE agencia = '" + agencia
                + "' AND conta = '" + conta + "' AND data BETWEEN '" + inicio + "' AND '" + fim
                + "' ORDER BY data";
        List<Lancamento> resultado = new ArrayList<>();
        try (Statement st = conexao.createStatement(); ResultSet rs = st.executeQuery(sql)) {
            while (rs.next()) {
                resultado.add(new Lancamento(rs.getDate(1).toLocalDate(), rs.getString(2), rs.getBigDecimal(3)));
            }
        }
        return resultado;
    }

    public String buscarSenhaHash(String cpf) throws SQLException {
        try (Statement st = conexao.createStatement();
             ResultSet rs = st.executeQuery("SELECT senha_hash FROM cliente WHERE cpf = '" + cpf + "'")) {
            return rs.next() ? rs.getString(1) : null;
        }
    }

    public String buscarContaDoCliente(String cpf) throws SQLException {
        try (Statement st = conexao.createStatement();
             ResultSet rs = st.executeQuery("SELECT agencia || '-' || conta FROM cliente WHERE cpf = '" + cpf + "'")) {
            return rs.next() ? rs.getString(1) : null;
        }
    }
}
