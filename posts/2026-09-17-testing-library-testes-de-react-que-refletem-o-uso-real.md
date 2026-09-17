---
title: "Testing Library: testes de React que refletem o uso real"
date: "2026-09-17"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "Quando comecei a testar interfaces com React, fazia tudo errado. Escrevia testes que verificavam como o componente era construído – se esse botão tem a classe .btn-primary e"
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-09-17-testing-library-testes-de-react-que-refletem-o-uso-real.jpg"
lang: "pt"
---

Quando comecei a testar interfaces com React, fazia tudo errado. Escrevia testes que verificavam como o componente era construído – "se esse botão tem a classe `.btn-primary` e dispara o evento `onClick`". Funcionava nos testes, mas quebrava silenciosamente em produção quando alguém mudava a implementação interna. Isso até trabalhar no OSPOS na loja onde cuidava do PDV: descobri que o problema real não era código quebrado, era código que parecia funcionar nos testes, mas não nos fluxos reais dos vendedores.

O problema não era a lógica, era a perspectiva. Meus testes validavam a perspectiva do desenvolvedor, não do usuário. Foi quando descobri o React Testing Library – uma biblioteca que te obriga (de forma amigável) a testar como o usuário realmente interage com sua aplicação.

## O princípio: testa o que o usuário vê

A ideia central do React Testing Library é simples: seus testes devem ser escritos como se fossem um guia para alguém usar sua interface sem ver o código. Não importa se você usa `useState`, `useReducer`, ou se o componente é funcional ou classe. O que importa é: o usuário consegue ver isso? Consegue clicar nisso? Recebe feedback claro quando faz algo?

Isso muda tudo. Em vez de afirmar "o botão tem o atributo `aria-label='Salvar'`", seu teste diz "o botão com o texto 'Salvar' existe e responde a cliques". Não porque você está seguindo uma regra arbitrária, mas porque é exatamente assim que um vendedor na Loja Quase Tudo interage com o PDV: ele vê um botão escrito, clica, e espera um resultado tangível.

No projeto `inventory-service`, que sincroniza catálogo e estoque entre OSPOS e Mercado Livre, isso fez diferença real. Em vez de testar se o componente chamava corretamente a API, testava se, após preencher o formulário e clicar em "Sincronizar", o usuário via uma mensagem de sucesso ou erro clara. O código mudou várias vezes, mas o comportamento visível – o que o usuário vê e usa – permanecia o mesmo.

## Queries: encontrando elementos como um usuário faria

As queries do Testing Library são categorizadas por prioridade. Isso não é casual: é um lembrete de que você deve buscar elementos da maneira mais próxima possível do que um usuário faria.

A ordem de prioridade (da mais para menos recomendada) é:

- `getBy`: para elementos que você espera que sempre existam. Se falhar, é erro real.
- `queryBy`: para elementos que podem ou não existir (ex: mensagens de erro). Não dispara exceção se não encontrar.
- `findBy`: para elementos que aparecem de forma assíncrona. Retorna uma promessa.

No dia a dia, use `getBy` e `findBy` na maioria dos casos. `queryBy` serve para cenários específicos, como validar que um campo de erro não aparece inicialmente.

Exemplo prático, do projeto `Plexo` (gerenciador de tasks com UI React/Vite):

```javascript
import { render, screen, waitFor } from '@testing-library/react'
import TaskForm from '../TaskForm'

test('exibe erro quando título está vazio', async () => {
  render(<TaskForm onSubmit={vi.fn()} />)
  
  // Pega o botão "Criar Task"
  const createButton = screen.getByRole('button', { name: /criar task/i })
  
  // Clica sem preencher o título
  await userEvent.click(createButton)
  
  // Verifica que o erro apareceu
  const errorMessage = screen.getByText(/título é obrigatório/i)
  expect(errorMessage).toBeInTheDocument()
})
```

Note que eu não procuro pelo `id` do botão, nem pelo seletor CSS `.task-form button[type="submit"]`. Procuro pelo texto visível e acessível que um usuário lerá. Isso garante que, mesmo se eu mudar a estrutura HTML ou classes CSS, o teste ainda valide a intenção real: o botão cria uma task.

