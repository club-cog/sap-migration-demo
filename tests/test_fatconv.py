"""Uma regra do FATCONV por teste."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from servicos.fatconv import (
    GLOSA_FORA_PRAZO,
    GLOSA_GUIA_DUPLICADA,
    GLOSA_NAO_COBERTO,
    GLOSA_SEM_AUTORIZACAO,
    GLOSA_SEM_PRECO,
    ConvenioNaoCadastrado,
    NenhumAtendimentoAFaturar,
    faturar_convenio,
)
from servicos.modelos import Atendimento, Convenio, Preco, ResultadoFaturamento
from tests.conftest import atendimento, montar_base

ENVIO = date(2026, 9, 5)


def faturar(
    atendimentos: list[Atendimento], precos: list[Preco] | None = None, convenios: list[Convenio] | None = None
) -> ResultadoFaturamento:
    return faturar_convenio(montar_base(atendimentos, precos, convenios), "900", "202608", ENVIO, "000001")


def test_g05_sem_preco_na_tabela() -> None:
    item = faturar([atendimento(procedimento="99999999")]).itens[0]
    assert (item.motivo_glosa, item.valor_tabela, item.valor_glosa) == (GLOSA_SEM_PRECO, 0, 0)


def test_g05_preco_zero() -> None:
    item = faturar([atendimento()], precos=[Preco("900", "10101012", Decimal("0.00"), "S")]).itens[0]
    assert item.motivo_glosa == GLOSA_SEM_PRECO


def test_g02_nao_coberto() -> None:
    item = faturar([atendimento()], precos=[Preco("900", "10101012", Decimal("100.00"), "N")]).itens[0]
    assert (item.motivo_glosa, item.valor_glosa) == (GLOSA_NAO_COBERTO, Decimal("100.00"))


def test_g01_convenio_exige_senha() -> None:
    convenios = [Convenio("900", 30, Decimal("0"), "S")]
    assert faturar([atendimento(autorizacao="")], convenios=convenios).itens[0].motivo_glosa == GLOSA_SEM_AUTORIZACAO


def test_g01_convenio_sem_exigencia_nao_glosa_ate_1000() -> None:
    precos = [Preco("900", "10101012", Decimal("1000.00"), "S")]
    assert faturar([atendimento(autorizacao="")], precos=precos).itens[0].motivo_glosa == ""


def test_g01_chamado_48211_alto_custo_acima_de_1000_exige_senha() -> None:
    precos = [Preco("900", "10101012", Decimal("1000.01"), "S")]
    assert faturar([atendimento(autorizacao="")], precos=precos).itens[0].motivo_glosa == GLOSA_SEM_AUTORIZACAO


def test_g03_prazo_em_dias_corridos_estritamente_maior() -> None:
    no_limite = atendimento(numate="X0001", guia="G1", data=date(2026, 8, 6))  # 30 dias
    fora = atendimento(numate="X0002", guia="G2", data=date(2026, 8, 5))  # 31 dias
    itens = faturar([no_limite, fora]).itens
    assert [(i.numate, i.motivo_glosa) for i in itens] == [("X0002", GLOSA_FORA_PRAZO), ("X0001", "")]


def test_g04_primeira_guia_aceita_e_segunda_glosada() -> None:
    itens = faturar([atendimento(numate="X0001"), atendimento(numate="X0002")]).itens
    assert [i.motivo_glosa for i in itens] == ["", GLOSA_GUIA_DUPLICADA]


def test_g04_guia_glosada_tambem_conta_como_duplicidade() -> None:
    primeira = atendimento(numate="X0001", procedimento="99999999")
    itens = faturar([primeira, atendimento(numate="X0002")]).itens
    assert [i.motivo_glosa for i in itens] == [GLOSA_SEM_PRECO, GLOSA_GUIA_DUPLICADA]


def test_g04_compara_guia_sem_espacos() -> None:
    itens = faturar([atendimento(numate="X0001", guia="G9001  "), atendimento(numate="X0002")]).itens
    assert itens[1].motivo_glosa == GLOSA_GUIA_DUPLICADA


def test_ordem_de_precedencia_da_glosa() -> None:
    convenios = [Convenio("900", 30, Decimal("0"), "S")]
    precos = [Preco("900", "10101012", Decimal("100.00"), "N")]
    tudo_errado = atendimento(autorizacao="", data=date(2026, 8, 1))
    assert faturar([tudo_errado], precos, convenios).itens[0].motivo_glosa == GLOSA_NAO_COBERTO
    assert faturar([tudo_errado], None, convenios).itens[0].motivo_glosa == GLOSA_SEM_AUTORIZACAO


def test_ordem_do_indice_data_e_numero_define_duplicidade() -> None:
    depois = atendimento(numate="X0001", data=date(2026, 8, 20))
    antes = atendimento(numate="X0002", data=date(2026, 8, 10))
    itens = faturar([depois, antes]).itens
    assert [(i.numate, i.motivo_glosa) for i in itens] == [("X0002", ""), ("X0001", GLOSA_GUIA_DUPLICADA)]


def test_aditivo_2021_04_desconto_saude_mais_em_consultas() -> None:
    base = montar_base(
        [atendimento(convenio="005"), atendimento(numate="X0002", guia="G2", convenio="005", procedimento="10101039")],
        precos=[Preco("005", "10101012", Decimal("140.00"), "S"), Preco("005", "10101039", Decimal("160.00"), "S")],
        convenios=[Convenio("005", 30, Decimal("10"), "N")],
    )
    itens = faturar_convenio(base, "005", "202608", ENVIO, "000001").itens
    assert [(i.valor_desconto, i.valor_coparticipacao, i.valor_faturado) for i in itens] == [
        (Decimal("14.00"), Decimal("12.60"), Decimal("113.40")),
        (Decimal("16.00"), Decimal("14.40"), Decimal("129.60")),
    ]


def test_desconto_nao_se_aplica_a_outros_convenios_nem_exames() -> None:
    assert faturar([atendimento()]).itens[0].valor_desconto == 0
    base = montar_base(
        [atendimento(convenio="005", procedimento="40901122")],
        precos=[Preco("005", "40901122", Decimal("230.00"), "S")],
        convenios=[Convenio("005", 30, Decimal("0"), "N")],
    )
    assert faturar_convenio(base, "005", "202608", ENVIO, "000001").itens[0].valor_desconto == 0


def test_coparticipacao_arredondada_sobre_tabela_menos_desconto() -> None:
    convenios = [Convenio("900", 30, Decimal("20"), "N")]
    precos = [Preco("900", "10101012", Decimal("10.03"), "S")]
    item = faturar([atendimento()], precos, convenios).itens[0]
    assert (item.valor_coparticipacao, item.valor_faturado) == (Decimal("2.01"), Decimal("8.02"))


def test_item_glosado_zera_desconto_coparticipacao_e_faturado() -> None:
    convenios = [Convenio("900", 30, Decimal("20"), "S")]
    item = faturar([atendimento(autorizacao="")], convenios=convenios).itens[0]
    assert (item.valor_desconto, item.valor_coparticipacao, item.valor_faturado, item.valor_glosa) == (
        0,
        0,
        0,
        Decimal("100.00"),
    )


@pytest.mark.parametrize(
    "ignorado",
    [
        atendimento(numate="X0009", tipo="P"),
        atendimento(numate="X0009", status="C"),
        atendimento(numate="X0009", fatura="000099"),
        atendimento(numate="X0009", data=date(2026, 7, 31)),
        atendimento(numate="X0009", convenio="901"),
    ],
)
def test_filtro_tipo_status_fatura_competencia_convenio(ignorado: Atendimento) -> None:
    itens = faturar([atendimento(guia="G1"), ignorado]).itens
    assert [i.numate for i in itens] == ["X0001"]


def test_totais_do_lote_e_atualizacao_z1_fatura() -> None:
    resultado = faturar([atendimento(numate="X0001"), atendimento(numate="X0002")])
    lote = resultado.lote
    assert (lote.qtd_guias, lote.valor_bruto, lote.valor_faturado, lote.valor_glosa) == (
        2,
        Decimal("200.00"),
        Decimal("100.00"),
        Decimal("100.00"),
    )
    assert resultado.faturados == {"X0001": "000001", "X0002": "000001"}


def test_convenio_nao_cadastrado() -> None:
    with pytest.raises(ConvenioNaoCadastrado):
        faturar_convenio(montar_base([atendimento()]), "777", "202608", ENVIO, "000001")


def test_nenhum_atendimento_a_faturar() -> None:
    with pytest.raises(NenhumAtendimentoAFaturar):
        faturar([atendimento(status="C")])
