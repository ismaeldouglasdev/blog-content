---
title: "Testing Library: testes de React que refletem o uso real"
date: "2026-09-17"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "Guia prático de React Testing Library: queries acessiveis, userEvent, testes assincronos, mocking com MSW e por que cobertura nao e tudo."
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-09-17-testing-library-testes-de-react-que-refletem-o-uso-real.jpg"
lang: "pt"
---

React Testing Library mudou a forma como testamos interfaces: o foco sai da implementacao e vai para o comportamento que o usuario ve e usa. Este guia cobre os principios, queries, interacoes reais, assincronicidade, mocking e a armadilha da cobertura.

## O principio: testa o que o usuario ve

A ideia central e simples: testes devem validar o comportamento visivel, nao a estrutura interna. Nao importa se o componente usa `useState`, `useReducer` ou classes. O que importa: o usuario consegue ver o elemento? Consegue interagir? Recebe feedback claro?

Em vez de afirmar "o botao tem o atributo `aria-label='Salvar'`", o teste verifica "o botao com o texto 'Salvar' existe e responde a cliques". Isso garante que refatoracoes internas nao quebrem os testes - apenas mudancas no comportamento percebido pelo usuario.

## Queries: encontrando elementos como um usuario faria

As queries sao categorizadas por prioridade, da mais para a menos recomendada:

- `getBy`: para elementos que sempre devem existir. Falha se nao encontrar.
- `queryBy`: para elementos opcionais (ex: mensagens de erro). Nao dispara excecao.
- `findBy`: para elementos assincronos. Retorna promise.

No dia a dia, use `getBy` e `findBy`. `queryBy` serve para validar ausencia inicial.

Exemplo pratico:

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskForm from '../TaskForm'

test('exibe erro quando titulo esta vazio', async () => {
  render(<TaskForm onSubmit={vi.fn()} />)
  
  const createButton = screen.getByRole('button', { name: /criar task/i })
  await userEvent.click(createButton)
  
  const errorMessage = screen.getByText(/titulo e obrigatorio/i)
  expect(errorMessage).toBeInTheDocument()
})
```

Procura-se pelo texto visivel e acessivel, nao por `id` ou seletor CSS. Isso torna testes resilientes a mudancas de estrutura HTML ou classes.

Cuidado com `getByLabelText` em campos sem label visivel. Se so ha placeholder (`<input placeholder="Titulo" />`), use `getByPlaceholderText`. Placeholder e guia, nao rotulo.

## User events: simule acao real, nao evento DOM

`fireEvent.click` ignora comportamentos do navegador: focus, eventos de teclado, acessibilidade. Use `@testing-library/user-event` que simula interacoes reais - um clique dispara `mouseenter`, `focus`, `mousedown`, `mouseup`, `click`.

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ModuleNavigation from '../ModuleNavigation'

test('navega para o proximo modulo e mantem foco', async () => {
  const user = userEvent.setup()
  render(<ModuleNavigation currentModule={1} totalModules={5} />)
  
  const nextButton = screen.getByRole('button', { name: /proximo modulo/i })
  await user.click(nextButton)
  
  const activeModuleButton = screen.getByRole('button', { 
    name: /modulo 2/i,
    selected: true 
  })
  expect(activeModuleButton).toHaveFocus()
})
```

Isso e essencial para acessibilidade: se o foco nao se move corretamente, usuarios de leitor de tela encontram barreiras.

## Async testing: quando o mundo nao para

Interfaces modernas sao assincronas: carregamento de API, animacoes, eventos. Testing Library oferece ferramentas sem truques:

- `await screen.findByText('Sucesso')`: espera ate aparecer.
- `waitFor(() => expect(...))`: repete assercao ate passar ou timeout.

```javascript
test('mostra loading durante sincronizacao e atualiza apos sucesso', async () => {
  const user = userEvent.setup()
  render(<SyncButton />)

  const syncButton = screen.getByRole('button', { name: /sincronizar/i })
  
  await user.click(syncButton)
  const loadingButton = await screen.findByRole('button', { name: /sincronizando\.\.\./i })
  expect(loadingButton).toBeDisabled()

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /sincronizar/i })).toBeInTheDocument()
  })
})
```

`findBy` e `waitFor` reagem ao DOM real, nao a tempo fixo - testes rapidos e confiaveis.

## Mocking API: controle sem dependencia real

Testar componentes que consomem APIs exige isolamento. `msw` (Mock Service Worker) intercepta requisicoes na camada de rede, simulando respostas sem servidor.

```javascript
// setupTests.js
import { setupServer } from 'msw/node'
import { handlers } from './mocks/handlers'

export const server = setupServer(...handlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

```javascript
// mocks/handlers.js
import { rest } from 'msw'

export const handlers = [
  rest.get('/api/models', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json([
      { id: 'llama-2', name: 'Llama 2' },
      { id: 'mistral-7b', name: 'Mistral 7B' }
    ]))
  })
]
```

Vantagem do `msw`: intercepta tanto `fetch` quanto `axios` sem mudar logica do componente. Prefira a `vi.mock` que testa implementacao, nao comportamento visivel.

## Cobertura: metrica util, mas com cuidado

Cobertura mede linhas executadas, nao se o comportamento certo foi testado. Facil chegar a 100% testando so `render`. Nao garante experiencia do usuario.

Uso pratico: filtre componentes criticos (checkout, pagamento, formularios) e verifique se tem testes neles. O numero exato e secundario - o que importa e validar fluxos reais com mensagens acessiveis.

## Conclusao: escreva testes que duram

Testar com React Testing Library documenta comportamento de forma que outros (ou voce no futuro) saibam como o codigo deve se comportar.

Diferenca entre teste fraco e forte:

- Fraco: "O botao deve disparar `handleClick`"
- Forte: "Ao clicar em 'Salvar', o usuario ve uma mensagem de confirmacao"

O segundo nao quebra se refatorar para `useReducer`. O comportamento percebido e o que importa.

Resumo pratico:
- Comece com queries baseadas em texto acessivel ou roles (`getByRole`, `getByText`)
- Use `userEvent` para cliques, digitacao, navegacao
- Prefira `findBy` e `waitFor` para assincrono
- Mocke APIs com `msw` para fidelidade total
- Esqueca cobertura percentual. Foque em fluxos reais de usuario

Se um teste falha so por renomear botao ou mudar id, testa implementacao - nao comportamento. Refatore ate falhar apenas quando o usuario ve algo quebrado.

## Fontes

- [React Testing Library: Getting Started](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library: Principal Concepts](https://testing-library.com/docs/guiding-principles/)
- [Kent C. Dodds: How to know if a test is good](https://kentcdodds.com/blog/how-to-know-if-a-test-is-good)
- [MSW: Mock Service Worker](https://mswjs.io/)
- [React Docs: Testing](https://react.dev/learn/testing)
- [User Event: Official Documentation](https://testing-library.com/docs/user-event/intro)

## Credito da imagem de capa
- **Imagem:** [Dragon 2 hover test (24159153709).jpg](https://commons.wikimedia.org/wiki/File%3ADragon_2_hover_test_%2824159153709%29.jpg)
- **Autor(a):** SpaceX Photos
- **Licenca:** [CC0](https://creativecommons.org/publicdomain/zero/1.0/) via Wikimedia Commons
