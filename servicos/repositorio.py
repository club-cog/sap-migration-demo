import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from servicos.modelos import Atendimento, Convenio, Paciente, Preco, RegraRepasse
from servicos.util import para_data

DADOS_LEGADO = Path(__file__).resolve().parent.parent / "legacy" / "dados"


def _ler(pasta: Path, arquivo: str) -> list[dict[str, str]]:
    with open(pasta / arquivo, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


@dataclass(frozen=True)
class BaseLegado:
    """Extração das tabelas do Protheus (SA1, SZ1..SZ4) em memória."""

    pacientes: dict[str, Paciente]
    convenios: dict[str, Convenio]
    precos: dict[tuple[str, str], Preco]
    regras_repasse: dict[str, RegraRepasse]
    atendimentos: tuple[Atendimento, ...]

    @classmethod
    def carregar(cls, pasta: Path = DADOS_LEGADO) -> "BaseLegado":
        pacientes = {
            r["A1_COD"]: Paciente(r["A1_COD"], r["A1_NOME"], r["A1_CGC"]) for r in _ler(pasta, "SA1_pacientes.csv")
        }
        convenios = {
            r["Z2_COD"]: Convenio(
                codigo=r["Z2_COD"],
                nome=r["Z2_NOME"],
                prazo_dias=int(r["Z2_PRAZO"]),
                copart_perc=Decimal(r["Z2_COPART"]),
                exige_autorizacao=r["Z2_EXIGAUT"] == "S",
            )
            for r in _ler(pasta, "SZ2_convenios.csv")
        }
        precos = {
            (r["Z3_CONVEN"], r["Z3_PROCED"]): Preco(
                convenio=r["Z3_CONVEN"],
                procedimento=r["Z3_PROCED"],
                descricao=r["Z3_DESCRI"],
                valor=Decimal(r["Z3_VALOR"]),
                coberto=r["Z3_COBERTO"] == "S",
            )
            for r in _ler(pasta, "SZ3_tabela_precos.csv")
        }
        regras = {
            r["Z4_MEDICO"]: RegraRepasse(
                medico=r["Z4_MEDICO"],
                nome=r["Z4_NOME"],
                cnpj=r["Z4_CNPJ"],
                especialidade=r["Z4_ESPEC"],
                perc=Decimal(r["Z4_PERC"]),
                retem_iss=r["Z4_MUNISS"] == "S",
            )
            for r in _ler(pasta, "SZ4_regras_repasse.csv")
        }
        atendimentos = tuple(
            Atendimento(
                numero=r["Z1_NUMATE"],
                data=para_data(r["Z1_DATA"]),
                paciente=r["Z1_PACIENT"],
                tipo=r["Z1_TIPO"],
                convenio=r["Z1_CONVEN"],
                procedimento=r["Z1_PROCED"],
                medico=r["Z1_MEDICO"],
                guia=r["Z1_GUIA"],
                autorizacao=r["Z1_AUTORIZ"],
                status=r["Z1_STATUS"],
                forma_pagamento=r["Z1_FORMPG"],
                parcelas=r["Z1_PARCELA"],
            )
            for r in _ler(pasta, "SZ1_atendimentos.csv")
        )
        return cls(pacientes, convenios, precos, regras, atendimentos)
