---
title: "Testing Library: testes de React que refletem o uso real"
date: "2026-09-01"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "Você já viu um teste verde no CI e, na hora de abrir a aplicação, o botão que deveria estar habilitado continua desabilitado? Essa desconexão entre o que o teste verifica e o"
lang: "pt"
---

## Introdução  

Você já viu um teste verde no CI e, na hora de abrir a aplicação, o botão que deveria estar habilitado continua desabilitado? Essa desconexão entre o que o teste verifica e o que o usuário realmente vê é a raiz de bugs que custam tempo e dinheiro. Quando comecei a migrar o catálogo da **Loja Quase Tudo** para o OSPOS, percebi que a maioria dos testes de interface eram baseados em detalhes de implementação – seletores de classe, chamadas de função interna – e não no fluxo que o cliente experimenta. Foi aí que descobri o **Testing Library** e, desde então, ele se tornou a ferramenta padrão nos meus projetos React, como o **inventory‑service** e o **Plexo**.  

Neste texto, mostro como usar a Testing Library para escrever testes que realmente refletem o uso real, evitando armadilhas comuns e garantindo que o comportamento do usuário seja o critério principal de aceitação.

## Princípio: teste o que o usuário vê  

A filosofia da Testing Library pode ser resumida em uma frase: *testar a aplicação da mesma forma que o usuário a utiliza*. Em vez de procurar por `data-test-id` ou por funções internas, buscamos por texto, rótulos, papéis e nomes acessíveis. Essa abordagem tem três benefícios claros:

1. **Manutenção mais fácil** – quando um detalhe de implementação muda, o teste permanece válido porque o fluxo do usuário não mudou.  
2. **Acessibilidade garantida** – ao usar queries baseadas em atributos ARIA, o teste força a equipe a produzir markup acessível.  
3. **Confiança na entrega** – se o teste passa, o usuário vê exatamente o que o teste descreve.

No meu projeto **inventory‑service**, que sincroniza OSPOS com o Mercado Livre, escrevi o primeiro teste de um formulário de criação de produto usando apenas o rótulo do campo “Nome do Produto”. Quando a equipe decidiu mudar o `id` do input, o teste continuou verde porque o usuário ainda interage pelo mesmo rótulo.

## Queries: como encontrar elementos na tela  

A Testing Library oferece três grupos de queries:

| Grupo | Quando usar | Exemplo |
|-------|-------------|---------|
| **getBy\*** | Quando o elemento deve estar presente imediatamente. | `getByRole('button', { name: /adicionar ao carrinho/i })` |
| **queryBy\*** | Quando a presença do elemento é opcional. | `queryByText('Sem resultados')` |
| **findBy\*** | Quando o elemento aparece de forma assíncrona. | `await findByRole('alert')` |

### Escolhendo a query correta  

1. **Role** – sempre que houver um papel semântico (botão, heading, textbox).  
2. **Label text** – ideal para inputs ligados a `<label>` ou `aria-label`.  
3. **Placeholder** – útil quando o campo não tem rótulo visível, mas tem placeholder.  
4. **Text** – para conteúdos estáticos, como mensagens de erro ou títulos.  

Exemplo prático de um componente de busca:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import SearchBar from './SearchBar';

