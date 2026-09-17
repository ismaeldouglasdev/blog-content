---
title: "Testing Library: React Tests That Reflect Real Usage"
date: "2026-09-17"
category: "tutorial"
tags: ["testing-library", "react", "testes"]
excerpt: "When I started testing React interfaces, I was doing everything wrong—I wrote tests checking how the component was built, like whether that button has the .btn-primary class"
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-09-17-testing-library-testes-de-react-que-refletem-o-uso-real.jpg"
lang: "en"
translation_of: "2026-09-17-testing-library-testes-de-react-que-refletem-o-uso-real"
---

When I started testing React interfaces, I was doing everything wrong. I wrote tests that checked how the component was built—"if that button has the `.btn-primary` class and fires the `onClick` event." It worked in tests but silently broke in production when someone changed the internal implementation. This continued until I worked at OSPOS in the store where I managed the POS: I discovered that the real issue wasn't broken code—it was code that appeared to work in tests but didn't work in the actual workflows of the sellers.

The problem wasn't the logic—it was the perspective. My tests validated the developer's perspective, not the user's. That's when I discovered React Testing Library—a library that (gracefully) forces you to test how users actually interact with your application.

## The principle: test what the user sees

The central idea of React Testing Library is simple: your tests should be written as if they're a guide for someone using your interface without seeing the code. It doesn't matter whether you use `useState`, `useReducer`, or whether the component is functional or class-based. What matters is: can the user see this? Can they click it? Do they get clear feedback when they do something?

This changes everything. Instead of asserting "the button has the attribute `aria-label='Save'`", your test says "the button with the text 'Save' exists and responds to clicks". Not because you're following an arbitrary rule, but because this is exactly how a salesperson at the Almost Everything Store interacts with the POS: they see a labeled button, click it, and expect a tangible result.

In the `inventory-service` project—which synchronizes catalog and inventory between OSPOS and Mercado Livre—this made a real difference. Instead of testing whether the component correctly called the API, we tested whether, after filling out the form and clicking "Synchronize", the user saw a clear success or error message. The code changed several times, but the visible behavior—the thing the user sees and interacts with—remained the same.

## Queries: finding elements the way a user would

Testing Library queries are categorized by priority. This isn’t arbitrary: it’s a reminder that you should find elements in the way that most closely mirrors what a user would do.

The priority order (from most to least recommended) is:

- `getBy`: for elements that you expect to always exist. If it fails, it’s a real error.
- `queryBy`: for elements that may or may not exist (e.g., error messages). Doesn’t throw an exception if not found.
- `findBy`: for elements that appear asynchronously. Returns a promise.

In day-to-day testing, use `getBy` and `findBy` most of the time. `queryBy` is for specific scenarios, such as validating that an error field doesn’t appear initially.

Here’s a practical example, from the `Plexo` project (a React/Vite task management UI):

```javascript
import { render, screen, waitFor } from '@testing-library/react'
import TaskForm from '../TaskForm'

test('displays error when title is empty', async () => {
  render(<TaskForm onSubmit={vi.fn()} />)
  
  // Gets the "Create Task" button
  const createButton = screen.getByRole('button', { name: /criar task/i })
  
  // Clicks without filling in the title
  await userEvent.click(createButton)
  
  // Verifies the error appeared
  const errorMessage = screen.getByText(/título é obrigatório/i)
  expect(errorMessage).toBeInTheDocument()
})
```

Notice that I’m not searching for the button’s `id` or the CSS selector `.task-form button[type="submit"]`. I’m searching for the visible, accessible text that a user would read. This ensures that even if I change the HTML structure or CSS classes, the test still validates the actual intent: the button creates a task.

A common confusion is using `getByLabelText` for fields that don’t have a visible label. If a field has only a placeholder (e.g., `<input placeholder="Título" />`), use `getByPlaceholderText`, not `getByLabelText`. The visible label or `aria-label` is what the user associates with the field. A placeholder is a guide, not a label.

Another common mistake is using `fireEvent.click(button)`. It works, but it ignores important browser behaviors: focus, keyboard events, accessibility.

The Testing Library provides `@testing-library/user-event`, which simulates real user interactions. A click with `userEvent.click` triggers all associated events (`mouseenter`, `focus`, `mousedown`, `mouseup`, `click`), as a user would expect.

Example: in the `Cronograma de Estudos` system, with gamification and visual feedback, it was necessary to ensure that navigation buttons between modules worked correctly. Testing with `fireEvent.click` didn't validate whether focus was moved to the next element (for screen reader users). With `userEvent`, it does.

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

This is crucial in projects with accessibility in mind (such as the `Mensageiros da Esperança` NGO system, with 100+ volunteers). If focus doesn't behave as expected, visually impaired users encounter real barriers.

Async testing: when the world doesn't stop

Modern interfaces are full of asynchronicity: API loading, animations, event reactions. Testing Library provides tools to handle this without dirty tricks.

