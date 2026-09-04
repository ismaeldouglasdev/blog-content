---
title: "SOLID Principles Explained with Real Code Examples"
date: "2026-09-04"
category: "article"
tags: ["solid", "arquitetura", "boas-praticas"]
excerpt: "Picture a retail store customer using OSPOS who asks for real‑time inventory sync with Mercado Livre. You deliver."
lang: "en"
translation_of: "2026-09-04-principios-solid-explicados-com-exemplos-de-codigo-real"
---

## Introduction

Imagine a customer of your retail store, who uses OSPOS as a point of sale, requests an integration that synchronizes inventory with Mercado Livre in real time. You deliver the code over a weekend, but two months later the same customer asks to add a sales report by category. What was a simple module is now full of conditionals, methods that do everything, and little room for change. This situation occurs frequently when design rules are ignored.

Here I explain how the five SOLID principles can prevent code from evolving into an uncontrollable monolith. Each principle is accompanied by a practical example written in the languages I use daily—TypeScript for the front‑end and Python for back‑end services. In the end, I show how to apply all of them together in a real case that arose when migrating over 10 k products from the Quase Tudo store to an omnichannel service.

## Single Responsibility Principle (SRP)

**Basic rule:** a class or module should have only one reason to change.

### Why it matters

When a single class handles file reading, data validation, and email sending, any change in one of those domains introduces a risk of regression in the others. In my *inventory‑service* project, the first version of the synchronization mixed external API logic, data transformation, and database persistence. When I had to change the payload format for Mercado Libre, the email‑sending code broke because of an unexpected field.

### Example in TypeScript

```ts
// antes: responsabilidade única violada
export class SyncService {
  async run() {
    const products = await this.fetchFromOspOS();
    const normalized = this.normalize(products);
    await this.saveToDb(normalized);
    await this.notifyTeam(normalized);
  }

  private async fetchFromOspOS() { /* ... */ }
  private normalize(items: any[]) { /* ... */ }
  private async saveToDb(data: any[]) { /* ... */ }
  private async notifyTeam(data: any[]) { /* ... */ }
}
```

The solution is to split the responsibilities:

```ts
export class OspOSFetcher {
  async fetch() { /* ... */ }
}

export class ProductNormalizer {
  normalize(items: any[]) { /* ... */ }
}

export class InventoryRepository {
  async upsert(data: any[]) { /* ... */ }
}

export class NotificationService {
  async send(data: any[]) { /* ... */ }
}

// Orchestrator that uses the components above
export class SyncOrchestrator {
  constructor(
    private fetcher: OspOSFetcher,
    private normalizer: ProductNormalizer,
    private repo: InventoryRepository,
    private notifier: NotificationService,
  ) {}

  async run() {
    const raw = await this.fetcher.fetch();
    const norm = this.normalizer.normalize(raw);
    await this.repo.upsert(norm);
    await this.notifier.send(norm);
  }
}
```

Now each class has a single reason to change: if the OSPOS API changes, only the `OspOSFetcher` will be modified.

## Open/Closed Principle (OCP)

**Basic rule:** modules should be open for extension, but closed for modification.

### Why this matters

In the same *inventory‑service* I needed to add a new sales channel (Shopee). Every time I changed the `SyncOrchestrator` to include the new client, the risk of breaking the integration with Mercado Livre increased. Applying OCP means the existing structure stays intact and the new functionality arrives as an additional module.

### Example in Python

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class ChannelAdapter(ABC):
    @abstractmethod
    def push(self, items: List[Dict]) -> None:
        ...

class MercadoLivreAdapter(ChannelAdapter):
    def push(self, items):
        # lógica específica do Mercado Livre
        ...

class ShopeeAdapter(ChannelAdapter):
    def push(self, items):
        # lógica específica da Shopee
        ...

class SyncEngine:
    def __init__(self, adapters: List[ChannelAdapter]):
        self.adapters = adapters

    def sync(self, items):
        for adapter in self.adapters:
            adapter.push(items)
