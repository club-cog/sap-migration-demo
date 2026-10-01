from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

from servicos.competencia import SaidasCompetencia, main, marcar_faturados, processar_competencia
from servicos.dados import DIR_DADOS, LAYOUT_SZ5, LAYOUT_SZ6, carregar_feriados, ler_csv
from servicos.modelos import BaseProtheus
from tests.conftest import COMPETENCIA, DATA_ENVIO


def test_faturados_marcam_z1_fatura(base_protheus: BaseProtheus, saidas: SaidasCompetencia) -> None:
    assert set(saidas.faturados) == {i.numate for i in saidas.itens_lote}
    atualizada = marcar_faturados(base_protheus, saidas.faturados)
    faturas = {a.numate: a.fatura for a in atualizada.atendimentos}
    assert faturas["A0001"] == "000001"
    assert all(not faturas[a.numate] for a in base_protheus.atendimentos if a.numate not in saidas.faturados)


def test_reprocessar_com_z1_fatura_nao_fatura_de_novo(base_protheus: BaseProtheus, saidas: SaidasCompetencia) -> None:
    atualizada = marcar_faturados(base_protheus, saidas.faturados)

    nova = processar_competencia(atualizada, COMPETENCIA, DATA_ENVIO, (), saidas.lotes, saidas.itens_lote)

    assert nova.lotes == []
    assert nova.itens_lote == []


def test_repasse_usa_sz6_de_execucoes_anteriores(base_protheus: BaseProtheus, saidas: SaidasCompetencia) -> None:
    atualizada = marcar_faturados(base_protheus, saidas.faturados)

    nova = processar_competencia(atualizada, COMPETENCIA, DATA_ENVIO, (), saidas.lotes, saidas.itens_lote)

    assert nova.itens_repasse == saidas.itens_repasse
    assert nova.titulos_pagar == saidas.titulos_pagar


def test_numeracao_de_lote_continua_do_historico(base_protheus: BaseProtheus, saidas: SaidasCompetencia) -> None:
    nova = processar_competencia(base_protheus, "202608", date(2026, 9, 5), (), saidas.lotes)

    assert [lote.lote for lote in nova.lotes] == ["000004", "000005", "000006"]
    assert {i.lote for i in nova.itens_lote} == {"000004", "000005", "000006"}


def test_feriados_configurados_mantem_paridade(base_protheus: BaseProtheus, saidas: SaidasCompetencia) -> None:
    com_feriados = processar_competencia(base_protheus, COMPETENCIA, DATA_ENVIO, carregar_feriados())

    assert com_feriados == saidas


def _rodar_cli(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["servicos.competencia", *args])
    main()


def test_reprocessamento_no_mesmo_diretorio_preserva_lotes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reprocessar com --historico apontando para a saída não apaga o SZ5/SZ6 já gravado."""
    saida = tmp_path / "saidas"
    _rodar_cli(monkeypatch, [COMPETENCIA, "20260905", str(saida)])
    lotes = (saida / LAYOUT_SZ5.arquivo).read_text(encoding="utf-8")
    itens = (saida / LAYOUT_SZ6.arquivo).read_text(encoding="utf-8")

    dados = tmp_path / "dados"
    dados.mkdir()
    shutil.copy(saida / "SZ1_atendimentos.csv", dados)
    for arquivo in ("SZ2_convenios.csv", "SZ3_tabela_precos.csv", "SZ4_regras_repasse.csv"):
        shutil.copy(DIR_DADOS / arquivo, dados)

    _rodar_cli(
        monkeypatch,
        [COMPETENCIA, "20260905", str(saida), "--dados", str(dados), "--historico", str(saida)],
    )

    assert (saida / LAYOUT_SZ5.arquivo).read_text(encoding="utf-8") == lotes
    assert (saida / LAYOUT_SZ6.arquivo).read_text(encoding="utf-8") == itens
    linhas = ler_csv(saida / LAYOUT_SZ5.arquivo)
    assert {linha["Z5_LOTE"] for linha in linhas} == {"000001", "000002", "000003"}