- `await screen.findByText('Success')`: waits until the text appears.
- `waitFor(() => expect(...))`: repeatedly executes an assertion until it passes or times out.

Real example: in `inventory-service`, when synchronizing products, the button changes to "Syncing..." with a loading state.

```javascript
test('shows loading during synchronization and updates after success', async () => {
  const user = userEvent.setup()
  render(<SyncButton />)

  const syncButton = screen.getByRole('button', { name: /sync/i })
  
  // Click and wait for loading to appear
  await user.click(syncButton)
  const loadingButton = await screen.findByRole('button', { name: /syncing\.\.\./i })
  expect(loadingButton).toBeDisabled()

  // Now wait for the button to return to its initial state with success
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /sync/i })).toBeInTheDocument()
  })
})
```

Note that I'm not using `setTimeout` or `wait(1000)`. `findBy` and `waitFor` react to what actually happens in the DOM, not fixed time intervals. This makes tests fast and reliable.

## Mocking API: control without real dependencies

Testing components that consume APIs is delicate. You don’t want to depend on a real server, nor risk flaky tests due to network failures.

In the local AI ecosystem I built (like `provider-health-daemon`), I use `msw` (Mock Service Worker). It intercepts requests at the network layer, simulating responses without needing a server.

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

In the component, just render it:

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

The advantage of `msw` is that it intercepts both real and mocked requests. Whether you use `fetch` or `axios`, the mock works the same. You don’t need to change the component logic just to test it.

If you prefer not to add `msw`, simple mocking with `vi.mock` also works:

```javascript
vi.mock('../api/models', () => ({
  fetchModels: vi.fn(() => Promise.resolve([
    { id: 'llama-2', name: 'Llama 2' }
  ]))
}))
```

But then you’re testing the implementation (whether `fetchModels` was called), not the visible behavior. Prefer `msw` whenever possible.

## Coverage: useful metric, but be careful

Has anyone ever told you your tests need 90% coverage? Stop listening to that.

Coverage measures lines of code executed by tests. It doesn't measure whether you tested the right behavior. It's easy to reach 100% coverage by only testing a component's `render` function. That doesn't guarantee anything about the user experience.

However, low coverage can indicate gaps. A good use is to filter by critical components (e.g., checkout forms, payment flows) and check whether they have tests. The exact number doesn't matter.

In `lead-pipeline`, the system that handles leads with AI, import and enrichment flows have tests, but coverage is secondary. What matters is that each step of the process (CSV upload → parse → enrich → save) has clear validation, with accessible messages for the user.

## Conclusion: Write tests that last

Testing with React Testing Library isn't extra work—it's a way to document your UI's behavior so other developers (or you six months from now) know exactly how the code should behave.

The difference between a weak test and a strong one:

- Weak: "The button should trigger `handleClick`"
- Strong: "When clicking the 'Save' button, the user sees a confirmation message"

The second test won't break if you refactor the component to use `useReducer` instead of `useState`. What matters is the behavior perceivable by the user—not the internal mechanics.

This mindset didn't come from years of experience at big companies. It came from seeing a salesperson at a store waste time because a button looked clickable but did nothing (the `.pointer-events-none` class was hidden in complex CSS). The previous tests passed—but the user saw nothing working.

I learned that good code is code that behaves as expected—period. Everything else is just implementation detail.

Here are some practical examples I follow:

- Always start with queries based on accessible text or roles (`getByRole`, `getByText`)
- Use `userEvent` for all interactions involving clicks, typing, or navigation
- Prefer `findBy` and `waitFor` for async operations, not `wait` or `setTimeout`
- Mock APIs with `msw` if you want full fidelity with browser behavior
- Forget about coverage percentages. Focus on covering real user flows

If a test needs adjustment when you rename a button or change an ID, it's testing implementation—not behavior. Refactor until it only fails when the user sees something broken.

In the end, testing this way isn't harder—it's just different. But it's the right way to ensure your code doesn't break when the real world uses it.

## Sources

- [React Testing Library: Getting Started](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Library: Principal Concepts](https://testing-library.com/docs/guiding-principles/)
- [Kent C. Dodds: How to know if a test is good](https://kentcdodds.com/blog/how-to-know-if-a-test-is-good)
- [MSW: Mock Service Worker](https://mswjs.io/)
- [React Docs: Testing](https://react.dev/learn/testing)
- [User Event: Official Documentation](https://testing-library.com/docs/user-event/intro)
## 📸 Cover image credit
- **Image:** [Dragon 2 hover test (24159153709).jpg](https://commons.wikimedia.org/wiki/File%3ADragon_2_hover_test_%2824159153709%29.jpg)
- **Author:** SpaceX Photos
- **License:** [CC0](https://creativecommons.org/publicdomain/zero/1.0/) · via Wikimedia Commons
