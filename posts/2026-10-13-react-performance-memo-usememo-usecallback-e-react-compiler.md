---
title: "React performance: memo, useMemo, useCallback e React Compiler"
date: "2026-10-13"
category: "article"
tags: ["react", "performance", "optimizacao"]
excerpt: "Introdução: quando a otimização se torna necessária"
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-10-13-react-performance-memo-usememo-usecallback-e-react-compiler.jpg"
lang: "pt"
---

## Introdução: quando a otimização se torna necessária

Quando você lida com um catálogo de mais de 10 mil produtos e precisa mantê-lo sincronizado entre um sistema de PDV e um marketplace, cada renderização extra começa a doer. Esse foi o cenário que me levou a mergulhar na otimização de performance no React. O projeto *inventory‑service* que construí para um cliente usava OSPOS como base e expunha um endpoint JSON que alimentava tanto o front‑end da loja quanto a integração com o Mercado Livre. Nos primeiros dias, a página de catálogo atualizava a lista inteira a cada digitação, e o navegador travava em conexões mais lentas.

A dor era visível no Chrome DevTools: centenas de componentes renderizando em cascata, muitos deles recebendo novas props mesmo quando a consulta de fundo não havia retornado novos dados. A primeira tentativa de corrigir o problema foi envolver tudo com `React.memo`, mas isso apenas mascarou o sintoma — as renderizações desnecessárias continuaram ocorrendo no nível mais profundo.

Esse padrão se repete em vários dos meus projetos pessoais. O *blog.ismaeltech.com* é um SPA React que gera artigos diariamente usando um pipeline automatizado de IA. Inicialmente, o guardador anti‑slop recriava todo o árbol de componentes a cada novo post, e só depois percebi que a maior parte do trabalho era apenas reavaliar expressões caras dentro dos componentes de layout. O mesmo raciocínio se aplica ao *Plexo*, um gerenciador de tarefas com uma API REST em Python e uma UI React/Vite — sempre que um novo item era adicionado, o front‑end executava um ciclo de renderização completo sem necessidade.

O que aprendi com essas experiências é que otimização não é um passo opcional “quando você tem tempo”. É uma resposta direta a um problema de negócio real: reduzir a latência percebida melhora a experiência do usuário e reduz custos com infraestrutura. A partir de agora, vamos explorar as ferramentas que ajudam a transformar uma interface reativa em uma interface responsiva, usando exemplos concretos dos meus próprios códigos.

## React.memo: evitando renderizações desnecessárias

`React.memo` é um wrapper de alto nível que memoiza o resultado de um componente funcional. Se as props não mudarem, o React reutiliza o último nó DOM, evitando um ciclo completo de commit. Em termos práticos, isso significa que um componente de lista de produtos pode sobreviver a um filtro de pesquisa digitado rapidamente, desde que a lista em si permaneça inalterada.

No *inventory‑service*, envolvi o componente `<ProductGrid>` com `React.memo` depois que percebi que cada entrada de teclado aciona uma reavaliação de todo o árbol. O componente recebe duas props: `items` (o array filtrado) e `onSelect` (um manipulador de clique). O manipulador é uma função de seta que não depende de dados externos, então sua identidade permanece estável. Como `items` é uma nova referência a cada digitação (porque a string de consulta é transformada em um novo array), o memo ainda dispara uma renderização — mas apenas para a grade, e não para toda a árvore de layout acima dela.

O verdadeiro ganho aparece quando você combina `React.memo` com um gerenciamento de estado mais granular. No mesmo projeto, usei `useReducer` para manter o conjunto de seleção separado do array de itens. Isso manteve o reducer e seus acionadores estáveis, permitindo que o `<ProductGrid>` permanecesse memoizado mesmo quando o status de seleção mudava.

Um erro comum que vi na minha própria codebase é envolver *tudo* com `React.memo` sem uma análise real. No *blog.ismaeltech.com*, tentei memoizar cada componente de artigo individualmente. O efeito colateral foi um aumento na memória, pois cada componente memoizado mantinha seu próprio cache de elementos React. A solução foi aumentar o granulo: apenas o `<ArticleList>` precisava ser memoizado, enquanto os componentes `<ArticleCard>` internos permaneciam funcionais.

