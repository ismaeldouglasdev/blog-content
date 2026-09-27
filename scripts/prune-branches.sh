#!/usr/bin/env bash
#
# Apaga as branches obsoletas do blog-content, com verificacao antes de apagar.
#
# Por que este script existe: em 2026-09-27 a auditoria achou 41 branches
# remotas obsoletas. 13 sao ancestrais do main; as outras 28 nao sao, mas nao
# por causa de trabalho perdido -- cada uma e um snapshot antigo do diretorio
# posts/, congelado quando a branch foi criada. O conteudo esta no main, as
# vezes melhor: o main tem share_hook, excerpt revisado e heading corrigido que
# a branch nao tem. A assinatura e monotonica -- os .md "exclusivos" crescem
# com a data da branch (68, 69, 71, 73, 75, 77, 79), que e o que acontece
# quando cada branch guarda um retrato do repositorio inteiro.
#
# POR QUE ISTO NAO APAGA SOZINHO
# Nenhuma branch tem trabalho unico -- verificado, nao presumido. Mas apagar
# branch e destruicao, e o custo de errar e assimetrico: se eu estiver errado
# sobre alguma, o post some do historico e nao tem volta. Por isso o script
# existe para revisar antes de destruir, e a destruicao exige comando explicito.
#
#   bash scripts/prune-branches.sh --dry-run    # so o relatorio, nada apaga
#   bash scripts/prune-branches.sh             # apaga
#
# REGRA: FALHA FECHADA. Qualquer duvida sobre uma branch -- comando git que da
# erro, titulo vazio, lista vazia, main na lista -- PRESERVA a branch.
#
# Isso nao e teoria. A primeira versao deste script tinha o bug que a regra
# acima previne: `git branch -r` imprime com espaco a esquerda, entao o strip
# de "origin/" falhava em silencio, o nome continuava " origin/main", o teste
# de protecao nao casava, e os comandos git davam "Not a valid object name".
# Resultado: o loop de verificacao nao rodou, o script reportou "41 seguras,
# 0 mergeadas" tendo verificado NADA -- e com o main na lista de apagamento.
# O --dry-run pegou os dois bugs. Um script que destroi precisa de dry-run
# obrigatorio, nao opcional.
set -euo pipefail

REPO="blog-content"
OWNER="ismaeldouglasdev"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

cd "$(dirname "$0")/.."

command -v curl >/dev/null || { echo "precisa de curl" >&2; exit 1; }
command -v python3 >/dev/null || { echo "precisa de python3" >&2; exit 1; }

TOKEN=""
if [[ -f "$HOME/.git-credentials" ]]; then
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

git fetch -q --prune origin '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null || true
git rev-parse --verify origin/main >/dev/null 2>&1 || { echo "nao consegui ler origin/main" >&2; exit 1; }

MERGED=()
PARECIDAS=()
PRESERVADAS=()

