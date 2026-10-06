#!/usr/bin/env bash
# Compila e roda o CCBATCH com GnuCOBOL, simulando os DDs do JCL.
# Uso: legacy/rodar_batch.sh [diretorio_saida]   (padrao: legacy/saidas_referencia)
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")" && pwd)"
SAIDA="${1:-$RAIZ/saidas_referencia}"
BUILD="$(mktemp -d)"
mkdir -p "$SAIDA"
for p in CCJUROS CCTARIF; do
  cobc -x -I "$RAIZ/cobol/copybooks" -o "$BUILD/$p" "$RAIZ/cobol/$p.cbl"
done
export DD_CONTAS="$RAIZ/dados/CONTAS.DAT"
export DD_MOVTOS="$RAIZ/dados/MOVTOS.DAT"
export DD_ENCARGOS="$SAIDA/ENCARGOS.DAT" DD_REJJUROS="$SAIDA/REJJUROS.DAT"
export DD_TARIFAS="$SAIDA/TARIFAS.DAT"   DD_REJTARIF="$SAIDA/REJTARIF.DAT"
set +e
"$BUILD/CCJUROS"; RC=$?
set -e
echo "STEP010 CCJUROS RC=$RC"
if [ "$RC" -gt 4 ]; then exit "$RC"; fi
set +e
"$BUILD/CCTARIF"; RC=$?
set -e
echo "STEP020 CCTARIF RC=$RC"
rm -rf "$BUILD"
