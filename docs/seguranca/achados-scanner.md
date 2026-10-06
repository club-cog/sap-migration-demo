# Relatório do scanner de segurança - api-extrato

Exportado em 2026-10-01 (exemplo). Severidade conforme a política interna de AppSec.

| ID | Severidade | Regra | Arquivo | Descrição |
|---|---|---|---|---|
| SEC-101 | Crítica | CWE-89 SQL Injection | `ExtratoRepository.java` (`buscarExtrato`, `buscarSenhaHash`, `buscarContaDoCliente`, `inserir`, `inserirCliente`) | SQL montado por concatenação com parâmetros vindos da requisição |
| SEC-102 | Alta | CWE-639 IDOR | `ExtratoHandler.java` (`handle`) | O token é validado, mas não se verifica se a agência/conta pedida pertence ao cliente autenticado |
| SEC-103 | Alta | CWE-798 Credencial no código | `Config.java` | Senha do banco e segredo do token fixos no código-fonte |
| SEC-104 | Alta | CWE-328 Hash fraco | `TokenService.java` (`hashSenha`) | Senhas com MD5 sem salt; assinatura do token com MD5 em vez de HMAC |
| SEC-105 | Média | CWE-532 Dado sensível em log (LGPD) | `TokenService.java`, `ExtratoHandler.java` | CPF e senha em texto claro nos logs |
| SEC-106 | Baixa | CWE-209 Exposição de erro | `ExtratoHandler.java` | Mensagem da exceção devolvida ao cliente |
