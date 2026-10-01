from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Paciente:
    codigo: str
    nome: str
    cpf: str


@dataclass(frozen=True)
class Convenio:
    codigo: str
    nome: str
    prazo_dias: int
    copart_perc: Decimal
    exige_autorizacao: bool


@dataclass(frozen=True)
class Preco:
    convenio: str
    procedimento: str
    descricao: str
    valor: Decimal
    coberto: bool


@dataclass(frozen=True)
class RegraRepasse:
    medico: str
    nome: str
    cnpj: str
    especialidade: str
    perc: Decimal
    retem_iss: bool


@dataclass(frozen=True)
class Atendimento:
    numero: str
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


@dataclass(frozen=True)
class ItemLote:
    lote: str
    atendimento: str
    guia: str
    procedimento: str
    vl_tabela: Decimal
    vl_desconto: Decimal
    vl_copart: Decimal
    vl_faturado: Decimal
    vl_glosa: Decimal
    motivo_glosa: str


@dataclass(frozen=True)
class Lote:
    lote: str
    convenio: str
    competencia: str
    data_envio: date
    itens: tuple[ItemLote, ...]

    @property
    def qtd_guias(self) -> int:
        return len(self.itens)

    def total(self, campo: str) -> Decimal:
        return sum((getattr(i, campo) for i in self.itens), Decimal("0"))


@dataclass(frozen=True)
class ItemRepasse:
    competencia: str
    medico: str
    atendimento: str
    procedimento: str
    base: Decimal
    perc: Decimal
    valor: Decimal


@dataclass(frozen=True)
class TituloPagar:
    prefixo: str
    numero: str
    fornecedor: str
    emissao: date
    vencimento: date
    vl_bruto: Decimal
    irrf: Decimal
    pis: Decimal
    cofins: Decimal
    csll: Decimal
    iss: Decimal
    vl_liquido: Decimal


@dataclass(frozen=True)
class TituloReceber:
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
    atendimento: str
    motivo: str
