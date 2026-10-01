"""Conciliação campo a campo com legacy/saidas_referencia (competência 08/2026, envio 05/09/2026)."""

from __future__ import annotations

from pathlib import Path

import pytest

from servicos.competencia import SaidasCompetencia, conciliar_saidas
from servicos.conciliacao import conciliar
from servicos.dados import DIR_REFERENCIA, gravar_csv

TABELAS = ["SZ5", "SZ6", "SZ7", "SZ8", "SE1", "SE2"]


@pytest.mark.parametrize("tabela", TABELAS)
def test_paridade_campo_a_campo(saidas: SaidasCompetencia, tabela: str) -> None:
    colunas, chave, arquivo, linhas = saidas.tabelas()[tabela]
    resultado = conciliar(tabela, colunas, chave, linhas, arquivo)

    assert resultado.colunas_iguais
    assert resultado.linhas_geradas == resultado.linhas_referencia
    assert resultado.divergencias == []
    assert resultado.paridade


@pytest.mark.parametrize("tabela", TABELAS)
def test_arquivo_gerado_identico_ao_protheus(saidas: SaidasCompetencia, tabela: str, tmp_path: Path) -> None:
    colunas, _, arquivo, linhas = saidas.tabelas()[tabela]
    gravar_csv(tmp_path / arquivo, colunas, linhas)

    assert (tmp_path / arquivo).read_bytes() == (DIR_REFERENCIA / arquivo).read_bytes()


def test_conciliacao_cobre_todas_as_tabelas_de_referencia(saidas: SaidasCompetencia) -> None:
    arquivos = {arquivo for _, _, arquivo, _ in saidas.tabelas().values()}
    assert arquivos == {p.name for p in DIR_REFERENCIA.glob("*.csv")}
    assert all(c.paridade for c in conciliar_saidas(saidas))


def test_conciliacao_detecta_divergencia(saidas: SaidasCompetencia) -> None:
    colunas, chave, arquivo, linhas = saidas.tabelas()["SE2"]
    adulteradas = [dict(linha) for linha in linhas]
    adulteradas[0]["E2_ISS"] = "29.95"

    resultado = conciliar("SE2", colunas, chave, adulteradas, arquivo)

    assert not resultado.paridade
    assert [(d.campo, d.gerado, d.referencia) for d in resultado.divergencias] == [("E2_ISS", "29.95", "29.94")]
