---
title: "Testing Library: testes de React que refletem o uso real"
date: "2026-09-17"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "Guia prático de React Testing Library: queries acessíveis, userEvent, testes assíncronos, mocking com MSW e por que cobertura não é tudo."
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-09-17-testing-library-testes-de-react-que-refletem-o-uso-real.jpg"
lang: "pt"
---

React Testing Library mudou a forma como testamos interfaces: o foco sai da implementação e vai para o comportamento que o usuário vê e usa. Este guia cobre os princípios, queries, interações reais, assincronicidade, mocking e a armadilha da cobertura.

## O princípio: testa o que o usuário vê

A ideia central é simples: testes devem validar o comportamento visível, não a estrutura interna. Não importa se o componente usa `useState`, `useReducer` ou classes. O que importa: o usuário consegue ver o elemento? Consegue interagir? Recebe feedback claro?

Em vez de afirmar "o botão tem o atributo `aria-label='Salvar'`", o teste verifica "o botão com o texto 'Salvar' existe e responde a cliques". Isso garante que refatorações internas não quebrem os testes — apenas mudanças no comportamento percebido pelo usuário.

## Queries: encontrando elementos como um usuário faria

As queries são categorizadas por prioridade, da mais para a menos recomendada:

- `getBy`: para elementos que sempre devem existir. Falha se não encontrar.
- `queryBy`: para elementos opcionais (ex: mensagens de erro). Não dispara exceção.
- `findBy`: para elementos assíncronos. Retorna promise.

No dia a dia, use `getBy` e `findBy`. `queryBy` serve para validar ausência inicial.

Exemplo prático:

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TaskForm from '../TaskForm'

test('exibe erro quando título está vazio', async () => {
  render(<TaskForm onSubmit={vi.fn()} />)
  
  const createButton = screen.getByRole('button', { name: /criar task/i })
  await userEvent.click(createButton)
  
  const errorMessage = screen.getByText(/título é obrigatório/i)
  expect(errorMessage).toBeInTheDocument()
})
```

Procura-se pelo texto visível e acessível, não por `id` ou seletor CSS. Isso torna testes resilientes a mudanças de estrutura HTML ou classes.

Cuidado com `getByLabelText` em campos sem label visível. Se só há placeholder (`<input placeholder="Título" />`), use `getByPlaceholderText`. Placeholder é guia, não rótulo.

## User events: simule ação real, não evento DOM

`fireEvent.click` ignora comportamentos do navegador: focus, eventos de teclado, acessibilidade. Use `@testing-library/user-event` que simula interações reais — um clique dispara `mouseenter`, `focus`, `mousedown`, `mouseup`, `click`.

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ModuleNavigation from '../ModuleNavigation'

test('navega para o próximo módulo e mantém foco', async () => {
  const user = userEvent.setup()
  render(<ModuleNavigation currentModule={1} totalModules={5} />)
  
  const nextButton = screen.getByRole('button', { name: /próximo módulo/i })
  await user.click(nextButton)
  
  const activeModuleButton = screen.getByRole('button', { 
    name: /módulo 2/i,
    selected: true 
  })
  expect(activeModuleButton).toHaveFocus()
})
```

Isso é essencial para acessibilidade: se o foco não se move corretamente, usuários de leitor de tela encontram barreiras.

## Async testing: quando o mundo não para

Interfaces modernas são assíncronas: carregamento de API, animações, eventos. Testing Library oferece ferramentas sem truques:

- `await screen.findByText('Sucesso')`: espera até aparecer.
- `waitFor(() => expect(...))`: repete asserção até passar ou timeout.

```javascript
test('mostra loading durante sincronização e atualiza após sucesso', async () => {
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

`findBy` e `waitFor` reagem ao DOM real, não a tempo fixo — testes rápidos e confiáveis.

## Mocking API: controle sem dependência real

Testar componentes que consomem APIs exige isolamento. `msw` (Mock Service Worker) intercepta requisições na camada de rede, simulando respostas sem servidor.

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

Vantagem do `msw`: intercepta tanto `fetch` quanto `axios` sem mudar lógica do componente. Prefira a `vi.mock` que testa implementação, não comportamento visível.

## Cobertura: métrica útil, mas com cuidado

Cobertura mede linhas executadas, não se o comportamento certo foi testado. Fácil chegar a 100% testando só `render`. Não garante experiência do usuário.

Uso prático: filtre componentes críticos (checkout, pagamento, formulários) e verifique se têm testes neles. O número exato é secundário — o que importa é validar fluxos reais com mensagens acessíveis.

## Conclusão: escreva testes que duram

Testar com React Testing Library documenta comportamento de forma que outros (ou você no futuro) saibam como o código deve se comportar.

Diferença entre teste fraco e forte:

- Fraco: "O botão deve disparar `handleClick`"
- Forte: "Ao clicar em 'Salvar', o usuário vê uma mensagem de confirmação"

O segundo não quebra se refatorar para `useReducer`. O comportamento percebido é o que importa.

Resumo prático:
- Comece com queries baseadas em texto acessível ou roles (`getByRole`, `getByText`)
- Use `userEvent` para cliques, digitação, navegação
- Prefira `findBy` e `waitFor` para assíncrono
- Mocke APIs com `msw` para fidelidade total
- Esqueça cobertura percentual. Foque em fluxos reais de usuário

Se um teste falha só por renomear botão ou mudar id, testa implementação — não comportamento. Refatore até falhar apenas quando o usuário vê algo quebrado.

## Fontes

- [React Testing Library: Getting Started](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library: Principal Concepts](https://testing-library.com/docs/guiding-principles/)
- [Kent C. Dodds: How to know if a test is good](https://kentcdodds.com/blog/how-to-know-if-a-test-is-good)
- [MSW: Mock Service Worker](https://mswjs.io/)
- [React Docs: Testing](https://react.dev/learn/testing)
- [User Event: Official Documentation](https://testing-library.com/docs/user-event/intro)

## Crédito da imagem de capa
- **Imagem:** [Dragon 2 hover test (24159153709).jpg](https://commons.wikimedia.org/wiki/File%3ADragon_2_hover_test_%2824159153709%29.jpg)
- **Autor(a):** SpaceX Photos
- **Licença:** [CC0](https://creativecommons.org/publicdomain/zero/1.0/) via Wikimedia Commons
