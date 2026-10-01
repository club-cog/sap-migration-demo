"""Uma regra do REPMED por teste."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from servicos.modelos import ItemLote, Preco, RegraRepasse
from servicos.repmed import calcular_repasse, calcular_retencoes, datas_titulo
from tests.conftest import atendimento, montar_base

D = Decimal


def item_lote(numate: str = "X0001", tabela: str = "100.00", desconto: str = "0.00", motivo: str = "") -> ItemLote:
    return ItemLote("000001", numate, "G1", "10101012", D(tabela), D(desconto), D("0"), D("0"), D("0"), motivo)


def test_base_convenio_tabela_menos_desconto_com_coparticipacao() -> None:
    base = montar_base([atendimento()])
    lote = [ItemLote("000001", "X0001", "G1", "10101012", D("140.00"), D("14.00"), D("12.60"), D("113.40"), D(0), "")]
    item = calcular_repasse(base, "202608", lote).itens[0]
    assert (item.base, item.valor) == (D("126.00"), D("63.00"))


def test_item_glosado_nao_gera_repasse() -> None:
    resultado = calcular_repasse(montar_base([atendimento()]), "202608", [item_lote(motivo="G01")])
    assert resultado.itens == [] and resultado.titulos == []


def test_convenio_nao_faturado_nao_gera_repasse() -> None:
    assert calcular_repasse(montar_base([atendimento()]), "202608", []).itens == []


def test_particular_repassa_sobre_tabela_par() -> None:
    base = montar_base([atendimento(tipo="P", convenio="PAR", forma_pagamento="PIX")])
    assert calcular_repasse(base, "202608", []).itens[0].base == D("100.00")


def test_particular_sem_preco_nao_gera_repasse() -> None:
    base = montar_base([atendimento(tipo="P", convenio="PAR", procedimento="99999999")])
    assert calcular_repasse(base, "202608", []).itens == []


def test_particular_rejeitado_no_financeiro_entra_no_repasse() -> None:
    base = montar_base([atendimento(tipo="P", convenio="PAR", forma_pagamento="CARTAO", parcelas="4")])
    assert [i.numate for i in calcular_repasse(base, "202608", []).itens] == ["X0001"]


def test_laboratorio_proprio_prefixo_4030_sem_repasse() -> None:
    atendimentos = [
        atendimento(numate="X0001", tipo="P", convenio="PAR", procedimento="40304361"),
        atendimento(numate="X0002", tipo="P", convenio="PAR", procedimento="40302040"),
        atendimento(numate="X0003", tipo="P", convenio="PAR", procedimento="40901122"),
    ]
    precos = [Preco("PAR", p, D("50.00"), "S") for p in ("40304361", "40302040", "40901122")]
    assert [i.numate for i in calcular_repasse(montar_base(atendimentos, precos), "202608", []).itens] == ["X0003"]


def test_adicional_de_plantao_mais_5_pontos() -> None:
    base = montar_base(
        [atendimento(tipo="P", convenio="PAR", procedimento="10101039")],
        precos=[Preco("PAR", "10101039", D("189.00"), "S")],
    )
    item = calcular_repasse(base, "202608", []).itens[0]
    assert (item.percentual, item.valor) == (D("55"), D("103.95"))


def test_valor_do_item_arredondado() -> None:
    base = montar_base(
        [atendimento(tipo="P", convenio="PAR")],
        precos=[Preco("PAR", "10101012", D("149.00"), "S")],
        regras=[RegraRepasse("M90", D("55"), "N")],
    )
    assert calcular_repasse(base, "202608", []).itens[0].valor == D("81.95")


def test_filtros_status_competencia_e_medico_sem_regra() -> None:
    atendimentos = [
        atendimento(numate="X0001", tipo="P", convenio="PAR", status="C"),
        atendimento(numate="X0002", tipo="P", convenio="PAR", data=date(2026, 9, 1)),
        atendimento(numate="X0003", tipo="P", convenio="PAR", medico="M99"),
        atendimento(numate="X0004", tipo="P", convenio="PAR"),
    ]
    assert [i.numate for i in calcular_repasse(montar_base(atendimentos), "202608", []).itens] == ["X0004"]


def test_um_titulo_por_medico_ordenado_pelo_codigo() -> None:
    atendimentos = [
        atendimento(numate="X0001", tipo="P", convenio="PAR", medico="M91"),
        atendimento(numate="X0002", tipo="P", convenio="PAR", medico="M90"),
        atendimento(numate="X0003", tipo="P", convenio="PAR", medico="M90"),
    ]
    regras = [RegraRepasse("M90", D("50"), "N"), RegraRepasse("M91", D("50"), "N")]
    titulos = calcular_repasse(montar_base(atendimentos, regras=regras), "202608", []).titulos
    assert [(t.fornecedor, t.valor_bruto) for t in titulos] == [("M90", D("100.00")), ("M91", D("50.00"))]
    assert {(t.prefixo, t.numero, t.parcela, t.tipo) for t in titulos} == {("REP", "202608", " ", "NF")}


def test_irrf_dispensado_ate_10_reais() -> None:
    assert calcular_retencoes(D("666.66"), "N").irrf == 0  # 9,9999 -> 10,00: dispensa (<=)
    assert calcular_retencoes(D("667.00"), "N").irrf == D("10.01")


def test_csrf_dispensada_quando_soma_ate_10_reais() -> None:
    dispensada = calcular_retencoes(D("215.00"), "N")  # 1,40 + 6,45 + 2,15 = 10,00
    assert (dispensada.pis, dispensada.cofins, dispensada.csll) == (0, 0, 0)
    retida = calcular_retencoes(D("216.00"), "N")
    assert (retida.pis, retida.cofins, retida.csll) == (D("1.40"), D("6.48"), D("2.16"))


def test_iss_truncado_quando_municipio_exige() -> None:
    assert calcular_retencoes(D("3228.55"), "S").iss == D("161.42")  # Round daria 161,43
    assert calcular_retencoes(D("3228.55"), "N").iss == 0


def test_liquido_desconta_todas_as_retencoes() -> None:
    base = montar_base(
        [atendimento(tipo="P", convenio="PAR")],
        precos=[Preco("PAR", "10101012", D("6457.10"), "S")],
        regras=[RegraRepasse("M90", D("50"), "S")],
    )
    titulo = calcular_repasse(base, "202608", []).titulos[0]
    assert (titulo.valor_bruto, titulo.irrf, titulo.pis, titulo.cofins, titulo.csll, titulo.iss, titulo.valor) == (
        D("3228.55"),
        D("48.43"),
        D("20.99"),
        D("96.86"),
        D("32.29"),
        D("161.42"),
        D("2868.56"),
    )


def test_emissao_ultimo_dia_e_vencimento_dia_15_proximo_dia_util() -> None:
    assert datas_titulo("202608") == (date(2026, 8, 31), date(2026, 9, 15))
    assert datas_titulo("202607") == (date(2026, 7, 31), date(2026, 8, 17))  # 15/08/2026 é sábado
    assert datas_titulo("202608", feriados=[date(2026, 9, 15)]) == (date(2026, 8, 31), date(2026, 9, 16))
    assert datas_titulo("202612") == (date(2026, 12, 31), date(2027, 1, 15))
