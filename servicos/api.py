"""Endpoint REST do ponto de entrada ZAGEFIN."""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from servicos.dados import ARQUIVO_FERIADOS, ARQUIVOS_BASE, DIR_DADOS, carregar_base, carregar_feriados
from servicos.modelos import BaseProtheus
from servicos.zagefin import gerar_titulos_receber

VARIAVEL_CHAVE_API = "ZAGEFIN_API_KEY"
VARIAVEL_FERIADOS = "ZAGEFIN_FERIADOS"

T = TypeVar("T")

app = FastAPI(title="Rede Clínica Exemplo - serviços migrados do Protheus")
cabecalho_chave_api = APIKeyHeader(name="X-API-Key", auto_error=False)


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


class CacheArquivos(Generic[T]):
    """Recarrega quando algum arquivo de origem muda (mtime/tamanho)."""

    def __init__(self, arquivos: Callable[[], Sequence[Path]], carregar: Callable[[], T]) -> None:
        self._arquivos = arquivos
        self._carregar = carregar
        self._lock = Lock()
        self._assinatura: tuple[tuple[str, int, int], ...] | None = None
        self._valor: T | None = None

    def _assinar(self) -> tuple[tuple[str, int, int], ...]:
        estados = ((caminho, caminho.stat()) for caminho in self._arquivos())
        return tuple((str(caminho), estado.st_mtime_ns, estado.st_size) for caminho, estado in estados)

    def obter(self) -> T:
        with self._lock:
            assinatura = self._assinar()
            if self._valor is None or assinatura != self._assinatura:
                self._valor = self._carregar()
                self._assinatura = assinatura
            return self._valor


def _arquivo_feriados() -> Path:
    return Path(os.environ.get(VARIAVEL_FERIADOS, ARQUIVO_FERIADOS))


cache_base: CacheArquivos[BaseProtheus] = CacheArquivos(
    lambda: [DIR_DADOS / nome for nome in ARQUIVOS_BASE], carregar_base
)
cache_feriados: CacheArquivos[tuple[date, ...]] = CacheArquivos(
    lambda: [_arquivo_feriados()], lambda: carregar_feriados(_arquivo_feriados())
)


def obter_base() -> BaseProtheus:
    return cache_base.obter()


def obter_feriados() -> tuple[date, ...]:
    return cache_feriados.obter()


def autenticar(chave: Annotated[str | None, Security(cabecalho_chave_api)]) -> None:
    esperada = os.environ.get(VARIAVEL_CHAVE_API)
    if not esperada:
        raise HTTPException(status_code=503, detail="Autenticação da API não configurada.")
    if chave is None or not secrets.compare_digest(chave.encode(), esperada.encode()):
        raise HTTPException(status_code=401, detail="Chave de API inválida.", headers={"WWW-Authenticate": "API-Key"})


@app.post(
    "/atendimentos/{numate}/titulos-receber",
    response_model=TitulosReceberResposta,
    dependencies=[Depends(autenticar)],
)
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
