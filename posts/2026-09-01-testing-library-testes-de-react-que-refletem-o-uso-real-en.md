---
title: "Testing Library: React tests that reflect real‑world usage"
date: "2026-09-01"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "Have you ever seen a green test in CI, only to open the application and find that the button that should be enabled is still disabled? That disconnect between what the test"
lang: "en"
translation_of: "2026-09-01-testing-library-testes-de-react-que-refletem-o-uso-real"
---

## Introduction  

Have you ever seen a green test in CI, only to open the application and find that the button that should be enabled is still disabled? That disconnect between what the test verifies and what the user actually sees is the root of bugs that waste time and money. When I started migrating the catalog of **Loja Quase Tudo** to OSPOS, I noticed that most UI tests were based on implementation details—class selectors, internal function calls—instead of the flow the customer experiences. That’s when I discovered **Testing Library**, and since then it’s become the standard tool in my React projects, such as **inventory‑service** and **Plexo**.  

In this post, I’ll show how to use Testing Library to write tests that truly reflect real usage, avoid common pitfalls, and ensure that user behavior is the primary acceptance criterion.

## Principle: test what the user sees  

The philosophy of Testing Library can be summed up in one sentence: *test the application the same way the user uses it*. Instead of looking for `data-test-id` or internal functions, we look for text, labels, roles, and accessible names. This approach has three clear benefits:

1. **Easier maintenance** – when an implementation detail changes, the test stays valid because the user flow hasn’t changed.  
2. **Guaranteed accessibility** – by using queries based on ARIA attributes, the test forces the team to produce accessible markup.  
3. **Confidence in delivery** – if the test passes, the user sees exactly what the test describes.

In my **inventory‑service** project, which syncs OSPOS with Mercado Livre, I wrote the first test for a product‑creation form using only the label of the “Product Name” field. When the team decided to change the input’s `id`, the test remained green because the user still interacts via the same label.

## Queries: how to find elements on the screen  

Testing Library offers three groups of queries:

| Group | When to use | Example |
|-------|-------------|---------|
| **getBy\*** | When the element must be present immediately. | `getByRole('button', { name: /adicionar ao carrinho/i })` |
| **queryBy\*** | When the element’s presence is optional. | `queryByText('Sem resultados')` |
| **findBy\*** | When the element appears asynchronously. | `await findByRole('alert')` |

### Choosing the right query  

1. **Role** – whenever there is a semantic role (button, heading, textbox).  
2. **Label text** – ideal for inputs associated with a `<label>` or `aria-label`.  
3. **Placeholder** – useful when the field has no visible label but does have a placeholder.  
4. **Text** – for static content such as error messages or headings.  

Practical example of a search component:

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

The `getByLabelText` query ensures the test fails if the field loses its label, reinforcing accessibility.

## User events: simulating real interactions  

The `fireEvent` API works, but it fires events at a very low level. The **user-event** library, maintained by the Testing Library maintainers themselves, simulates clicks, typing, and dragging in the same way the browser does. In my CI workflow, I replace `fireEvent.click` with `userEvent.click` whenever possible.

```tsx
import userEvent from '@testing-library/user-event';

test('opens the details modal when the card is clicked', async () => {
  render(<ProductCard product={mockProduct} />);
  await userEvent.click(screen.getByRole('button', { name: /detalhes/i }));
  expect(screen.getByRole('dialog')).toBeVisible();
});
```

Note that `userEvent.click` returns a *Promise* when there are asynchronous effects, so the `await` ensures that the modal is actually open before the assertion.

## Async testing: handling API calls  

Modern React applications depend on data loaded asynchronously. The Testing Library recommends two strategies:

1. **`findBy*`** – waits until the element appears, with a default timeout of 1000 ms.  
2. **`waitFor`** – repeatedly runs a verification function until it does not throw an error.

In the **lead‑pipeline**, which consumes a lead‑enrichment endpoint, I used `findByRole` to validate the loading spinner and the final result:

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

The endpoint call is intercepted by **MSW** (Mock Service Worker), which allows testing the full flow without touching external services.

## Mocking API: when mocking is necessary  

Although Testing Library prefers tests that use the real stack, some scenarios require mocks: payment services, integration with OSPOS, or third‑party APIs that can’t be invoked in CI. I usually combine **MSW** with `setupServer` to register global handlers and clean up between tests:

```tsx
// test/setupTests.ts
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

export const server = setupServer(...handlers);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

With this setup, each test can override the behavior of a specific endpoint without affecting the others, preserving test case independence.

## Coverage: quality beyond the quantity  

Having 100 % line coverage doesn’t mean your code is free of bugs. Testing Library encourages **user‑flow coverage**, which can be measured with tools like **c8** or **nyc**. In my **Plexo** project, I configured `jest` to generate a coverage report and then revisited the files that still didn’t have interaction tests. The result was a 35 % increase in critical‑path coverage, even though total coverage was only 78 %. This approach focuses on what really matters: the path the user takes.

Some practices that help improve relevant coverage:

- **Visible state testing** – verify that a button enables/disables according to user input.  
- **Error‑message testing** – mock API responses with errors and confirm that the UI displays the correct alert.  
- **Navigation testing** – use `MemoryRouter` to ensure the correct route

## Conclusion  

Testing Library changed my way of thinking about testing in React. Instead of “the code works,” I started asking “can the user do what they expect?” This shift in perspective brings concrete benefits: less maintenance, more accessible interfaces, and greater confidence when delivering new features.  

If you still use fragile selectors or `setTimeout`s to wait for elements, it’s worth investing time to refactor your tests following the principles presented here. The learning curve is short, especially if you’re already familiar with the React ecosystem, and the productivity gain quickly outweighs the initial effort.

## Practical Takeaways  

- Use semantic queries (`getByRole`, `getByLabelText`) to ensure accessibility and resilience to implementation changes.  
- Replace `fireEvent` with `userEvent` to simulate real interactions and avoid false positives.  
- Prefer `findBy*` or `waitFor` when dealing with asynchronously loaded content.  
- Integrate **MSW** in integration tests to mock external APIs without polluting production code.  
- Focus coverage on user flows, not just lines of code.  
- Reapply the same pattern in existing projects (e.g., **inventory‑service**, **Plexo**) to gain consistency and reduce technical debt.

## Sources  

- [Testing Library Docs – React Testing Library](https://testing-library.com/docs/react-testing-library/intro)  
- [User Event – Simulating user interactions](https://testing-library.com/docs/user-event/intro)  
- [MSW – Mock Service Worker](https://mswjs.io/)  
- [Jest – Code coverage](https://jestjs.io/docs/configuration#collectcoverage-boolean)  
- [React Docs – Accessibility with JSX](https://react.dev/reference/react-dom/components/common)