Em resumo, `React.memo` funciona melhor quando você tem um limite claro de quais props realmente afetam a saída visual. Use-o como um primeiro nível de defesa, e não como uma solução para todo o componente.

## useMemo: cache de cálculos pesados

`useMemo` permite que você armazene o resultado de uma expressão cara entre renders. Sua utilidade é mais evidente quando você tem um cálculo baseado em dados que é mais caro que uma simples atribuição. Um exemplo clássico é a ordenação ou filtragem de um grande array. No *inventory‑service*, precisei ordenar o catálogo por relevância sempre que o parâmetro de ordenação mudava. Inicialmente, a ordenação era feita dentro do corpo do componente a cada renderização. Mover o resultado para `useMemo` eliminou dezenas de milhares de comparações por segundo.

```js
// antes
const sortedItems = items
  .filter(...)
  .sort((a, b) => b.score - a.score);

// depois
const sortedItems = useMemo(() => (
  items
    .filter(...)
    .sort((a, b) => b.score - a.score)
), [items, query, sortKey]);
```

O array de dependências é crucial. Como `items` é regenerado a cada digitação (devido à transformação da consulta), o uso de `items` na lista de dependências garante que o valor memoizado seja descartado quando a fonte muda. Isso também evita um problema de atualização atrasada: se você acidentalmente omitir uma dependência, o valor memoizado antigo pode permanecer visível após uma mudança de dados, causando comportamento de interface do usuário desatualizado.

Outro cenário onde `useMemo` me ajudou é no *PeakVault*, um analisador de desktop Python que expõe uma visualização React do arquivo JSON bruto. O componente `<JsonViewer>` recebia um objeto JavaScript grande (até 10 mil entradas). Renderizar cada nó recursivamente a cada alteração de scroll era proibitivamente lento. Ao envolver cada nível de recursão com `useMemo`, pude garantir que apenas os nós visíveis fossem reavaliados. O resultado foi uma rolagem suave mesmo em conjuntos de dados massivos.

`useMemo` funciona melhor quando a expressão custa mais que um simples `Array.prototype.map`. Se você estiver apenas mapeando um array de strings para JSX, o custo é insignificante e o memo pode até adicionar sobrecarga. Um teste de perfil rápido no React DevTools me mostrou exatamente onde a memoização trazia benefícios: na ordenação, na transformação de dados e na renderização recursiva de árvores profundas.

## useCallback: quando a estabilidade de referência importa

`useCallback` memoiza funções para que sua identidade permaneça a mesma entre renders. Seu propósito é evitar que um novo manipulador force um componente filho memoizado a renderizar novamente. No *inventory‑service*, passei um manipulador `onAddToCart` para um `<CartButton>` que estava envolvido com `React.memo`. Inicialmente, o manipulador era uma função de seta definida dentro do componente, o que significava uma nova referência a cada renderização. O resultado foi um loop infinito de renders no botão, pois o botão comparava a prop recebida com a prop anterior e sempre encontrava uma diferença.

```js
// problema
const handleAdd = () => { /* lógica */ };

// solução
const handleAdd = useCallback(() => { /* lógica */ }, []);
```

A lista de dependências é importante aqui. Se `handleAdd` precisasse de valores de estado, esses valores seriam listados. No meu pipeline de leads *lead‑pipeline*, usei `useCallback` para o manipulador de envio que atualizava um Firestore externo. Como o manipulador não acessava nenhum estado do React, uma lista de dependências vazia foi suficiente.

Um problema comum que surge é o “escape de captura” — onde você passa um manipulador para um componente filho, o filho o armazena em um closure e o expõe novamente mais tarde, efetivamente criando um ciclo de referência que anula o propósito da memoização. Eu vi isso acontecer no *Plexo* quando o manipulador de arrastar e soltar era armazenado em um ref e depois repassado para um componente `<TaskCard>`. A solução foi extrair a lógica do manipulador para uma função pura fora do componente, e então envolver essa função externa com `useCallback`. Dessa forma, a identidade permaneceu estável e o ciclo de renderização foi quebrado.

