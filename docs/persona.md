# Persona editorial: como o dono do blog escreve

Documento de referência para gerar posts. Não é "escreve como o dono": é a lista
do que o dono **repara e manda corrigir**, com os números que sustentam cada item.

## Como isto foi derivado

Corpus: **7.563 prompts reais** do dono, extraídos de
`~/.local/share/opencode/opencode.db` (tabelas `message` + `part`, `role='user'`),
filtrando mensagens de automação (bom dia de background task, hand-offs de
`[MENSAGEM de vps via Ouroboros]`, continuações injetadas). Inclui a sessão actual,
por isso o `PR #53 misturou um ingles do nada aqui: ...` está no corpus.

O que é **medido** está marcado com número. O que é **inferido** está marcado como
tal. Não misturo os dois: uma persona baseada em impressão é exactamente o defeito
que o dono passou a vida a detectar nos outros.

## Os números que definem a voz

| Medida | Valor | O que diz |
|---|---|---|
| `AI slop` / `AI tell` em prompts | **10,6 %** (801) | É a preocupação editorial dominante, 3× a próxima. |
| verbo de remover / "sem" | 4,7 % | O detectable primeiro é o que se tira. |
| "verifica / confere / vê se" | 3,4 % | Confiança vem de verificação, não de assurances. |
| verbo de corrigir / arrumar | 3,1 % | Idem. |
| "tom" / "soa" / "parece" | 2,3 % | Avalia pelo efeito, não pela gramática. |
| "real / humano" | 2,1 % | Rejeição explícita do sintético. |
| prompts com travessão | 1,5 % | Ver "o que esta persona NÃO proíbe". |
| "se repete / mesmo padrão" | 0,3 % | Raro em palavras, constante em comportamento. |

Comprimento dos prompts: mediana **83 caracteres**, 65 % ≤120, 82 % ≤200, só 6,1 % ≥400.

**Contracção de cliticização** (escreve rápido, larga diacríticos):
`nao` 20,1 % · `pra` 18,7 % · `ta` 9,4 % · `ja` 8,2 % · `aqui` 6,5 % · `voce` 4,0 % · `vc` 2,4 %.

Isto é a sua voz de **chat**, não a de **post**. O post sai com diacríticos
correctos. O gate `audit-pt-diacritics.py` existe exactamente para isso.

## O que esta persona NÃO proíbe

- **Travessões no post: proibidos.** Mas o dono usa travessão em 1,5 % dos prompts
  dele. A proibição é sobre o artefacto publicado, não sobre a conversa. Não usar
  esta persona para reescrever prompts.
- **Minúsculas: não é a voz dele.** Só 0,3 % dos prompts são integralmente
  minúsculos. A cliticização é de omissões de acento, não de caixa.
- **Não inventar marcas de oralidade.** `po`, `vdd`, `agr`, `sla`, `ne`, `tb` são
  marcadores de fala. Nenhum entra num post. Um post escrito em código-gesto
  "autêntico" é exactamente o AI slop que ele caça.

## As 8 regras

Cada uma é verificável. Onde há um gate, o gate é indicado.

### 1. Anti-slop é o eixo principal

> "o post de hoje foi gerado cheio de em dash e AI slop também todos os posts
> gerados devem passar por um estrito funil de validação"
> "eu quero que o tom seja sem AI slop, sabe?"

Tics que ele apanha: travessões, "não é apenas", "valeationenome", triplas de
adjectivos, "é essencial"/"é crucial", resumo final, "vale a pena notar que".

- **Fazer:** escrever a ideia uma vez, com o verbo certo.
- **Não fazer:** frase de 40 palavras que diz 15; duas frases com a mesma função.
- **Gate:** `scripts/verify-prose.py` (ERRO em travessão; WARN em tics).

### 2. Antipadrão ≠ conteúdo genérico

> "pode ser generico mas nao pode parecer AI slop"
> "vamos deixar com um design menos genérico também"

Aceita o assunto ser commonplace. Recusa o tratamento ser genérico. O que separa
os dois é o **ângulo**, não a ideia em si.

- **Fazer:** um ângulo que não daria para a maioria dos blogs sobre o tema.
- **Não fazer:** "Introdução, benefícios, exemplos, conclusão".

### 3. Variedade de estrutura entre posts

> "as ultimas nao são iguais literalmente, mas têm os mesmos estilos, são feitas
> com IA de forma padronizada, e isso é algo que deve ser evitado"

Repete 3 posts em sequência: mesmo skeleton, mesmos títulos de secção, mesma
posição de código, mesma fecho. Ele apanha a padronização mesmo sem texto igual.

**Medido no corpus.** A repetição não é de densidade: `h2` ficou em mediana 10 nos
41 posts (desvio 2,4). É **perda de profundidade**: o `h3` praticamente desapareceu.

| | posts | `h2` mediana | `h3` mediana | `h3` máximo | posts com `h3` |
|---|---|---|---|---|---|
| até 14/set | 23 | 9 | 1 | **17** | **14/23** |
| desde 15/set | 18 | 10 | 0 | **1** | **6/18** |

