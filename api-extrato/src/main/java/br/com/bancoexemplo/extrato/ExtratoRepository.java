package br.com.bancoexemplo.extrato;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
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
        try (PreparedStatement ps = conexao.prepareStatement("INSERT INTO lancamento VALUES (?,?,?,?,?)")) {
            ps.setString(1, agencia);
            ps.setString(2, conta);
            ps.setObject(3, l.data());
            ps.setString(4, l.historico());
            ps.setBigDecimal(5, l.valor());
            ps.executeUpdate();
        }
    }

    public void inserirCliente(String agencia, String conta, String cpf, String nome, String senhaHash)
            throws SQLException {
        try (PreparedStatement ps = conexao.prepareStatement("INSERT INTO cliente VALUES (?,?,?,?,?)")) {
            ps.setString(1, agencia);
            ps.setString(2, conta);
            ps.setString(3, cpf);
            ps.setString(4, nome);
            ps.setString(5, senhaHash);
            ps.executeUpdate();
        }
    }

    public List<Lancamento> buscarExtrato(String agencia, String conta, String inicio, String fim)
            throws SQLException {
        String sql = "SELECT data, historico, valor FROM lancamento WHERE agencia = ? AND conta = ?"
                + " AND data BETWEEN ? AND ? ORDER BY data";
        List<Lancamento> resultado = new ArrayList<>();
        try (PreparedStatement ps = conexao.prepareStatement(sql)) {
            ps.setString(1, agencia);
            ps.setString(2, conta);
            ps.setObject(3, java.time.LocalDate.parse(inicio));
            ps.setObject(4, java.time.LocalDate.parse(fim));
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    resultado.add(new Lancamento(rs.getDate(1).toLocalDate(), rs.getString(2), rs.getBigDecimal(3)));
                }
            }
        }
        return resultado;
    }

    public String buscarSenhaHash(String cpf) throws SQLException {
        return buscarTexto("SELECT senha_hash FROM cliente WHERE cpf = ?", cpf);
    }

    public String buscarContaDoCliente(String cpf) throws SQLException {
        return buscarTexto("SELECT agencia || '-' || conta FROM cliente WHERE cpf = ?", cpf);
    }

    private String buscarTexto(String sql, String parametro) throws SQLException {
        try (PreparedStatement ps = conexao.prepareStatement(sql)) {
            ps.setString(1, parametro);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }
}
