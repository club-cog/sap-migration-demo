from fastapi.testclient import TestClient

from servicos.api import app

client = TestClient(app)


def test_lotes() -> None:
    r = client.post("/faturamento/202608/lotes", params={"data_envio": "2026-09-05"})
    assert r.status_code == 200
    assert [lt["vl_faturado"] for lt in r.json()] == ["1748.50", "1126.40", "1728.90"]


def test_titulos_particular_rejeitado() -> None:
    r = client.post("/atendimentos/A0030/titulos")
    assert r.status_code == 422
    assert r.json()["detail"] == "PARCELAS_INVALIDAS"


def test_titulos_particular_inexistente() -> None:
    assert client.post("/atendimentos/X9999/titulos").status_code == 404