```

The `SyncEngine` class knows nothing about any specific channel. When a new marketplace appears, you simply implement `ChannelAdapter` and register the instance in the list passed to the constructor.

## Liskov Substitution Principle (LSP)

**Basic rule:** objects of a subclass must be able to replace objects of the superclass without changing the expected behavior.

### Why it matters

While developing the Neovim plugin for the *Engram* project, I created two logging classes: `ConsoleLogger` and `FileLogger`. The `FileLogger` started throwing exceptions when the directory didn't exist, breaking parts of the code that only expected to log messages. The LSP violation made the substitution unsafe.

### Example in TypeScript

```ts
interface Logger {
  log(message: string): void;
}

class ConsoleLogger implements Logger {
  log(message: string) {
    console.log(message);
  }
}

class FileLogger implements Logger {
  constructor(private path: string) {}

  log(message: string) {
    // fails if the path does not exist
    const fs = require('fs');
    fs.appendFileSync(this.path, message + '\n');
  }
}
```

To fix it, we ensure that `FileLogger` never throws unexpected exceptions:

```ts
class FileLogger implements Logger {
  private fs = require('fs');
  constructor(private path: string) {
    // ensure the directory exists
    const dir = require('path').dirname(this.path);
    if (!this.fs.existsSync(dir)) {
      this.fs.mkdirSync(dir, { recursive: true });
    }
  }

  log(message: string) {
    this.fs.appendFileSync(this.path, message + '\n');
  }
}
```

Now any code that expects a `Logger` can receive either `ConsoleLogger` or `FileLogger` without needing additional handling.

## Interface Segregation Principle (ISP)

**Basic rule:** clients should not be forced to depend on interfaces they do not use.

### Why it matters

In the *provider-health-daemon* project I defined a `HealthCheck` interface that included metrics, alerts, and logging methods. Some AI providers didn’t need advanced metrics, yet they were still required to implement empty methods. This added complexity and produced redundant code.

### Python example

```python
from abc import ABC, abstractmethod

class BasicHealthCheck(ABC):
    @abstractmethod
    def ping(self) -> bool:
        ...

class MetricsHealthCheck(BasicHealthCheck):
    @abstractmethod
    def get_latency(self) -> float:
        ...

class AlertHealthCheck(BasicHealthCheck):
    @abstractmethod
    def alert(self, msg: str) -> None:
        ...
```

A provider that only needs `ping` implements `BasicHealthCheck`. If it needs metrics, it implements `MetricsHealthCheck`. This way each client receives only the contract it actually uses.

## Dependency Inversion Principle (DIP)

**Basic rule:** high‑level modules should not depend on low‑level modules; both should depend on abstractions.

### Why it matters

When building the *lead‑pipeline* I initially wired the AI enrichment script directly to the SQLite database. When the client requested a migration to PostgreSQL, all the business code became tied to the SQLite driver. Applying DIP lets you change the persistence layer without touching the business logic.

### Example in TypeScript

```ts
// abstraction
export interface LeadRepository {
  save(lead: Lead): Promise<void>;
  findById(id: string): Promise<Lead | null>;
}

// SQLite implementation
export class SqliteLeadRepository implements LeadRepository {
  async save(lead) { /* ... */ }
  async findById(id) { /* ... */ }
}

// PostgreSQL implementation
export class PostgresLeadRepository implements LeadRepository {
  async save(lead) { /* ... */ }
  async findById(id) { /* ... */ }
}

// business service that depends on the abstraction
export class LeadEnrichmentService {
  constructor(private repo: LeadRepository) {}

  async enrichAndSave(raw) {
    const enriched = await this.enrich(raw);
    await this.repo.save(enriched);
  }

