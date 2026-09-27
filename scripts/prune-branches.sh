#!/usr/bin/env bash
#
# Apaga as branches obsoletas do blog-content.
#
# Este script NAO decide nada. Ele consome o veredito do audit-branches.py e
# apaga exatamente o que a auditoria classificou como seguro.
#
# POR QUE A LOGICA FICOU NUM SO LUGAR
# A v1 deste script tinha a propria verificacao, e ela estava errada tres
# vezes -- o resultado esperado quando a mesma regra e implementada em dois
# lugares:
#   1. `git branch -r` imprime com espaco a esquerda, o strip de "origin/" nao
#      casava, e o MAIN entrou na lista de apagamento;
#   2. os comandos git davam "Not a valid object name", o loop de verificacao
#      nao rodou, e o script reportou "41 seguras, 0 mergeadas" tendo
#      verificado NADA;
#   3. testava a BRANCH inteira em vez do POST que ela nomeia. Como cada branch
#      e um snapshot do diretorio posts/ inteiro, isso errava a escala e
#      preservava 25 das 41 branches sem necessidade -- e, pior, reportava o
#      titulo do post errado ("CSS Grid vs Flexbox" numa branch de devtools).
# Agora a regra mora no audit-branches.py, testada contra o corpus real.
#
#   bash scripts/prune-branches.sh --dry-run    # so o relatorio, nada apaga
#   bash scripts/prune-branches.sh             # apaga
#
# REGRA: FALHA FECHADA. Se a auditoria nao rodar, nao produzir lista, ou a
# lista vier com main/HEAD dentro, o script ABORTA sem apagar nada. Um script
# que destroi nao pode ter valor padrao em caso de duvida.
set -euo pipefail

OWNER="ismaeldouglasdev"
REPO="blog-content"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

cd "$(dirname "$0")/.."

command -v curl >/dev/null || { echo "precisa de curl" >&2; exit 1; }
command -v python3 >/dev/null || { echo "precisa de python3" >&2; exit 1; }

TOKEN=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  TOKEN="$GITHUB_TOKEN"
elif [[ -f "$HOME/.git-credentials" ]]; then
  TOKEN=$(python3 - <<'PY'
import io, re
t = io.open('/home/ubuntu/.git-credentials', encoding='utf-8', errors='replace').read()
for l in t.splitlines():
    m = re.match(r'https?://[^:]+:([^@]+)@github\.com', l.strip())
    if m and m.group(1).startswith(('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_')):
        print(m.group(1)); break
PY
)
fi
[[ -n "$TOKEN" ]] || { echo "sem token: rode 'gh auth login' ou exporte GITHUB_TOKEN" >&2; exit 1; }

echo "repositorio: $OWNER/$REPO"
if [[ $DRY -eq 1 ]]; then echo "MODO DRY-RUN: nada sera apagado"; else echo "MODO REAL: branches serao apagadas"; fi
echo

git rev-parse --verify origin/main >/dev/null 2>&1 || { echo "nao consegui ler origin/main" >&2; exit 1; }

# ---- o veredito vem de fora, e falhar aqui e abortar
if ! LISTA=$(python3 scripts/audit-branches.py --emit-safe 2>/tmp/prune-audit.err); then
  echo "ABORTANDO: a auditoria falhou, entao nada e seguro." >&2
  sed 's/^/  /' /tmp/prune-audit.err >&2
  exit 1
fi
rm -f /tmp/prune-audit.err

mapfile -t SEGURAS < <(printf '%s\n' "$LISTA" | grep -v '^[[:space:]]*$' || true)

if [[ ${#SEGURAS[@]} -eq 0 ]]; then
  echo "a auditoria nao encontrou nada seguro. Nada sera apagado."
  exit 0
fi

# ---- trava final: main e symref nunca podem estar na lista
for nome in "${SEGURAS[@]}"; do
  if [[ "$nome" == "main" || "$nome" == "HEAD" || "$nome" == *HEAD* ]]; then
    echo "ABORTANDO: '$nome' na lista de apagamento. Nada foi apagado." >&2
    exit 1
  fi
  if [[ "$nome" == origin/* || "$nome" == *'=>'* ]]; then
    echo "ABORTANDO: nome de branch inesperado '$nome'. Nada foi apagado." >&2
    exit 1
  fi
done

TOTAL=${#SEGURAS[@]}
echo "auditoria: $TOTAL branch(es) sem conteudo unico"
echo "  (o que a auditoria PRESERVOU fica de fora, por construcao)"
echo

if [[ $DRY -eq 1 ]]; then
  echo "--- seriam apagadas ---"
  printf '  %s\n' "${SEGURAS[@]}"
  echo
  echo "rode sem --dry-run para apagar de verdade"
  exit 0
fi

echo "apagando $TOTAL branches..."
falhas=0
for nome in "${SEGURAS[@]}"; do
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$OWNER/$REPO/git/refs/heads/$(printf '%s' "$nome" | sed 's|/|%2F|g')")
  if [[ "$codigo" == "204" ]]; then
    printf '  apagada  %s\n' "$nome"
  else
    printf '  FALHOU (%s) %s\n' "$codigo" "$nome" >&2
    falhas=$((falhas+1))
  fi
done

echo
echo "apagadas: $((TOTAL - falhas)) | falhas: $falhas"
git fetch -q --prune origin '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null || true
restantes=$(git branch -r | grep -v ' -> ' | grep -v HEAD | sed 's/^ *//' | grep -c . || true)
echo "branches remotas restantes: $restantes"
if git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
  echo "main intacto: SIM"
else
  echo "main intacto: NAO  <-- INVESTIGUE"
fi
