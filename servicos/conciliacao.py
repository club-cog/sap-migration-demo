"""Conciliação campo a campo entre as saídas geradas e as saídas de referência do Protheus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

from servicos.dados import DIR_REFERENCIA, Linha, ler_csv


@dataclass(frozen=True)
class Divergencia:
    chave: tuple[str, ...]
    campo: str
    gerado: str | None
    referencia: str | None


@dataclass(frozen=True)
class Conciliacao:
    tabela: str
    colunas_iguais: bool
    linhas_referencia: int
    linhas_geradas: int
    campos_comparados: int
    divergencias: list[Divergencia]

    @property
    def paridade(self) -> bool:
        return self.colunas_iguais and self.linhas_referencia == self.linhas_geradas and not self.divergencias


def conciliar(
    tabela: str,
    colunas: Sequence[str],
    chave: Sequence[str],
    geradas: list[Linha],
    arquivo_referencia: str,
    diretorio: Path = DIR_REFERENCIA,
) -> Conciliacao:
    caminho = diretorio / arquivo_referencia
    referencia = ler_csv(caminho)
    with caminho.open(encoding="utf-8") as arquivo:
        cabecalho = arquivo.readline().strip().split(";")

    def indexar(linhas: list[Linha]) -> dict[tuple[str, ...], list[Linha]]:
        """Chave -> linhas na ordem do arquivo. Chaves repetidas são comparadas linha a linha."""
        indice: dict[tuple[str, ...], list[Linha]] = defaultdict(list)
        for linha in linhas:
            indice[tuple(linha[c] for c in chave)].append(linha)
        return indice

    por_chave_ref = indexar(referencia)
    por_chave_ger = indexar(geradas)
    divergencias: list[Divergencia] = []
    comparados = 0
    for k in sorted(por_chave_ref.keys() | por_chave_ger.keys()):
        for ref, ger in zip_longest(por_chave_ref.get(k, []), por_chave_ger.get(k, [])):
            for campo in cabecalho:
                comparados += 1
                valor_ref = ref.get(campo) if ref else None
                valor_ger = ger.get(campo) if ger else None
                if valor_ref != valor_ger:
                    divergencias.append(Divergencia(chave=k, campo=campo, gerado=valor_ger, referencia=valor_ref))
    return Conciliacao(
        tabela=tabela,
        colunas_iguais=list(colunas) == cabecalho,
        linhas_referencia=len(referencia),
        linhas_geradas=len(geradas),
        campos_comparados=comparados,
        divergencias=divergencias,
    )