Uma confusão comum é usar `getByLabelText` para campos onde não há label visível. Se o campo tem apenas um placeholder (ex: `<input placeholder="Título" />`), use `getByPlaceholderText`, não `getByLabelText`. A label visual ou `aria-label` é o que o usuário associa ao campo. Um placeholder é um guia, não um rótulo.

## User events: simule ação real, não evento DOM

Outro erro comum é usar `fireEvent.click(button)`. Funciona, mas ignora comportamentos importantes do navegador: focus, eventos do teclado, acessibilidade.

O Testing Library traz o `@testing-library/user-event`, que simula interações reais de usuário. Um clique com `userEvent.click` dispara todos os eventos associados (`mouseenter`, `focus`, `mousedown`, `mouseup`, `click`), como o usuário esperaria.

Exemplo: no sistema `Cronograma de Estudos`, com gamificação e feedback visual, precisava garantir que os botões de navegação entre módulos funcionassem corretamente. Testar com `fireEvent.click` não validava se o foco era movido para o próximo elemento (para usuários de leitor de tela). Com `userEvent`, sim.

```javascript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ModuleNavigation from '../ModuleNavigation'

test('navega para o próximo módulo e mantém foco', async () => {
  const user = userEvent.setup()
  render(<ModuleNavigation currentModule={1} totalModules={5} />)
  
  const nextButton = screen.getByRole('button', { name: /próximo módulo/i })
  
  await user.click(nextButton)
  
  // O foco agora está no botão do novo módulo ativo
  const activeModuleButton = screen.getByRole('button', { 
    name: /módulo 2/i,
    selected: true 
  })
  
  expect(activeModuleButton).toHaveFocus()
})
```

Isso é crucial em projetos com acessoibilidade em mente (como o sistema para a ONG `Mensageiros da Esperança`, com 100+ voluntários). Se o foco não se comportar como esperado, usuários com deficiência visual encontram barreiras reais.

## Async testing: quando o mundo não para

Interfaces modernas são cheias de assincronicidade: carregamento de API, animações, reações a eventos. O Testing Library oferece ferramentas para lidar com isso sem truques sujos.

- `await screen.findByText('Sucesso')`: espera até que o texto apareça.
- `waitFor(() => expect(...))`: executa uma asserção repetidamente até que ela passe ou timeout.

Exemplo real: no `inventory-service`, ao sincronizar produtos, o botão muda para "Sincronizando..." com um loading.

```javascript
test('mostra loading durante sincronização e atualiza após sucesso', async () => {
  const user = userEvent.setup()
  render(<SyncButton />)

  const syncButton = screen.getByRole('button', { name: /sincronizar/i })
  
  // Clica e espera o loading aparecer
  await user.click(syncButton)
  const loadingButton = await screen.findByRole('button', { name: /sincronizando\.\.\./i })
  expect(loadingButton).toBeDisabled()

  // Agora espera o botão voltar ao estado inicial com sucesso
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /sincronizar/i })).toBeInTheDocument()
  })
})
```

Note que não uso `setTimeout` ou `wait(1000)`. O `findBy` e `waitFor` reagem ao que realmente acontece na DOM, não a tempo fixo. Isso torna os testes rápidos e confiáveis.

## Mocking API: controle sem dependência real

Testar componentes que consomem APIs é delicado. Você não quer depender de um servidor real, nem correr risco de testes flaky por falhas de rede.

No ecossistema de IA local que construí (como o `provider-health-daemon`), uso `msw` (Mock Service Worker). Ele intercepta requisições na camada de rede, simulando respostas sem precisar de servidor.

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

No componente, basta renderizar:

```javascript
import { render, screen } from '@testing-library/react'
import ModelSelector from '../ModelSelector'

test('exibe modelos após carregar', async () => {
  render(<ModelSelector />)
  
  // Aguarda o texto aparecer
  expect(await screen.findByText(/Llama 2/i)).toBeInTheDocument()
  expect(screen.getByText(/Mistral 7B/i)).toBeInTheDocument()
})
```

A vantagem de `msw` é que ele intercepta tanto requisições reais quanto simuladas. Se você usar `fetch` ou `axios`, o mock funciona igual. Não precisa mudar a lógica do componente só para testar.

