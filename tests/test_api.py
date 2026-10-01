from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from servicos.api import VARIAVEL_CHAVE_API, CacheArquivos, app, obter_base, obter_feriados
from servicos.dados import DIR_DADOS, ler_csv
from tests.conftest import atendimento, montar_base

CHAVE = "chave-de-teste"
cliente = TestClient(app, headers={"X-API-Key": CHAVE})


@pytest.fixture(autouse=True)
def chave_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(VARIAVEL_CHAVE_API, CHAVE)
    yield
    app.dependency_overrides.clear()


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


def test_sem_chave_ou_chave_errada_retorna_401() -> None:
    anonimo = TestClient(app)
    assert anonimo.post("/atendimentos/A0025/titulos-receber").status_code == 401
    errada = anonimo.post("/atendimentos/A0025/titulos-receber", headers={"X-API-Key": "outra"})
    assert errada.status_code == 401
    assert "P022" not in errada.text


def test_sem_chave_configurada_recusa_tudo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VARIAVEL_CHAVE_API)
    assert cliente.post("/atendimentos/A0025/titulos-receber").status_code == 503


def test_feriados_configurados_sao_aplicados_no_boleto() -> None:
    assert date(2026, 9, 7) in obter_feriados()
    boleto = atendimento(numate="X0100", tipo="P", convenio="PAR", data=date(2026, 9, 4), forma_pagamento="BOLETO")
    app.dependency_overrides[obter_base] = lambda: montar_base([boleto])

    resposta = cliente.post("/atendimentos/X0100/titulos-receber")

    assert resposta.json()["titulos"][0]["vencimento"] == "2026-09-08"


def test_cache_recarrega_quando_arquivo_muda(tmp_path: Path) -> None:
    arquivo = tmp_path / "SZ1.csv"
    arquivo.write_text("v1")
    cache = CacheArquivos(lambda: [arquivo], arquivo.read_text)
    assert cache.obter() == "v1"

    arquivo.write_text("v2-maior")
    os.utime(arquivo, ns=(1, 1))

    assert cache.obter() == "v2-maior"
