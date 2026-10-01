from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from servicos import faturamento_convenio as fat
from servicos import repasse_medico as rep
from servicos import titulos_particular as tit
from servicos.modelos import Rejeicao
from servicos.repositorio import BaseLegado
from servicos.util import arredonda, proximo_dia_util, trunca

ENVIO = date(2026, 9, 5)


@pytest.fixture(scope="module")
def base() -> BaseLegado:
    return BaseLegado.carregar()


def _item(base: BaseLegado, convenio: str, numero: str) -> fat.ItemLote:
    lote = fat.gerar_lote(base, "000001", convenio, "202608", ENVIO)
    assert lote is not None
    return next(i for i in lote.itens if i.atendimento == numero)


def test_arredondamento_igual_advpl() -> None:
    assert arredonda(Decimal("0.125")) == Decimal("0.13")
    assert trunca(Decimal("161.4275")) == Decimal("161.42")


def test_dia_util_pula_fim_de_semana() -> None:
    assert proximo_dia_util(date(2026, 8, 29)) == date(2026, 8, 31)


def test_convenio_inexistente(base: BaseLegado) -> None:
    with pytest.raises(fat.ConvenioNaoCadastrado):
        fat.gerar_lote(base, "000001", "999", "202608", ENVIO)


@pytest.mark.parametrize(
    "convenio,numero,motivo",
    [
        ("001", "A0003", fat.SEM_AUTORIZACAO),
        ("002", "A0012", fat.NAO_COBERTO),
        ("002", "A0013", fat.SEM_AUTORIZACAO),  # alto custo sem senha, mesmo sem exigência contratual
        ("005", "A0017", fat.FORA_DO_PRAZO),
        ("001", "A0006", fat.GUIA_DUPLICADA),
        ("001", "A0001", ""),
    ],
)
def test_motivos_de_glosa(base: BaseLegado, convenio: str, numero: str, motivo: str) -> None:
    assert _item(base, convenio, numero).motivo_glosa == motivo


def test_cancelado_e_fora_da_competencia_nao_entram(base: BaseLegado) -> None:
    lote = fat.gerar_lote(base, "000001", "001", "202608", ENVIO)
    assert lote is not None
    assert {"A0008", "A0009"}.isdisjoint(i.atendimento for i in lote.itens)


def test_desconto_contratual_saude_mais(base: BaseLegado) -> None:
    item = _item(base, "005", "A0018")
    assert (item.vl_desconto, item.vl_copart, item.vl_faturado) == (
        Decimal("14.00"),
        Decimal("12.60"),
        Decimal("113.40"),
    )


def test_repasse_ignora_laboratorio_e_glosa(base: BaseLegado) -> None:
    lotes = fat.gerar_lotes_competencia(base, "202608", ENVIO)
    atendimentos = {i.atendimento for i in rep.calcular_itens(base, "202608", lotes)}
    assert {"A0002", "A0011", "A0019", "A0029"}.isdisjoint(atendimentos)  # laboratório
    assert {"A0003", "A0013", "A0017"}.isdisjoint(atendimentos)  # glosados


def test_irrf_dispensado_ate_dez_reais(base: BaseLegado) -> None:
    lotes = fat.gerar_lotes_competencia(base, "202608", ENVIO)
    titulos = rep.gerar_titulos(base, "202608", rep.calcular_itens(base, "202608", lotes))
    m01 = next(t for t in titulos if t.fornecedor == "M01")
    assert m01.irrf == Decimal("0") and m01.pis > 0


def test_cartao_acima_de_tres_parcelas_rejeita(base: BaseLegado) -> None:
    atendimento = next(a for a in base.atendimentos if a.numero == "A0030")
    assert tit.gerar_titulos(base, atendimento) == Rejeicao("A0030", "PARCELAS_INVALIDAS")


def test_centavos_na_primeira_parcela(base: BaseLegado) -> None:
    atendimento = next(a for a in base.atendimentos if a.numero == "A0025")
    titulos = tit.gerar_titulos(base, atendimento)
    assert isinstance(titulos, list)
    assert [t.valor for t in titulos] == [Decimal("86.68"), Decimal("86.66"), Decimal("86.66")]


def test_forma_invalida(base: BaseLegado) -> None:
    atendimento = replace(next(a for a in base.atendimentos if a.numero == "A0024"), forma_pagamento="CHEQUE")
    assert tit.gerar_titulos(base, atendimento) == Rejeicao("A0024", "FORMA_INVALIDA")