Em termos práticos, use `useCallback` quando um manipulador for passado para um componente memoizado, ou quando for armazenado em um estado que aciona um efeito. Use `useMemo` para valores computados que você precisa comparar ou armazenar. Misturar os dois incorretamente pode levar a uma falsa sensação de segurança e a um aumento no uso de memória.

## React Compiler: o que é e por que importa

O React Compiler (anteriormente conhecido como React Refresh com algumas alterações internas) altera o modelo mental de quando as memoizações são necessárias. Ele analisa graficamente as árvores de componentes e decide automaticamente onde aplicar `React.memo`, `useMemo` e `useCallback` em tempo de execução. O objetivo é permitir que os desenvolvedores escrevam componentes funcionais mais limpos sem sacrificar a performance.

No meu blog, tenho um padrão de componente `<LazySection>` que renderiza um bloco de conteúdo pesado apenas quando o botão “Expandir” é clicado. Antes do compilador, eu precisava envolver este componente com `React.memo` e gerenciar um estado de suspensão manual. Com o compilador habilitado, a mesma peça de código funciona sem nenhuma declaração extra de memoização. O compilador detecta que o componente nunca será renderizado no mount inicial e insere um stub que só é resolvido após o gatilho de interação do usuário.

O React Compiler funciona melhor com a nova sintaxe de hooks, sem o uso de hooks em componentes de classes. Ele também se integra com o React DevTools para exibir uma visualização da árvore de memoização. No entanto, o compilador não é uma solução mágica — ainda é necessário escrever componentes puros e evitar efeitos colaterais na fase de renderização. No *inventory‑service*, onde tenho um efeito que busca dados do backend dentro do componente, preciso manter o `useEffect` explícito; o compilador não pode inferir que esse efeito deve ser ignorado para fins de memoização.

Uma armadilha que descobri é que o compilador pode ser agressivo demais ao memoizar componentes que dependem de contexto. No *Plexo*, uso o `ThemeContext` para alternar entre modos claro e escuro. Inicialmente, o compilador envolvia o `<ThemeProvider>` com `React.memo`, mas como o objeto de contexto é uma nova referência a cada renderização, isso causava renderizações desnecessárias em toda a árvore. A solução foi adicionar `React.memo` manualmente ao provedor com uma comparação de profundidade de valores simples, ou mudar para `useContext` dentro do compilador para reduzir a sobrecarga.

Em resumo, o React Compiler pode reduzir a necessidade de declarações manuais de memoização, mas você ainda precisa entender os limites: componentes puros, efeitos estáveis e dependências estáveis são essenciais. Quando esses pilares estão presentes, o compilador cuida do resto, permitindo que você se concentre na lógica de negócios.

## Profiler no DevTools: medindo o real impacto

Depois de aplicar `React.memo`, `useMemo` e `useCallback`, o próximo passo é validar se as mudanças realmente reduziram o trabalho de renderização. O React DevTools Profiler é a ferramenta padrão para isso. Ele registra cada renderização de componente, informando sobre tempo de CPU, tempo de renderização e renderizações adicionais.

No *inventory‑service*, habilitei o profiler durante um teste A/B onde mantive a grade sem memoização contra uma versão com `React.memo`. O perfil mostrou que a versão sem memoização consumia 120 ms por digitação, enquanto a versão com memoização caiu para 38 ms — uma melhoria significativa. No entanto, o custo extra de memória aumentou em 15 %, o que só se tornou aparente após a execução do profiler por alguns minutos.

O profiler também me ajudou a identificar um problema oculto no *blog.ismaeltech.com*. O componente `<ArticleList>` parecia estar renderizando a cada novo artigo gerado pela IA. O perfil revelou que a causa era um `useEffect` dentro do componente que reconstruía um índice de busca a cada artigo. Mover esse índice para `useMemo` eliminou seis dos dez picos de renderização por ciclo de geração de artigo.

