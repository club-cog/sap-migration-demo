"""LGPD: nenhum log ou exceção expõe CPF, nome de paciente, razão social ou CNPJ."""

from __future__ import annotations

import logging
from datetime import date

import pytest

from servicos.competencia import processar_competencia
from servicos.dados import DIR_DADOS, carregar_base, ler_csv
from servicos.fatconv import ConvenioNaoCadastrado, faturar_convenio


def dados_pessoais() -> list[str]:
    pacientes = ler_csv(DIR_DADOS / "SA1_pacientes.csv")
    medicos = ler_csv(DIR_DADOS / "SZ4_regras_repasse.csv")
    return (
        [p["A1_CGC"] for p in pacientes]
        + [p["A1_NOME"] for p in pacientes]
        + [m["Z4_CNPJ"] for m in medicos]
        + [m["Z4_NOME"] for m in medicos]
    )


def test_logs_da_competencia_sem_dado_pessoal(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        processar_competencia(carregar_base(), "202608", date(2026, 9, 5))

    assert caplog.records, "o processamento deve gerar log de auditoria"
    texto = caplog.text
    for dado in dados_pessoais():
        assert dado not in texto
    assert "A0001" in texto


def test_logs_nao_registram_guia() -> None:
    base = carregar_base()
    guias = {a.guia for a in base.atendimentos if a.guia}
    registros: list[str] = []

    class Coletor(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registros.append(record.getMessage())

    coletor = Coletor(level=logging.DEBUG)
    raiz = logging.getLogger("servicos")
    nivel_original = raiz.level
    raiz.addHandler(coletor)
    raiz.setLevel(logging.DEBUG)
    try:
        processar_competencia(base, "202608", date(2026, 9, 5))
    finally:
        raiz.removeHandler(coletor)
        raiz.setLevel(nivel_original)
    assert registros
    assert not any(guia in mensagem for mensagem in registros for guia in guias)


def test_base_carregada_nao_contem_dado_pessoal() -> None:
    base = carregar_base()
    representacao = repr(base)
    for dado in dados_pessoais():
        assert dado not in representacao


def test_excecao_sem_dado_pessoal() -> None:
    with pytest.raises(ConvenioNaoCadastrado) as erro:
        faturar_convenio(carregar_base(), "777", "202608", date(2026, 9, 5), "000001")
    assert str(erro.value) == "Convenio 777 nao cadastrado."
