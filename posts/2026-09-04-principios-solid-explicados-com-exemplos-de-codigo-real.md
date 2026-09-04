---
title: "Principios SOLID explicados com exemplos de codigo real"
date: "2026-09-04"
category: "article"
tags: ["solid", "arquitetura", "boas-praticas"]
excerpt: "Imagine que um cliente da sua loja de varejo, que usa OSPOS como ponto de venda, solicita uma integração que sincroniza estoque com o Mercado Livre em tempo real. Você"
lang: "pt"
---

## Introdução

Imagine que um cliente da sua loja de varejo, que usa OSPOS como ponto de venda, solicita uma integração que sincroniza estoque com o Mercado Livre em tempo real. Você entrega o código em um fim de semana, mas, dois meses depois, o mesmo cliente pede para acrescentar um relatório de vendas por categoria. O que era um módulo simples agora está cheio de condições, métodos que fazem tudo e pouca margem para mudanças. Essa situação acontece com frequência quando as regras de design são deixadas de lado.

aqui eu explico como os cinco princípios SOLID podem impedir que um código evolua para um monólito incontrolável. Cada princípio vem acompanhado de um exemplo prático escrito em linguagens que eu uso no dia a dia – TypeScript para o front‑end e Python para serviços back‑end. Ao final, mostro como aplicar todos eles em conjunto num caso real que surgiu ao migrar mais de 10 k produtos da loja Quase Tudo para um serviço omnichannel.

---

## Single Responsibility Principle (SRP)

**Regra básica:** uma classe ou módulo deve ter apenas um motivo para mudar.

### Por que isso importa

Quando uma única classe cuida de leitura de arquivos, validação de dados e envio de e‑mail, qualquer alteração em um desses domínios gera risco de regressão nos outros. No meu projeto *inventory‑service*, a primeira versão da sincronização misturava a lógica de API externa, a transformação de dados e a persistência no banco. Quando precisei mudar o formato de payload para o Mercado Livre, o código que envia e‑mails quebrou por causa de um campo inesperado.

### Exemplo em TypeScript

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

A solução é dividir as responsabilidades:

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

// Orquestrador que usa os componentes acima
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

Agora cada classe tem um único motivo para mudar: se a API do OSPOS mudar, só o `OspOSFetcher` será alterado.

---

## Open/Closed Principle (OCP)

**Regra básica:** módulos devem estar abertos para extensão, mas fechados para modificação.

### Por que isso importa

No mesmo *inventory‑service* eu precisava acrescentar um novo canal de venda (Shopee). Cada vez que eu alterava o `SyncOrchestrator` para incluir o novo cliente, o risco de quebrar a integração com o Mercado Livre aumentava. Aplicar OCP significa que a estrutura existente permanece intacta e a nova funcionalidade chega como um módulo adicional.

### Exemplo em Python

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

A classe `SyncEngine` não conhece detalhes de nenhum canal. Quando surge um novo marketplace, basta implementar `ChannelAdapter` e registrar a instância na lista passada ao construtor.

---

## Liskov Substitution Principle (LSP)

**Regra básica:** objetos de uma subclasse devem poder substituir objetos da superclasse sem alterar o comportamento esperado.

### Por que isso importa

Durante o desenvolvimento do plugin Neovim para o projeto *Engram*, eu criei duas classes de log: `ConsoleLogger` e `FileLogger`. O `FileLogger` começou a lançar exceções quando o diretório não existia, quebrando partes do código que esperavam apenas registrar mensagens. A violação de LSP fez com que a substituição não fosse segura.

