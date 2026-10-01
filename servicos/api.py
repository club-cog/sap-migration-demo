"""API REST que substitui as rotinas FATCONV, REPMED e ZAGEFIN."""

from datetime import date

from fastapi import FastAPI, HTTPException

from servicos import faturamento_convenio, repasse_medico, titulos_particular
from servicos.repositorio import BaseLegado

app = FastAPI(title="Financeiro Clínico - serviços migrados do Protheus")
base = BaseLegado.carregar()


@app.post("/faturamento/{competencia}/lotes")
def gerar_lotes(competencia: str, data_envio: date) -> list[dict]:
    lotes = faturamento_convenio.gerar_lotes_competencia(base, competencia, data_envio)
    return [
        {
            "lote": lt.lote,
            "convenio": lt.convenio,
            "qtd_guias": lt.qtd_guias,
            "vl_faturado": str(lt.total("vl_faturado")),
            "vl_glosa": str(lt.total("vl_glosa")),
            "itens": [i.__dict__ for i in lt.itens],
        }
        for lt in lotes
    ]


@app.post("/repasse/{competencia}")
def gerar_repasse(competencia: str, data_envio: date) -> list[dict]:
    lotes = faturamento_convenio.gerar_lotes_competencia(base, competencia, data_envio)
    itens = repasse_medico.calcular_itens(base, competencia, lotes)
    return [t.__dict__ for t in repasse_medico.gerar_titulos(base, competencia, itens)]


@app.post("/atendimentos/{numero}/titulos")
def gerar_titulos_particular(numero: str) -> list[dict]:
    atendimento = next((a for a in base.atendimentos if a.numero == numero), None)
    if atendimento is None:
        raise HTTPException(status_code=404, detail="Atendimento não encontrado")
    resultado = titulos_particular.gerar_titulos(base, atendimento)
    if resultado is None:
        raise HTTPException(status_code=422, detail="Atendimento não é particular")
    if isinstance(resultado, titulos_particular.Rejeicao):
        raise HTTPException(status_code=422, detail=resultado.motivo)
    return [t.__dict__ for t in resultado]