  private async enrich(raw) { /* IA aqui */ }
}
```

When you change the database, just instantiate `PostgresLeadRepository` and pass it to the service; no line of enrichment logic needs to be changed.

## All the principles together in a real case

### Context

In 2020 I took over the commercial leadership of the store Quase Tudo. Between 2020 and 2022 I migrated about 10 k products from a legacy system to OSPOS, setting up omnichannel integrations that connected POS with e‑commerce. In 2024 I started programming seriously, and in 2026 I contributed as a Top Contributor to the open‑source project Engram. Today I'm consolidating all of this into *inventory‑service*, an MVP that synchronizes catalog and stock between OSPOS, Mercado Livre, and Shopee.

### Final architecture

```
+-------------------+      +-------------------+      +-------------------+
| OspOSFetcher      | ---> | ProductNormalizer | ---> | InventoryRepo     |
+-------------------+      +-------------------+      +-------------------+
                                 |                         |
                                 v                         v
                          +-------------------+   +-------------------+
                          | NotificationSrv  |   | ChannelAdapters   |
                          +-------------------+   +-------------------+
```

* **SRP** – Each class has a single responsibility (fetch, normalize, persist, notify, send to channels).  
* **OCP** – `ChannelAdapters` are extensible; when adding TikTok Shop we create a `TikTokAdapter` that implements the same interface.  
* **LSP** – Any `ChannelAdapter` can be used in the `SyncEngine` without breaking the iteration logic.  
* **ISP** – `ChannelAdapter` exposes only `push`; metrics or alert functionalities are provided by separate interfaces.  
* **DIP** – `SyncEngine` depends on abstractions (`Fetcher`, `Normalizer`, `Repository`, `Notifier`, `ChannelAdapter`). Concrete implementations are injected in the composition layer (file `compose.ts`).

### Composition code (TypeScript)

```ts
import { OspOSFetcher } from './fetcher';
import { ProductNormalizer } from './normalizer';
import { InventoryRepository } from './repository';
import { NotificationService } from './notification';
import { MercadoLivreAdapter, ShopeeAdapter } from './adapters';
import { SyncOrchestrator } from './orchestrator';
```

```javascript
const fetcher = new OspOSFetcher();
const normalizer = new ProductNormalizer();
const repo = new InventoryRepository(); // usa PostgreSQL via DIP
const notifier = new NotificationService(); // envia Slack via Engram bot
const adapters = [
  new MercadoLivreAdapter(),
  new ShopeeAdapter(),
];

const orchestrator = new SyncOrchestrator(
  fetcher,
  normalizer,
  repo,
  notifier,
  adapters,
);

orchestrator.run()
  .then(() => console.log('Sincronização concluída'))
  .catch(err => console.error('Erro na sincronização', err));
```

The structure allows me, as a freelance developer, to add new channels or swap the persistence layer without touching the orchestration logic. When I migrated the store’s database to PostgreSQL, I only had to replace the implementation of `InventoryRepository`. The code I wrote for migrating 10 k products served as a foundation for this reuse.

## Conclusion

Applying SOLID is not about following abstract rules; it’s a way to keep the agility I need when serving retail clients who demand rapid changes. When the store **Quase Tudo** asked for new integrations, the separation of responsibilities and the ability to extend the system without refactoring everything were decisive. The same pattern repeated in the open‑source projects (**Engram**) and in my SaaS products (**lead‑pipeline**, **provider‑health‑daemon**).

### Practical takeaways

- Define a single entry point for each data flow; then extract helper functions into smaller classes.  
- Create interfaces that represent only what the consumer actually uses; add extensions when necessary.  
- Test subclass substitution using mocks; if the test fails, there’s probably an LSP violation.  
- Inject dependencies via constructors or DI containers; this isolates high‑level modules from implementation details.  
- Review the code whenever a new feature is added; ask whether you’re violating any principle before writing.

By following these steps, you reduce the risk of “code that works today but breaks tomorrow” and gain time to focus on what really matters: delivering value to the customer.

## Sources

- [SOLID Principles – Robert C. Martin](https://web.archive.org/web/20210101000000/https://www.objectmentor.com/resources/articles/SOLID.pdf)
- [TypeScript Handbook – Interfaces](https://www.typescriptlang.org/docs/handbook/interfaces.html)
- [Python abc – Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- [OSPOS GitHub Repository](https://github.com/opensourcepos/opensourcepos)
- [Engram – GitHub Organization](https://github.com/engram-security)