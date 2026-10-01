"""Endpoint REST do ponto de entrada ZAGEFIN."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from servicos.dados import carregar_base
from servicos.modelos import BaseProtheus
from servicos.zagefin import gerar_titulos_receber

app = FastAPI(title="Rede Clínica Exemplo - serviços migrados do Protheus")


class TituloReceberSaida(BaseModel):
    prefixo: str
    numero: str
    parcela: str
    tipo: str
    cliente: str
    emissao: date
    vencimento: date
    valor: Decimal


class TitulosReceberResposta(BaseModel):
    numate: str
    titulos: list[TituloReceberSaida]


@lru_cache(maxsize=1)
def obter_base() -> BaseProtheus:
    return carregar_base()


def obter_feriados() -> tuple[date, ...]:
    return ()


@app.post("/atendimentos/{numate}/titulos-receber", response_model=TitulosReceberResposta)
def titulos_receber(
    numate: str,
    base: Annotated[BaseProtheus, Depends(obter_base)],
    feriados: Annotated[tuple[date, ...], Depends(obter_feriados)],
) -> TitulosReceberResposta:
    resultado = gerar_titulos_receber(base, numate, feriados)
    if resultado.rejeicao is not None:
        raise HTTPException(status_code=422, detail={"numate": numate, "motivo": resultado.rejeicao.motivo})
    if not resultado.gerou:
        raise HTTPException(
            status_code=404, detail={"numate": numate, "motivo": "ATENDIMENTO_PARTICULAR_NAO_ENCONTRADO"}
        )
    return TitulosReceberResposta(
        numate=numate,
        titulos=[
            TituloReceberSaida(
                prefixo=t.prefixo,
                numero=t.numero,
                parcela=t.parcela,
                tipo=t.tipo,
                cliente=t.cliente,
                emissao=t.emissao,
                vencimento=t.vencimento,
                valor=t.valor,
            )
            for t in resultado.titulos
        ],
    )
