from __future__ import annotations

from datetime import date

from servicos.competencia import SaidasCompetencia, marcar_faturados, processar_competencia
from servicos.dados import carregar_feriados
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
