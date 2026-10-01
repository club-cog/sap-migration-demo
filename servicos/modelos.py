"""Modelos de entrada e saída no layout das tabelas do Protheus (SZ1..SZ8, SE1, SE2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Atendimento:
    """SZ1 - Atendimentos."""

    numate: str
    data: date
    paciente: str
    tipo: str
    convenio: str
    procedimento: str
    medico: str
    guia: str
    autorizacao: str
    status: str
    forma_pagamento: str
    parcelas: str
    fatura: str = ""


@dataclass(frozen=True)
class Convenio:
    """SZ2 - Convênios."""

    codigo: str
    prazo_dias: int
    coparticipacao: Decimal
    exige_autorizacao: str


@dataclass(frozen=True)
class Preco:
    """SZ3 - Tabela de preços por convênio."""

    convenio: str
    procedimento: str
    valor: Decimal
    coberto: str


@dataclass(frozen=True)
class RegraRepasse:
    """SZ4 - Regra de repasse do médico (PJ). Razão social e CNPJ não são carregados (minimização LGPD)."""

    medico: str
    percentual: Decimal
    retem_iss: str


@dataclass(frozen=True)
class BaseProtheus:
    """Extração das tabelas de entrada, indexadas pelas chaves usadas nos `DbSeek` do legado."""

    atendimentos: tuple[Atendimento, ...]
    convenios: dict[str, Convenio]
    precos: dict[tuple[str, str], Preco]
    regras_repasse: dict[str, RegraRepasse]


@dataclass(frozen=True)
class LoteFaturamento:
    """SZ5 - Lote de faturamento (cabeçalho)."""

    lote: str
    convenio: str
    competencia: str
    data_envio: date
    qtd_guias: int
    valor_bruto: Decimal
    valor_desconto: Decimal
    valor_coparticipacao: Decimal
    valor_faturado: Decimal
    valor_glosa: Decimal


@dataclass(frozen=True)
class ItemLote:
    """SZ6 - Item do lote de faturamento."""

    lote: str
    numate: str
    guia: str
    procedimento: str
    valor_tabela: Decimal
    valor_desconto: Decimal
    valor_coparticipacao: Decimal
    valor_faturado: Decimal
    valor_glosa: Decimal
    motivo_glosa: str


@dataclass(frozen=True)
class ItemRepasse:
    """SZ7 - Memória de cálculo do repasse."""

    competencia: str
    medico: str
    numate: str
    procedimento: str
    base: Decimal
    percentual: Decimal
    valor: Decimal


@dataclass(frozen=True)
class TituloPagar:
    """SE2 - Título a pagar do repasse médico."""

    prefixo: str
    numero: str
    parcela: str
    tipo: str
    fornecedor: str
    emissao: date
    vencimento: date
    valor_bruto: Decimal
    irrf: Decimal
    pis: Decimal
    cofins: Decimal
    csll: Decimal
    iss: Decimal
    valor: Decimal


@dataclass(frozen=True)
class TituloReceber:
    """SE1 - Título a receber de atendimento particular."""

    prefixo: str
    numero: str
    parcela: str
    tipo: str
    cliente: str
    emissao: date
    vencimento: date
    valor: Decimal


@dataclass(frozen=True)
class Rejeicao:
    """SZ8 - Atendimento rejeitado na integração financeira."""

    numate: str
    motivo: str


@dataclass(frozen=True)
class ResultadoFaturamento:
    """Saída do FATCONV: SZ5, SZ6 e a atualização de Z1_FATURA (numate -> lote)."""

    lote: LoteFaturamento
    itens: list[ItemLote]
    faturados: dict[str, str]


@dataclass(frozen=True)
class ResultadoRepasse:
    """Saída do REPMED: SE2 e SZ7."""

    titulos: list[TituloPagar]
    itens: list[ItemRepasse]


@dataclass(frozen=True)
class ResultadoTitulosReceber:
    """Saída do ZAGEFIN: retorno lógico do ponto de entrada, SE1 e SZ8."""

    gerou: bool
    titulos: list[TituloReceber] = field(default_factory=list)
    rejeicao: Rejeicao | None = None