Caso não queira adicionar `msw`, o mock simples com `vi.mock` também funciona:

```javascript
vi.mock('../api/models', () => ({
  fetchModels: vi.fn(() => Promise.resolve([
    { id: 'llama-2', name: 'Llama 2' }
  ]))
}))
```

Mas aí você testa a implementação (se o `fetchModels` foi chamado), não o comportamento visível. Prefira `msw` sempre que possível.

## Coverage: métrica útil, mas com cuidado

Alguém já te disse que seus testes precisam de 90% de cobertura? Pare de ouvir isso.

Cobertura mede linhas de código executadas pelos testes. Não mede se você testou o comportamento certo. É fácil chegar a 100% cobertura testando apenas a função `render` de um componente. Isso não garante nada sobre a experiência do usuário.

No entanto, cobertura baixa pode indicar lacunas. Um bom uso é filtrar por componentes críticos (ex: formulários de checkout, fluxos de pagamento) e verificar se tem testes neles. Não importa o número exato.

No `lead-pipeline`, o sistema que manipula leads com IA, os fluxos de importação e enriquecimento têm testes, mas a cobertura é secundária. O que importa é que cada etapa do processo (upload CSV → parse → enriquecer → salvar) tenha uma validação clara, com mensagens acessíveis para o usuário.

## Conclusão: escreva testes que duram

Testar com o React Testing Library não é mais trabalho extra. É uma forma de documentar o comportamento da interface de maneira que outros desenvolvedores (ou você daqui a 6 meses) saibam exatamente como o código deve se comportar.

A diferença entre um teste fraco e um forte:

- Fraco: "O botão deve disparar `handleClick`"
- Forte: "Ao clicar no botão 'Salvar', o usuário vê uma mensagem de confirmação"

O segundo teste não quebra se você refatorar o componente para usar `useReducer` em vez de `useState`. O comportamento percebido pelo usuário é o que importa – não a mecânica interna.

Essa mentalidade não veio de anos de experiência em grandes empresas. Veio de ver um vendedor na loja perdendo tempo porque um botão parecia clicável, mas não fazia nada (a classe `.pointer-events-none` estava escondida num CSS complexo). Os testes anteriores passavam – mas o usuário não via o que estava errado.

Aprendi que bom código é aquele que se comporta como esperado, ponto. O resto é detalhe de implementação.

Aqui estão alguns exemplos práticos que uso:

- Sempre comece com queries baseadas em texto acessível ou roles (`getByRole`, `getByText`)
- Use `userEvent` para todas as interações que envolvem cliques, digitação ou navegação
- Prefira `findBy` e `waitFor` para assíncrono, não `wait` ou `setTimeout`
- Mocke APIs com `msw` se quiser fidelidade total ao comportamento do navegador
- Esqueça a cobertura percentual. Foque em cobrir fluxos reais de usuário

Se um teste precisar de um reajuste quando você renomeia um botão ou muda um id, ele está testando a implementação – não o comportamento. Refatore até ele falhar apenas quando o usuário vê algo quebrado.

No fim, testar assim não é mais difícil. É só diferente. Mas é o jeito certo de garantir que seu código não quebre quando o mundo real o usa.

## Fontes

- [React Testing Library: Getting Started](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library: Principal Concepts](https://testing-library.com/docs/guiding-principles/)
- [Kent C. Dodds: How to know if a test is good](https://kentcdodds.com/blog/how-to-know-if-a-test-is-good)
- [MSW: Mock Service Worker](https://mswjs.io/)
- [React Docs: Testing](https://react.dev/learn/testing)
- [User Event: Official Documentation](https://testing-library.com/docs/user-event/intro)
## 📸 Crédito da imagem de capa
- **Imagem:** [Dragon 2 hover test (24159153709).jpg](https://commons.wikimedia.org/wiki/File%3ADragon_2_hover_test_%2824159153709%29.jpg)
- **Autor(a):** SpaceX Photos
- **Licença:** [CC0](https://creativecommons.org/publicdomain/zero/1.0/) · via Wikimedia Commons
