from __future__ import annotations

from fastapi.testclient import TestClient

from servicos.api import app
from servicos.dados import DIR_DADOS, ler_csv

cliente = TestClient(app)


def test_cartao_3x_gera_titulos() -> None:
    resposta = cliente.post("/atendimentos/A0025/titulos-receber")
    assert resposta.status_code == 200
    assert [(t["parcela"], t["valor"], t["vencimento"]) for t in resposta.json()["titulos"]] == [
        ("A", "86.68", "2026-09-05"),
        ("B", "86.66", "2026-10-05"),
        ("C", "86.66", "2026-11-04"),
    ]


def test_rejeicao_retorna_422_com_motivo() -> None:
    resposta = cliente.post("/atendimentos/A0030/titulos-receber")
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == {"numate": "A0030", "motivo": "PARCELAS_INVALIDAS"}


def test_convenio_ou_inexistente_retorna_404() -> None:
    assert cliente.post("/atendimentos/A0001/titulos-receber").status_code == 404
    assert cliente.post("/atendimentos/Z9999/titulos-receber").status_code == 404


def test_respostas_nao_expoem_cpf_nem_nome() -> None:
    pacientes = ler_csv(DIR_DADOS / "SA1_pacientes.csv")
    for numate in ("A0024", "A0025", "A0026", "A0027", "A0028", "A0029", "A0030", "A0001"):
        corpo = cliente.post(f"/atendimentos/{numate}/titulos-receber").text
        for paciente in pacientes:
            assert paciente["A1_CGC"] not in corpo
            assert paciente["A1_NOME"] not in corpo
