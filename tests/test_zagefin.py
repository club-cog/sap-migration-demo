"""Uma regra do ZAGEFIN por teste."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from servicos.modelos import Atendimento, Preco, ResultadoTitulosReceber
from servicos.zagefin import gerar_titulos_receber
from tests.conftest import atendimento, montar_base

D = Decimal


def gerar(at: Atendimento, valor: str = "260.00", feriados: tuple[date, ...] = ()) -> ResultadoTitulosReceber:
    base = montar_base([at], precos=[Preco("PAR", "10101012", D(valor), "S")])
    return gerar_titulos_receber(base, at.numate, feriados)


def particular(**campos: object) -> Atendimento:
    return atendimento(**{"tipo": "P", "convenio": "PAR", "data": date(2026, 8, 6), **campos})


def test_pix_5_por_cento_de_desconto_vencimento_no_dia() -> None:
    titulo = gerar(particular(forma_pagamento="PIX"), "149.00").titulos[0]
    assert (titulo.parcela, titulo.tipo, titulo.valor, titulo.vencimento) == (" ", "PIX", D("141.55"), date(2026, 8, 6))


def test_cartao_3x_parcela_truncada_e_centavos_na_primeira() -> None:
    titulos = gerar(particular(forma_pagamento="CARTAO", parcelas="3")).titulos
    assert [(t.parcela, t.tipo, t.valor, t.vencimento) for t in titulos] == [
        ("A", "CC", D("86.68"), date(2026, 9, 5)),
        ("B", "CC", D("86.66"), date(2026, 10, 5)),
        ("C", "CC", D("86.66"), date(2026, 11, 4)),
    ]


def test_cartao_1x_parcela_em_branco() -> None:
    titulos = gerar(particular(forma_pagamento="CARTAO", parcelas="1")).titulos
    assert [(t.parcela, t.valor) for t in titulos] == [(" ", D("260.00"))]


def test_cartao_vencimento_em_dias_corridos_sem_ajuste_de_dia_util() -> None:
    titulos = gerar(particular(forma_pagamento="CARTAO", parcelas="2", data=date(2026, 8, 12))).titulos
    assert titulos[1].vencimento == date(2026, 10, 11)  # domingo


@pytest.mark.parametrize("parcelas", ["0", "4", "", "X"])
def test_cartao_parcelas_invalidas(parcelas: str) -> None:
    resultado = gerar(particular(forma_pagamento="CARTAO", parcelas=parcelas))
    assert not resultado.gerou and resultado.titulos == []
    assert resultado.rejeicao is not None and resultado.rejeicao.motivo == "PARCELAS_INVALIDAS"


def test_boleto_3_dias_proximo_dia_util() -> None:
    assert gerar(particular(forma_pagamento="BOLETO", data=date(2026, 8, 7))).titulos[0].vencimento == date(2026, 8, 10)
    assert gerar(particular(forma_pagamento="BOLETO", data=date(2026, 8, 26))).titulos[0].vencimento == date(
        2026, 8, 31
    )
    titulo = gerar(particular(forma_pagamento="BOLETO", data=date(2026, 9, 4)), feriados=(date(2026, 9, 7),)).titulos[0]
    assert (titulo.tipo, titulo.valor, titulo.vencimento) == ("BOL", D("260.00"), date(2026, 9, 8))


def test_forma_de_pagamento_com_espacos_e_aceita() -> None:
    assert gerar(particular(forma_pagamento="PIX   ")).gerou


def test_forma_invalida() -> None:
    resultado = gerar(particular(forma_pagamento="pix"))
    assert resultado.rejeicao is not None and resultado.rejeicao.motivo == "FORMA_INVALIDA"


def test_sem_preco_particular() -> None:
    base = montar_base([particular(forma_pagamento="PIX", procedimento="99999999")])
    resultado = gerar_titulos_receber(base, "X0001")
    assert resultado.rejeicao is not None and resultado.rejeicao.motivo == "SEM_PRECO"


def test_atendimento_de_convenio_ou_inexistente_retorna_falso_sem_rejeicao() -> None:
    assert gerar(atendimento()) == ResultadoTitulosReceber(gerou=False)
    assert gerar_titulos_receber(montar_base([]), "X0001") == ResultadoTitulosReceber(gerou=False)


def test_titulo_leva_prefixo_numero_cliente_e_emissao_do_atendimento() -> None:
    titulo = gerar(particular(forma_pagamento="PIX")).titulos[0]
    assert (titulo.prefixo, titulo.numero, titulo.cliente, titulo.emissao) == ("ATE", "X0001", "P900", date(2026, 8, 6))
