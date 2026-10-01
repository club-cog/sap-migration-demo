"""Processamento da competência na ordem do legado: FATCONV (todos os convênios) -> REPMED -> ZAGEFIN.

Uso: python -m servicos.competencia 202608 20260905 [diretorio_saida]
     [--dados DIR] [--historico DIR] [--feriados ARQUIVO]

A saída inclui o SZ1 com Z1_FATURA preenchido. Para reprocessar, use esse SZ1 em `--dados` e a saída
anterior em `--historico` (SZ5/SZ6 já gravados), como no banco do Protheus.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from servicos.conciliacao import Conciliacao, conciliar
from servicos.dados import (
    ARQUIVO_FERIADOS,
    DIR_DADOS,
    LAYOUT_SE1,
    LAYOUT_SE2,
    LAYOUT_SZ1,
    LAYOUT_SZ5,
    LAYOUT_SZ6,
    LAYOUT_SZ7,
    LAYOUT_SZ8,
    Linha,
    carregar_base,
    carregar_feriados,
    carregar_historico_lotes,
    gravar_csv,
)
from servicos.fatconv import NenhumAtendimentoAFaturar, faturar_convenio
from servicos.modelos import (
    BaseProtheus,
    ItemLote,
    ItemRepasse,
    LoteFaturamento,
    Rejeicao,
    TituloPagar,
    TituloReceber,
)
from servicos.protheus import dtos, stod
from servicos.repmed import calcular_repasse
from servicos.zagefin import TIPO_PARTICULAR, gerar_titulos_receber

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SaidasCompetencia:
    lotes: list[LoteFaturamento]
    itens_lote: list[ItemLote]
    itens_repasse: list[ItemRepasse]
    titulos_pagar: list[TituloPagar]
    titulos_receber: list[TituloReceber]
    rejeicoes: list[Rejeicao]
    faturados: dict[str, str]

    def tabelas(self) -> dict[str, tuple[tuple[str, ...], tuple[str, ...], str, list[Linha]]]:
        """Tabela -> (colunas, chave, arquivo, linhas no layout do Protheus)."""
        pares = (
            (LAYOUT_SZ5, self.lotes),
            (LAYOUT_SZ6, self.itens_lote),
            (LAYOUT_SZ7, self.itens_repasse),
            (LAYOUT_SZ8, self.rejeicoes),
            (LAYOUT_SE1, self.titulos_receber),
            (LAYOUT_SE2, self.titulos_pagar),
        )
        return {
            layout.tabela: (layout.colunas, layout.chave, layout.arquivo, layout.linhas(registros))  # type: ignore[arg-type]
            for layout, registros in pares
        }


def proximo_lote(lotes_anteriores: Iterable[LoteFaturamento]) -> int:
    """Sequência do `GetSXENum("SZ5", "Z5_LOTE")`: continua a partir do maior lote já gravado."""
    return max((int(lote.lote) for lote in lotes_anteriores), default=0) + 1


def marcar_faturados(base: BaseProtheus, faturados: dict[str, str]) -> BaseProtheus:
    """Aplica o `SZ1->Z1_FATURA := cLote` do FATCONV, devolvendo a base atualizada."""
    atendimentos = tuple(
        replace(a, fatura=faturados[a.numate]) if a.numate in faturados else a for a in base.atendimentos
    )
    return replace(base, atendimentos=atendimentos)


def processar_competencia(
    base: BaseProtheus,
    competencia: str,
    data_envio: date,
    feriados: Iterable[date] = (),
    lotes_anteriores: Sequence[LoteFaturamento] = (),
    itens_lote_anteriores: Sequence[ItemLote] = (),
) -> SaidasCompetencia:
    """`lotes_anteriores`/`itens_lote_anteriores` são o SZ5/SZ6 já gravado antes desta execução."""
    feriados = tuple(feriados)
    lotes: list[LoteFaturamento] = []
    itens_lote: list[ItemLote] = []
    faturados: dict[str, str] = {}
    sequencial = proximo_lote(lotes_anteriores)
    for convenio in sorted(base.convenios):
        try:
            resultado = faturar_convenio(base, convenio, competencia, data_envio, f"{sequencial:06d}")
        except NenhumAtendimentoAFaturar:
            continue
        sequencial += 1
        lotes.append(resultado.lote)
        itens_lote.extend(resultado.itens)
        faturados.update(resultado.faturados)

    # O REPMED lê todo o SZ6 gravado (índice Z6_NUMATE + ordem de gravação), não só o desta execução.
    repasse = calcular_repasse(base, competencia, [*itens_lote_anteriores, *itens_lote], feriados)

    titulos_receber: list[TituloReceber] = []
    rejeicoes: list[Rejeicao] = []
    particulares = sorted(
        (a for a in base.atendimentos if a.tipo == TIPO_PARTICULAR and dtos(a.data)[:6] == competencia),
        key=lambda a: a.numate,
    )
    for atendimento in particulares:
        resultado_fin = gerar_titulos_receber(base, atendimento.numate, feriados)
        titulos_receber.extend(resultado_fin.titulos)
        if resultado_fin.rejeicao is not None:
            rejeicoes.append(resultado_fin.rejeicao)

    return SaidasCompetencia(
        lotes=lotes,
        itens_lote=itens_lote,
        itens_repasse=repasse.itens,
        titulos_pagar=repasse.titulos,
        titulos_receber=titulos_receber,
        rejeicoes=rejeicoes,
        faturados=faturados,
    )


def conciliar_saidas(saidas: SaidasCompetencia) -> list[Conciliacao]:
    return [
        conciliar(tabela, colunas, chave, linhas, arquivo)
        for tabela, (colunas, chave, arquivo, linhas) in saidas.tabelas().items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("competencia", help="AAAAMM")
    parser.add_argument("data_envio", help="AAAAMMDD (MV_PAR03 do FATCONV)")
    parser.add_argument("saida", nargs="?", default="saidas", type=Path)
    parser.add_argument("--dados", default=DIR_DADOS, type=Path, help="diretório com SZ1..SZ4")
    parser.add_argument("--historico", type=Path, help="diretório com SZ5/SZ6 de execuções anteriores")
    parser.add_argument("--feriados", default=ARQUIVO_FERIADOS, type=Path, help="CSV de feriados (SX5/63)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    base = carregar_base(args.dados)
    lotes_anteriores, itens_anteriores = carregar_historico_lotes(args.historico) if args.historico else ([], [])
    saidas = processar_competencia(
        base,
        args.competencia,
        stod(args.data_envio),
        carregar_feriados(args.feriados),
        lotes_anteriores,
        itens_anteriores,
    )
    for colunas, _, arquivo, linhas in saidas.tabelas().values():
        gravar_csv(args.saida / arquivo, colunas, linhas)
    atualizada = marcar_faturados(base, saidas.faturados)
    gravar_csv(args.saida / LAYOUT_SZ1.arquivo, LAYOUT_SZ1.colunas, LAYOUT_SZ1.linhas(atualizada.atendimentos))

    print("| Tabela | Linhas (ref/gerado) | Campos comparados | Divergências | Paridade |")
    print("|---|---|---|---|---|")
    for c in conciliar_saidas(saidas):
        paridade = "100%" if c.paridade else "FALHOU"
        print(
            f"| {c.tabela} | {c.linhas_referencia}/{c.linhas_geradas} | {c.campos_comparados} "
            f"| {len(c.divergencias)} | {paridade} |"
        )


if __name__ == "__main__":
    main()