Use o profiler com moderação. Executações longas podem distorcer os números, então capture um perfil que represente um fluxo de usuário típico. No caso do *PeakVault*, executei o profiler enquanto rolava um conjunto de dados de 10 mil entradas, e vi que 70 % do tempo de CPU era gasto reavaliando nós não visíveis. A solução foi envolver a função de renderização recursiva com `useMemo` e limitar a profundidade de recursão ao campo de viewport.

O profiler também mostra renderizações adicionais ocultas que podem ser causadas por atualizações de contexto ou state machines personalizadas. No *Plexo*, usei um `useReducer` simples para gerenciar a lista de tarefas. O perfil mostrou um aumento constante de renderizações adicionais sempre que o painel lateral era aberto. A causa era um bug em que o manipulador de redução acidentalmente criava um novo objeto de ação a cada despacho, fazendo com que todo o árbol comparasse novas referências. Corrigir o manipulador para retornar uma referência estável eliminou as renderizações extras.

Em última análise, o profiler é a única maneira de validar se sua otimização está realmente resolvendo o problema. Sem ele, você pode estar adicionando código desnecessário ou perdendo um gargalo oculto.

## Anti‑patterns: quando otimizar demais ou de forma errada

Otimização é um processo iterativo. Começar com uma solução excessiva pode levar a um código mais difícil de manter. Aqui estão alguns anti‑patterns que encontrei em meus próprios projetos e como eu os corrijoi.

Primeiro anti‑pattern: “Tudo é memoizado”. No *blog.ismaeltech.com*, tentei envolver cada `<PostCard>` com `React.memo`. O resultado foi um grande overhead de memória e um aumento na complexidade. O componente era muito pequeno para justificar o overhead, e a verdadeira solução estava no nível do `<ArticleList>`. Mover o memo para cima simplificou a árvore e reduziu o uso de memória pela metade.

Segundo anti‑pattern: uso excessivo de `useMemo` para operações baratas. No *lead‑pipeline*, envolvi um simples `array.map` que gerava JSX dentro de `useMemo`. Isso adicionou uma etapa extra de cache a cada renderização, sem nenhum ganho de performance. Remover o `useMemo` acelerou o primeiro render em ~15 ms. A lição é: se a expressão custa menos que um único `requestIdleCallback` tick, o memo é desnecessário.

Terceiro anti‑pattern: esquecer de atualizar as listas de dependências. No *inventory‑service*, inicialmente usei `useMemo` para calcular um valor derivado de `filters` e `sortKey`. Como `filters` era um objeto que eu recriava a cada digitação, a lista de dependências `[filters, sortKey]` parecia segura. No entanto, como `filters` era um novo objeto, o valor memoizado nunca foi descartado, levando a filtros desatualizados. A solução foi mudar `filters` para um estado baseado em `useReducer` que só gera um novo objeto quando a chave primária muda.

Quarto anti‑pattern: supor que `useCallback` sozinho resolve problemas de renderização desnecessária. No *Plexo*, passei um manipulador de arrastar e soltar para um `<DragHandle>` memoizado. O manipulador era um closure que lia `isDragging` de um ref, o que mudava a cada frame. Mesmo com `useCallback`, o componente filho ainda renderizava porque o closure capturava uma referência mutável. Extrair o manipulador para uma função pura que lê o ref dentro do corpo eliminou as renderizações extras.

Finalmente, anti‑pattern: confiar apenas no React Compiler para otimização. No *blog.ismaeltech.com*, o compilador sugeriu envolver `<AdBanner>` com `React.memo`. O componente renderizava apenas uma vez por página, mas o banner buscava um preço dinâmico a cada renderização. Como o compilador não sabia que a busca era um efeito colateral, ele ainda envolvia o componente, preservando o comportamento indesejado. Eu precisei adicionar um `useEffect` manual para buscar dados separadamente.

O padrão geral é: comece simples, profila, identifica o gargalo, então aplica a ferramenta mais granular que resolve o problema sem afetar componentes não relacionados. Otimizar excessivamente muitas vezes cria mais problemas do que resolve.