test('exibe resultados ao digitar e pressionar Enter', () => {
  render(<SearchBar onSearch={jest.fn()} />);
  const input = screen.getByLabelText(/buscar produto/i);
  fireEvent.change(input, { target: { value: 'camisa' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

  expect(screen.getByText(/resultados para "camisa"/i)).toBeInTheDocument();
});
```

A query `getByLabelText` garante que o teste falhe se o campo perder o rótulo, reforçando a acessibilidade.

## User events: simulando interações reais  

A API `fireEvent` funciona, mas reproduz eventos de forma muito baixa‑nível. A **user-event** library, mantida pelos próprios mantenedores da Testing Library, simula cliques, digitação e arrastos da mesma forma que o navegador faz. No meu workflow de CI, troco `fireEvent.click` por `userEvent.click` sempre que possível.

```tsx
import userEvent from '@testing-library/user-event';

test('abre o modal de detalhes ao clicar no card', async () => {
  render(<ProductCard product={mockProduct} />);
  await userEvent.click(screen.getByRole('button', { name: /detalhes/i }));
  expect(screen.getByRole('dialog')).toBeVisible();
});
```

Observe que `userEvent.click` retorna uma *Promise* quando há efeitos assíncronos, por isso o `await` garante que o modal esteja realmente aberto antes da asserção.

## Async testing: lidando com chamadas de API  

Aplicações React modernas dependem de dados carregados de forma assíncrona. A Testing Library recomenda duas estratégias:

1. **`findBy*`** – espera até que o elemento apareça, com timeout padrão de 1000 ms.  
2. **`waitFor`** – executa uma função de verificação repetidamente até que não lance erro.

No **lead‑pipeline**, que consome um endpoint de enriquecimento de leads, usei `findByRole` para validar o spinner de carregamento e o resultado final:

```tsx
test('exibe lead enriquecido após chamada de API', async () => {
  server.use(
    rest.get('/api/leads/:id', (req, res, ctx) =>
      res(ctx.json({ name: 'Ana', score: 87 }))
    )
  );

  render(<LeadDetail id="123" />);
  expect(screen.getByText(/carregando/i)).toBeInTheDocument();

  const name = await screen.findByText('Ana');
  expect(name).toBeInTheDocument();
  expect(screen.getByText(/score: 87/i)).toBeInTheDocument();
});
```

A chamada ao endpoint é interceptada por **MSW** (Mock Service Worker), que permite testar o fluxo completo sem tocar em serviços externos.

## Mocking API: quando o mock é necessário  

Embora a Testing Library prefira testes que usem a pilha real, alguns cenários exigem mocks: serviços de pagamento, integração com OSPOS ou APIs de terceiros que não podem ser invocadas em CI. Eu costumo combinar **MSW** com `setupServer` para registrar handlers globais e limpar entre testes:

```tsx
// test/setupTests.ts
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

export const server = setupServer(...handlers);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Com essa configuração, cada teste pode sobrescrever o comportamento de um endpoint específico sem interferir nos demais, mantendo a independência dos casos de teste.

## Coverage: qualidade além da quantidade  

Ter 100 % de cobertura de linhas não significa que seu código está livre de bugs. A Testing Library encoraja a **cobertura de fluxos de usuário**, que pode ser medida com ferramentas como **c8** ou **nyc**. No meu projeto **Plexo**, configurei o `jest` para gerar um relatório de cobertura e, em seguida, revisitei os arquivos que ainda não tinham testes de interação. O resultado foi um aumento de 35 % na cobertura de caminhos críticos, embora a cobertura total fosse apenas 78 %. Essa abordagem foca no que realmente importa: o caminho que o usuário percorre.

Algumas práticas que ajudam a melhorar a cobertura relevante:

- **Teste de estado visível** – verifique se um botão habilita/desabilita conforme a entrada do usuário.  
- **Teste de mensagens de erro** – simule respostas de API com erro e confirme que a UI exibe o alerta correto.  
- **Teste de navegação** – use `MemoryRouter` para garantir que a rota correta é renderizada após uma ação.  

## Conclusão  

A Testing Library mudou minha forma de pensar sobre testes em React. Em vez de “o código funciona”, passei a perguntar “o usuário consegue fazer o que ele espera?”. Essa mudança de perspectiva traz benefícios concretos: menos manutenção, interfaces mais acessíveis e maior confiança ao entregar novas funcionalidades.  

Se você ainda utiliza seletores frágeis ou `setTimeout`s para esperar por elementos, vale a pena investir tempo para refatorar os testes seguindo os princípios aqui apresentados. A curva de aprendizado é curta, especialmente se você já está familiarizado com o ecossistema React, e o ganho em produtividade compensa rapidamente o esforço inicial.

## Takeaways práticos  

- Use queries semânticas (`getByRole`, `getByLabelText`) para garantir acessibilidade e resistência a mudanças de implementação.  
- Substitua `fireEvent` por `userEvent` para simular interações reais e evitar falsos positivos.  
- Prefira `findBy*` ou `waitFor` ao lidar com conteúdo carregado assincronamente.  
- Integre **MSW** nos testes de integração para mockar APIs externas sem poluir o código de produção.  
- Foque a cobertura em fluxos de usuário, não apenas em linhas de código.  
- Reaplique o mesmo padrão nos projetos existentes (ex.: **inventory‑service**, **Plexo**) para ganhar consistência e reduzir dívidas técnicas.

## Fontes  

- [Testing Library Docs – React Testing Library](https://testing-library.com/docs/react-testing-library/intro)  
- [User Event – Simulando interações de usuário](https://testing-library.com/docs/user-event/intro)  
- [MSW – Mock Service Worker](https://mswjs.io/)  
- [Jest – Cobertura de código](https://jestjs.io/docs/configuration#collectcoverage-boolean)  
- [React Docs – Acessibilidade com JSX](https://react.dev/reference/react-dom/components/common)  