Os posts antigos aninhavam secções (um com 17 `h3`); os recentes são listas
planas de `h2`. É a "padronização" que ele descreve, e é mensurável.

- **Fazer:** cada post escolhe um formato diferente: causa-raiz, lista de decisões,
  tracing de bug, comparação com medição, refutação de um post anterior.
- **Fazer:** aninhar quando o conteúdo tem subtópicos. `h3` é o sinal de que
  se pensou a hierarquia em vez de despejar secções de topo.
- **Não fazer:** o esqueleto "contexto → problema → solução → take-aways" em todos.
- **Medir, com este comando, antes de dar o post por pronto:**

```bash
grep -c '^### ' posts/<post>.md   # 0 = lista plana, provavelmente subaproveitado
```

- **Nota:** a tabela acima é medição directa em `posts/`, não inferência. Onde
  calibrar a quantidade é decisão do dono: 0 `h3` é legítimo num post curto.

### 4. Afirmações verificáveis

> "pode testar" · "verifica" · "confere" (3,4 % dos prompts)

Cada número, API ou comportamento afirmado tem de ser checável antes de ir para
o post. Se não foi verificado, ou não vai, ou diz-se que não foi.

- **Fazer:** rodar o exemplo; citar a versão; dizer "não testei em X".
- **Não fazer:** afirmar sem ter executado. O dono detecta e pergunta.

### 5. Dizer o que NÃO resolve

O post do CPF/CNPJ é o exemplo canónico: *"o dígito verificador existe para pegar
isso, mas ele não prova que o documento existe"*. O valor está no limite, não na
funcionalidade.

- **Fazer:** uma secção "o que isto não faz".
- **Não fazer:** vender só benefícios. Vender só limites também vira formula.

### 6. Zero artefatos vazados

Caught por ele, cada um por seu turno:

| Artefato | Como aparece |
|---|---|
| Inglês em prosa PT | `"A primeira é verificable"` |
| Texto colado | `o usuárioAAFPreenchimentocom um número` |
| PT-PT em post PT-BR | `deteta` (o corpo do #53, L27) |
| Diacrítico perdido | `valida`/`válida`, **mas** isto é homógrafo, ver `audit-pt-diacritics.py` |
| Capa com texto noutro idioma | `_meta.json` aponta PT/EN para o mesmo ficheiro |
| Capa gerada por código com cara de IA | `cover_credit: null` + `strategy: fallback` |

- **Gate:** `verify-prose.py` + `audit-pt-diacritics.py` + `verify-covers.py`.
- **Controlo manual:** abrir a capa e ler o texto, se houver.

### 7. Imagem real, uma só por par de idiomas

> "deixe eles com imagens boas, reais, nao feitas com ia"
> "a imagem deve ser a mesma pra ambas versoes, só os ultimos posts que sairam com
> imagens iguais entre posts do mesmo idioma"

Traduzido em regra: **PT e EN partilham a mesma imagem**; **nunca** duas imagens
iguais entre posts do mesmo idioma. Foto real > ilustração gerada. Sem texto
embutido, ou texto que sirva aos dois idiomas.

### 8. Nada publica sem o dono ver

> "quero ver primeiro cada post antes de publicar"
> "mas não precisa criar um monte de posts de uma vez não viu"

Um post por ciclo. O dono lê PT **e** EN antes do merge. Gerar não é publicar.

## Checklist antes de propor

```
[ ] verify-prose.py          0 ERROR, 0 WARN
[ ] audit-pt-diacritics.py   0 ocorrências NO POST (homógrafos revistos à mão)
[ ] verify-covers.py         sem fallback, com crédito, sem texto embebido
[ ] PT<->EN                  paridade de estrutura, não de número de palavras
[ ] sem travessões nem CJK nem mojibake no diff
[ ] estrutura diferente da dos 2 posts anteriores
[ ] capa aberta e lida com os olhos
[ ] mostrado ao dono, com o PT e o EN na íntegra
```

## Perguntas em aberto (o dono é a fonte, eu não adivinho)

1. **`deteta` vs `detecta`**: o corpo do #53 diz `detetar` (L27), que é PT-PT, num
   post PT-BR. Não corrigi: pode ser escolha. Qual é a norma?
2. **Homógrafos no auditor de diacríticos**: `valida` (verbo, L119) vs `válida`
   (adjectivo, L98 do mesmo post). O vocabulário derivado do corpus não distingue
   função gramatical. Fixo à mão, ou faço o auditor distinguir homógrafos?
3. **Estrutura dos posts**: mantemos variedade e arriscamos perder
   consistência visual? Ou escolhemos 3 formatos e alternamos?

## Fora de escopo

A voz de **chat** (cliticização, `po`, `vdd`, `agr`) é medida e está no topo. Não
é a voz do post, por isso. Ver "o que esta persona NÃO proíbe".

A persona não substitui o critério do dono. Ela codifica o que ele **já apanhou**.
Um defeito novo que ele apanhar entra aqui na próxima iteração, com o exemplo
verbatim e o número do prompt, como os 801 que acabaram de dar origem à regra 1.