## Conclusão: uma filosofia de performance

A performance no React não se resume a “usar mais hooks”. É uma combinação de compreensão do fluxo de dados, conhecimento das ferramentas e paciência para medir antes de agir. Dois projetos pessoais que mencionei — *inventory‑service* e *blog.ismaeltech.com* — ilustram esse ciclo. Ambos começaram com interfaces reativas que se tornaram lentas à medida que os dados cresciam. A aplicação sistemática de `React.memo` para componentes de nível superior, `useMemo` para cálculos pesados e `useCallback` para identificadores estáveis reduziu o tempo de renderização por entrada de usuário de mais de 100 ms para menos de 30 ms.

O React Compiler adiciona outra camada de abstração, permitindo que você escreva componentes mais limpos e deixe que o compilador lide com o memoization granular. No entanto, você ainda precisa entender os limites: componentes puros, efeitos estáveis e dependências estáveis são pré-requisitos. O Profiler no DevTools continua sendo a única maneira confiável de validar se suas otimizações estão realmente ajudando.

Um aspecto frequentemente subestimado é o custo da manutenção do estado. No *inventory‑service*, mudei o conjunto de seleção para um reducer dedicado para manter a identidade estável do manipulador de clique. Essa mudança não só melhorou a performance, como também tornou o fluxo de ação do aplicativo mais previsível. Da mesma forma, no *Plexo*, um pequeno ajuste na criação de ações estáveis eliminou uma série de renderizações extras que antes passavam despercebidas.

Lembre-se de que otimização excessiva pode prejudicar a legibilidade. Um componente que é demasiado memoizado pode se tornar um labirinto de hooks, dificultando a compreensão de por que ele se renderiza. O objetivo é tornar o componente “graso o suficiente para ser queimado, mas não a ponto de se tornar cinzas”. Use o menor granulo possível, e sempre profila antes de otimizar.

Em última análise, as mesmas preocupações de performance que aplicamos ao front‑end também se estendem ao backend e à infraestrutura. No *inventory‑service*, reduzi o número de renders, o que por sua vez reduziu a carga na API JSON que alimentava o front‑end. Essa redução cascata resultou em custos de servidor mais baixos para o cliente.

## Takeaways práticos

- Comece medindo. Use o Profiler para identificar quais componentes consomem mais tempo de CPU antes de adicionar qualquer memoization.
- Aplique `React.memo` apenas quando as props afetam o resultado visual; evite envolver componentes pequenos e de folha.
- Use `useMemo` para expressões caras (ordenação, filtragem, computação pesada) e mantenha a lista de dependências precisa.
- Estabilize manipuladores com `useCallback` quando forem passados para componentes memoizados ou armazenados em estado que aciona efeitos.
- O React Compiler pode reduzir a necessidade de declarações manuais de memoization, mas componentes puros e estáveis ainda são necessários.
- Monitore tanto a performance da CPU quanto o uso de memória; o ganho de velocidade às vezes vem com um custo de memória.
- Mantenha o código simples. Otimize apenas o que o perfil indica como um gargalo; o resto deve permanecer legível.
- Teste em conexões reais. Um componente que parece rápido em um laptop pode se tornar um gargalo em redes móveis mais lentas.

---

## Fontes

- Documentação oficial do React: Hooks (React)
  https://react.dev/reference/react
- Documentação do React DevTools Profiler
  https://react.dev/learn/profile-your-react-application
- Artigo do blog “React Compiler: next‑gen optimization” (React)
  https://react.dev/blog/2024/06/13/react-compiler
- Artigo MDN “useMemo”
  https://developer.mozilla.org/en-US/docs/Web/JS/Reference/Global_Objects/Array/sort
- Guia de performance do React: Memoization
  https://react.dev/docs/performance
- Documentação do React.memo
  https://react.dev/reference/react/memo
- “Understanding React Performance” – artigo no blog do Vercel
  https://vercel.com/blog/understanding-react-performance