### Exemplo em TypeScript

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
    // falha se o caminho não existir
    const fs = require('fs');
    fs.appendFileSync(this.path, message + '\n');
  }
}
```

Para corrigir, garantimos que `FileLogger` nunca lance exceções inesperadas:

```ts
class FileLogger implements Logger {
  private fs = require('fs');
  constructor(private path: string) {
    // garante que o diretório exista
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

Agora qualquer código que espere um `Logger` pode receber `ConsoleLogger` ou `FileLogger` sem precisar de tratamento adicional.

---

## Interface Segregation Principle (ISP)

**Regra básica:** clientes não devem ser forçados a depender de interfaces que não utilizam.

### Por que isso importa

No projeto *provider-health-daemon* eu defini uma interface `HealthCheck` que incluía métodos de métricas, alertas e logging. Alguns provedores de IA não precisavam de métricas avançadas, mas ainda eram obrigados a implementar métodos vazios. Isso aumentou a complexidade e gerou código redundante.

### Exemplo em Python

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

Um provedor que só precisa de `ping` implementa `BasicHealthCheck`. Se precisar de métricas, implementa `MetricsHealthCheck`. Assim cada cliente recebe apenas o contrato que realmente usa.

---

## Dependency Inversion Principle (DIP)

**Regra básica:** módulos de alto nível não devem depender de módulos de baixo nível; ambos devem depender de abstrações.

### Por que isso importa

Ao criar o *lead‑pipeline* eu inicialmente conectei diretamente o script de enriquecimento de IA ao banco SQLite. Quando o cliente pediu migração para PostgreSQL, todo o código de negócio ficou preso ao driver SQLite. Aplicar DIP permite mudar a camada de persistência sem tocar na lógica de negócio.

### Exemplo em TypeScript

```ts
// abstração
export interface LeadRepository {
  save(lead: Lead): Promise<void>;
  findById(id: string): Promise<Lead | null>;
}

// implementação SQLite
export class SqliteLeadRepository implements LeadRepository {
  async save(lead) { /* ... */ }
  async findById(id) { /* ... */ }
}

// implementação PostgreSQL
export class PostgresLeadRepository implements LeadRepository {
  async save(lead) { /* ... */ }
  async findById(id) { /* ... */ }
}

// serviço de negócio que depende da abstração
export class LeadEnrichmentService {
  constructor(private repo: LeadRepository) {}

  async enrichAndSave(raw) {
    const enriched = await this.enrich(raw);
    await this.repo.save(enriched);
  }

  private async enrich(raw) { /* IA aqui */ }
}
```

Ao mudar o banco, basta instanciar `PostgresLeadRepository` e passar para o serviço; nenhuma linha de lógica de enriquecimento é modificada.

---

## Todos os princípios juntos em um caso real

### Contexto

Em 2020 assumi a liderança comercial da loja Quase Tudo. Entre 2020 e 2022 migrei cerca de 10 k produtos de um sistema legado para OSPOS, configurando integrações omnichannel que conectavam PDV com e‑commerce. Em 2024 comecei a programar seriamente, e em 2026 contribuí como Top Contributor no projeto open source Engram. Hoje estou consolidando tudo isso no *inventory‑service*, um MVP que sincroniza catálogo e estoque entre OSPOS, Mercado Livre e Shopee.

### Arquitetura final

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

* **SRP** – Cada classe tem uma única responsabilidade (fetch, normalize, persist, notificar, enviar a canais).
* **OCP** – `ChannelAdapters` são extensíveis; ao acrescentar TikTok Shop, criamos `TikTokAdapter` que implementa a mesma interface.
* **LSP** – Qualquer `ChannelAdapter` pode ser usado no `SyncEngine` sem quebrar a lógica de iteração.
* **ISP** – `ChannelAdapter` expõe apenas `push`; funcionalidades de métricas ou alertas são oferecidas por interfaces separadas.
* **DIP** – `SyncEngine` depende de abstrações (`Fetcher`, `Normalizer`, `Repository`, `Notifier`, `ChannelAdapter`). Implementações concretas são injetadas na camada de composição (arquivo `compose.ts`).

### Código de composição (TypeScript)

```ts
import { OspOSFetcher } from './fetcher';
import { ProductNormalizer } from './normalizer';
import { InventoryRepository } from './repository';
import { NotificationService } from './notification';
import { MercadoLivreAdapter, ShopeeAdapter } from './adapters';
import { SyncOrchestrator } from './orchestrator';

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

A estrutura permite que eu, como desenvolvedor freelancer, adicione novos canais ou troque a camada de persistência sem tocar na lógica de orquestração. Quando migrei o banco de dados da loja para PostgreSQL, bastou trocar a implementação de `InventoryRepository`. O código que eu escrevi para a migração de 10 k produtos serviu de base para esse reuso.

---

## Conclusão

Aplicar SOLID não é uma questão de seguir regras abstratas; é um caminho para manter a agilidade que eu preciso ao atender clientes de varejo que exigem mudanças rápidas. Quando a loja Quase Tudo pediu novas integrações, a separação de responsabilidades e a capacidade de estender o sistema sem refatorar tudo foram decisivas. O mesmo padrão se repetiu nos projetos open source (Engram) e nos meus produtos SaaS (lead‑pipeline, provider‑health‑daemon).

### Takeaways práticos

- Defina um ponto de entrada único para cada fluxo de dados; depois extraia funções auxiliares em classes menores.
- Crie interfaces que representem apenas o que o consumidor realmente usa; adicione extensões quando necessário.
- Teste substituição de subclasses usando mocks; se o teste falhar, provavelmente há violação de LSP.
- Injete dependências por meio de construtores ou contêineres DI; isso isola módulos de alto nível de detalhes de implementação.
- Revise o código sempre que uma nova funcionalidade for adicionada; pergunte se está violando algum princípio antes de escrever.

Seguindo esses passos, você reduz o risco de “código que funciona hoje, mas quebra amanhã” e ganha tempo para focar no que realmente importa: entregar valor ao cliente.

## Fontes

- [SOLID Principles – Robert C. Martin](https://web.archive.org/web/20210101000000/https://www.objectmentor.com/resources/articles/SOLID.pdf)
- [TypeScript Handbook – Interfaces](https://www.typescriptlang.org/docs/handbook/interfaces.html)
- [Python abc – Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- [OSPOS GitHub Repository](https://github.com/opensourcepos/opensourcepos)
- [Engram – GitHub Organization](https://github.com/engram-security)