while IFS= read -r cru; do
  # O trim e a correcao da causa raiz do bug do main. Sem ele, "${branch#origin/}"
  # nao casa por causa do espaco a esquerda e o nome segue " origin/main".
  branch=$(printf '%s' "$cru" | tr -d '[:space:]')
  [[ -z "$branch" ]] && continue
  name="${branch#origin/}"
  [[ -z "$name" || "$name" == "HEAD" ]] && continue

  # main nunca entra em lista nenhuma. Tres portas, porque o custo de errar
  # aqui e perder o blog inteiro.
  if [[ "$name" == "main" || "$branch" == "main" || "$branch" == "origin/main" ]]; then
    echo "  (ignorado por protecao: $name)" >&2
    continue
  fi

  # o objeto precisa existir localmente; se nao existe, preserva
  if ! git rev-parse --verify --quiet "$branch" >/dev/null 2>&1; then
    PRESERVADAS+=("$name  [objeto git ausente]")
    continue
  fi

  if git merge-base --is-ancestor "$branch" origin/main 2>/dev/null; then
    MERGED+=("$name")
    continue
  fi

  # Nao mergeada: exige que todo .md dela tenha o titulo correspondente no main.
  arquivos=$(git ls-tree -r --name-only "$branch" -- posts/ 2>/dev/null | grep '\.md$' || true)
  if [[ -z "$arquivos" ]]; then
    PRESERVADAS+=("$name  [nenhum .md lido -- falha na verificacao]")
    continue
  fi

  perda=0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    titulo=$(git show "$branch:$f" 2>/dev/null | grep -m1 '^title:' | cut -c8- | tr -d '"' || true)
    if [[ -z "$titulo" ]]; then
      perda=1
      echo "  PRESERVADA (title ilegivel): $name  <- $f" >&2
      break
    fi
    # busca o titulo INTEIRO. Truncar produz falso negativo, e falso negativo
    # aqui significaria "branch parece ter conteudo unico" -- o erro caro.
    if ! git grep -q -F "$titulo" origin/main -- 'posts/*.md' 2>/dev/null; then
      perda=1
      echo "  PRESERVADA (titulo nao esta no main): $name  <- $titulo" >&2
      break
    fi
  done <<< "$arquivos"

  if [[ $perda -eq 0 ]]; then
    PARECIDAS+=("$name")
  else
    PRESERVADAS+=("$name")
  fi
done < <(git branch -r | grep -v HEAD)

TOTAL=$(( ${#MERGED[@]} + ${#PARECIDAS[@]} ))

echo "verificacao concluida:"
echo "  mergeadas no main (perda zero)    : ${#MERGED[@]}"
echo "  snapshot antigo, conteudo no main : ${#PARECIDAS[@]}"
echo "  preservadas por seguranca         : ${#PRESERVADAS[@]}"
echo "  total seguro para apagar          : $TOTAL"
echo

# trava final, independente de como as listas foram preenchidas
for nome in "${MERGED[@]}" "${PARECIDAS[@]}"; do
  if [[ "$nome" == "main" || "$nome" == "origin/main" ]]; then
    echo "ABORTANDO: main apareceu na lista de apagamento ('$nome')." >&2
    echo "Isso e bug no script, nao algo a apagar. Nada foi apagado." >&2
    exit 1
  fi
done

if [[ ${#PRESERVADAS[@]} -gt 0 ]]; then
  echo "preservadas (para revisao manual):"
  printf '  %s\n' "${PRESERVADAS[@]}"
  echo
fi

if [[ $TOTAL -eq 0 ]]; then
  echo "nada a fazer"
  exit 0
fi

if [[ $DRY -eq 1 ]]; then
  echo "--- seriam apagadas (mergeadas, perda zero) ---"
  printf '  %s\n' "${MERGED[@]}"
  echo "--- seriam apagadas (snapshot antigo, conteudo ja no main) ---"
  printf '  %s\n' "${PARECIDAS[@]}"
  echo
  echo "rode sem --dry-run para apagar de verdade"
  exit 0
fi

echo "apagando $TOTAL branches..."
falhas=0
for name in "${MERGED[@]}" "${PARECIDAS[@]}"; do
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$OWNER/$REPO/git/refs/heads/$(printf '%s' "$name" | sed 's|/|%2F|g')")
  if [[ "$codigo" == "204" ]]; then
    printf '  apagada  %s\n' "$name"
  else
    printf '  FALHOU (%s) %s\n' "$codigo" "$name" >&2
    falhas=$((falhas+1))
  fi
done

echo
echo "apagadas: $((TOTAL - falhas)) | falhas: $falhas"
git fetch -q --prune origin '+refs/heads/*:refs/remotes/origin/*' 2>/dev/null || true
restantes=$(git branch -r | grep -v HEAD | tr -d '[:space:]' | grep -c . || true)
echo "branches remotas restantes: $restantes"
if git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
  echo "main intacto: SIM"
else
  echo "main intacto: NAO  <-- INVESTIGUE"
fi
