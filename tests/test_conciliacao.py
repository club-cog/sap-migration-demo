from __future__ import annotations

from pathlib import Path

from servicos.conciliacao import conciliar
from servicos.dados import gravar_csv

COLUNAS = ("Z8_NUMATE", "Z8_MOTIVO")
CHAVE = ("Z8_NUMATE",)


def _referencia(tmp_path: Path, linhas: list[dict[str, str]]) -> Path:
    gravar_csv(tmp_path / "SZ8.csv", COLUNAS, linhas)
    return tmp_path


def test_chave_duplicada_compara_todas_as_linhas(tmp_path: Path) -> None:
    _referencia(tmp_path, [{"Z8_NUMATE": "A1", "Z8_MOTIVO": "SEM_PRECO"}, {"Z8_NUMATE": "A1", "Z8_MOTIVO": "X"}])
    geradas = [{"Z8_NUMATE": "A1", "Z8_MOTIVO": "FORMA_INVALIDA"}, {"Z8_NUMATE": "A1", "Z8_MOTIVO": "X"}]

    resultado = conciliar("SZ8", COLUNAS, CHAVE, geradas, "SZ8.csv", tmp_path)

    assert not resultado.paridade
    assert resultado.campos_comparados == 4
    assert [(d.campo, d.gerado, d.referencia) for d in resultado.divergencias] == [
        ("Z8_MOTIVO", "FORMA_INVALIDA", "SEM_PRECO")
    ]


def test_linha_duplicada_a_mais_gera_divergencia(tmp_path: Path) -> None:
    diretorio = _referencia(tmp_path, [{"Z8_NUMATE": "A1", "Z8_MOTIVO": "X"}, {"Z8_NUMATE": "A2", "Z8_MOTIVO": "Y"}])
    geradas = [{"Z8_NUMATE": "A1", "Z8_MOTIVO": "X"}, {"Z8_NUMATE": "A1", "Z8_MOTIVO": "X"}]

    resultado = conciliar("SZ8", COLUNAS, CHAVE, geradas, "SZ8.csv", diretorio)

    assert not resultado.paridade
    assert {d.chave for d in resultado.divergencias} == {("A1",), ("A2",)}
