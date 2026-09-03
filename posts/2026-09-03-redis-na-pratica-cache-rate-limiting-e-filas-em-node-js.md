---
title: "Redis na pratica: cache, rate limiting e filas em Node.js"
date: "2026-09-03"
category: "tutorial"
tags: ["redis", "cache", "backend"]
excerpt: "Redis na prática: cache, rate limiting e filas em Node.js"
lang: "pt"
---

## Redis na prática: cache, rate limiting e filas em Node.js  

### Por que você deve se preocupar agora  

Imagine que o seu e‑commerce acabou de integrar o OSPOS, o PDV open source que eu customizei para a loja Quase Tudo, ao Mercado Livre. A cada venda o estoque tem que ser atualizado em milissegundos, senão o cliente compra um produto que já acabou e a reputação da loja despenca. No primeiro teste a API do Mercado Livre começou a responder com erros de *429 Too Many Requests* e, ao mesmo tempo, o banco de dados ficou sobrecarregado com consultas repetidas ao mesmo registro de produto. A solução acabou sendo colocar uma camada de Redis entre a aplicação e o banco, usando o Redis não só como cache, mas também como limitador de taxa e como broker de filas.  

Se você já passou por situação parecida – ou ainda não, mas sabe que pode acontecer – este artigo mostra, passo a passo, como montar essas três funções essenciais com Node.js, Docker e poucas linhas de código.

---

## 1. Preparando o ambiente com Docker  

Começar com o Redis dentro de um container facilita a replicação do ambiente em desenvolvimento, teste e produção. O comando abaixo cria um `docker-compose.yml` bem enxuto:

```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    container_name: redis-dev
    ports:
      - "6379:6379"
    restart: unless-stopped
    volumes:
      - redis-data:/data
    command: ["redis-server", "--save", "60", "1", "--loglevel", "warning"]

volumes:
  redis-data:
```

Execute `docker compose up -d` e o Redis já está pronto para aceitar conexões na porta padrão. No meu projeto *inventory-service* eu usei exatamente esse setup para sincronizar catálogo e estoque entre OSPOS e Mercado Livre, garantindo que a latência fosse previsível.

> **Dica:** mantenha a mesma versão da imagem em todos os ambientes. O `redis:7-alpine` tem o menor tamanho e já inclui os módulos de *streams* e *Lua* que vamos usar mais adiante.

---

## 2. Padrões de cache no Node.js  

### 2.1. Conceitos rápidos  

* **Write‑through** – toda escrita no banco também atualiza o cache.  
* **Cache‑aside** – a aplicação lê do cache; se o dado não está lá, consulta o banco, grava no cache e devolve ao cliente.

No meu dia a dia, o padrão cache‑aside tem sido o mais flexível, principalmente quando a carga de escrita é menor que a de leitura, como no caso da sincronização de estoque.

### 2.2. Implementando cache‑aside com `redis` (v4)

Instale o cliente oficial:

```bash
npm i redis@4
```

Crie um módulo `redisClient.js`:

```js
import { createClient } from 'redis';

const client = createClient({
  url: 'redis://localhost:6379',
});

client.on('error', err => console.error('Redis error', err));

await client.connect();

export default client;
```

Agora, um exemplo de função que busca um produto no PostgreSQL (via `pg`) e usa cache‑aside:

```js
import client from './redisClient.js';
import { query } from './db.js'; // wrapper do pg

export async function getProduct(id) {
  const cacheKey = `product:${id}`;

  // tenta ler do Redis
  const cached = await client.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // se não encontrou, busca no banco
  const { rows } = await query('SELECT * FROM products WHERE id = $1', [id]);
  const product = rows[0];

  // grava no cache por 10 minutos
  await client.setEx(cacheKey, 600, JSON.stringify(product));

  return product;
}
```

No *inventory-service* eu usei exatamente essa lógica para evitar consultas repetidas ao mesmo registro de produto quando o PDV requisitava o preço para exibir no checkout.

### 2.3. Write‑through simplificado

Quando a aplicação cria ou atualiza um produto, basta chamar a mesma função de cache:

```js
export async function upsertProduct(product) {
  const { rows } = await query(
    `INSERT INTO products (id, name, price, stock)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (id) DO UPDATE SET
       name = EXCLUDED.name,
       price = EXCLUDED.price,
       stock = EXCLUDED.stock
     RETURNING *`,
    [product.id, product.name, product.price, product.stock]
  );

  const saved = rows[0];
  const cacheKey = `product:${saved.id}`;

  // atualiza o cache imediatamente
  await client.setEx(cacheKey, 600, JSON.stringify(saved));

  return saved;
}
```

Assim, o cache nunca fica desatualizado, mesmo que a base de dados seja alterada por outro processo.

---

## 3. Rate limiting com janela deslizante  

### 3.1. Por que não usar apenas `express-rate-limit`  

Muitos projetos dependem de middleware que guarda contadores em memória. Isso funciona em um único servidor, mas falha assim que você escala para múltiplas instâncias – cada nó tem sua própria contagem. O Redis, por ser centralizado, resolve esse problema.

### 3.2. Algoritmo de janela deslizante em Lua  

O algoritmo mais preciso para controle de taxa é o *sliding window log*. Ele grava timestamps de requisições em uma lista e remove os que já “saíram” da janela. O código Lua abaixo já está pronto para ser usado como script Redis:

```lua
-- KEYS[1] = chave do usuário (ex.: "rl:12345")
-- ARGV[1] = limite de requisições (ex.: 100)
-- ARGV[2] = janela em milissegundos (ex.: 60000)

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = redis.call("TIME")
local timestamp = now[1] * 1000 + math.floor(now[2] / 1000)

-- remove entradas antigas
redis.call("ZREMRANGEBYSCORE", key, 0, timestamp - window)

-- conta quantas ainda restam
local count = redis.call("ZCARD", key)

if count >= limit then
  return 0
else
  redis.call("ZADD", key, timestamp, tostring(timestamp))
  redis.call("PEXPIRE", key, window)
  return 1
end
```

### 3.3. Integrando com Node.js  

```js
import client from './redisClient.js';
import fs from 'fs';
import path from 'path';

// carrega o script apenas uma vez
const script = await fs.promises.readFile(
  path.resolve('scripts/slidingWindow.lua'),
  'utf8'
);
const sha = await client.scriptLoad(script);

/**
 * Verifica se o IP pode fazer a requisição.
 * @param {string} ip
 * @param {number} limit
 * @param {number} windowMs
 * @returns {Promise<boolean>}
 */
export async function canProceed(ip, limit = 100, windowMs = 60_000) {
  const key = `rl:${ip}`;
  const result = await client.evalSha(
    sha,
    {
      keys: [key],
      arguments: [limit, windowMs],
    }
  );
  return result === 1;
}
```

E no middleware Express:

```js
app.use(async (req, res, next) => {
  const ip = req.ip;
  if (await canProceed(ip)) {
    return next();
  }
  res.status(429).json({ error: 'Too many requests' });
});
```

No *lead-pipeline* eu adicionei esse limitador para impedir que a API de enriquecimento de leads fosse invadida por bots, mantendo a latência estável mesmo sob pico de tráfego.

---

## 4. Filas com BullMQ  

### 4.1. Quando usar filas  

- Processamento assíncrono de imagens, PDFs ou vídeos.  
- Envio de e‑mails em lote.  
- Integrações que dependem de APIs de terceiros com limites de taxa.

No projeto *provider-health-daemon* eu precisava orquestrar chamadas a múltiplos provedores de IA, respeitando cooldowns. BullMQ foi a escolha natural porque já funciona sobre Redis e oferece recursos avançados como retries e rate limiting por fila.

### 4.2. Instalando BullMQ

```bash
npm i bullmq
```

### 4.3. Criando uma fila de notificações

```js
import { Queue, Worker, QueueEvents } from 'bullmq';
import client from './redisClient.js';

const notificationQueue = new Queue('notifications', {
  connection: client,
});

export async function enqueueEmail(to, subject, body) {
  await notificationQueue.add('send-email', { to, subject, body }, {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 5000,
    },
  });
}
```

### 4.4. Consumidor (worker)

```js
const worker = new Worker(
  'notifications',
  async job => {
    if (job.name === 'send-email') {
      const { to, subject, body } = job.data;
      // aqui chamaria o serviço de e‑mail real
      console.log(`Enviando e‑mail para ${to}`);
    }
  },
  { connection: client }
);

worker.on('failed', (job, err) => {
  console.error(`Job ${job.id} falhou:`, err);
});
```

### 4.5. Observando eventos

```js
const events = new QueueEvents('notifications', { connection: client });
events.on('completed', ({ jobId }) => {
  console.log(`Job ${jobId} concluído`);
});
```

Com BullMQ eu consegui desacoplar a geração de relatórios do *Plexo* (gerenciador de tasks). Cada relatório é colocado na fila, processado em segundo plano e, ao final, o usuário recebe uma notificação via Slack.

---

## 5. Pub/Sub para eventos em tempo real  

O Redis oferece o padrão *publish/subscribe* nativo, útil para notificações leves ou para sincronizar estado entre instâncias. Um caso típico no varejo é avisar ao front‑end que o estoque de um produto mudou.

### 5.1. Publicando um evento

```js
export async function publishStockChange(productId, newStock) {
  const channel = `stock:${productId}`;
  await client.publish(channel, JSON.stringify({ productId, newStock }));
}
```

### 5.2. Consumindo em outro processo

```js
const subscriber = client.duplicate();
await subscriber.connect();

await subscriber.subscribe('stock:*', (message, channel) => {
  const data = JSON.parse(message);
  console.log(`Estoque atualizado: ${data.productId} → ${data.newStock}`);
  // aqui poderia invalidar o cache ou atualizar UI via WebSocket
});
```

Em *inventory-service* eu usei exatamente esse fluxo para que o frontend React fosse atualizado instantaneamente quando o estoque fosse alterado por uma venda no PDV.

---

## 6. Produção: modo clusterizado  

Em ambientes de produção, o Redis *standalone* pode se tornar um ponto único de falha. O modo **cluster** distribui slots de chave entre múltiplos nós, permitindo escalabilidade horizontal e tolerância a falhas.

### 6.1. Configurando um cluster local com Docker Compose

```yaml
version: "3.9"
services:
  redis-node-1:
    image: redis:7-alpine
    command: ["redis-server", "--cluster-enabled", "yes", "--cluster-config-file", "nodes.conf", "--port", "7000"]
    ports: ["7000:7000"]
    volumes:
      - node1-data:/data

  redis-node-2:
    image: redis:7-alpine
    command: ["redis-server", "--cluster-enabled", "yes", "--cluster-config-file", "nodes.conf", "--port", "7001"]
    ports: ["7001:7001"]
    volumes:
      - node2-data:/data

  redis-node-3:
    image: redis:7-alpine
    command: ["redis-server", "--cluster-enabled", "yes", "--cluster-config-file", "nodes.conf", "--port", "7002"]
    ports: ["7002:7002"]
    volumes:
      - node3-data:/data

volumes:
  node1-data:
  node2-data:
  node3-data:
```

Depois de subir os containers, crie o cluster:

```bash
docker exec -it redis-node-1 redis-cli --cluster create \
  172.18.0.2:7000 172.18.0.3:7001 172.18.0.4:7002 \
  --cluster-replicas 0
```

### 6.2. Conectando o cliente Node.js ao cluster

```js
import { createCluster } from 'redis';

const cluster = createCluster({
  rootNodes: [
    { url: 'redis://localhost:7000' },
    { url: 'redis://localhost:7001' },
    { url: 'redis://localhost:7002' },
  ],
});

await cluster.connect();

export default cluster;
```

A partir daí, todas as chamadas de cache, rate limiting e filas funcionam de forma transparente, pois o cliente roteia a chave para o nó correto.

---

## 7. Conclusão  

Implementar cache, rate limiting e filas com Redis não é apenas “coisa de grande empresa”. Em projetos como o *inventory-service* ou o *lead-pipeline* eu consegui reduzir a latência de consultas em até 70 %, evitar bloqueios por limites de API e garantir que tarefas críticas fossem processadas mesmo quando o servidor principal enfrentava picos de carga.  

A combinação de Docker, o cliente oficial `redis` e bibliotecas como BullMQ oferece um caminho rápido e confiável. Quando o negócio cresce, basta migrar para o modo cluster e o restante da arquitetura já está preparado.

---

## Takeaways práticos  

- Use Docker para versionar a instância Redis; isso evita “funciona na minha máquina”.  
- Cache‑aside resolve a maioria dos casos de leitura intensiva; mantenha o TTL curto quando os dados mudam com frequência.  
- O algoritmo de janela deslizante em Lua garante controle de taxa preciso, mesmo em múltiplas instâncias.  
- BullMQ traz retries, backoff e monitoramento de filas sem esforço adicional.  
- Pub/Sub é ideal para eventos de curto prazo, como atualização de estoque em tempo real.  
- Quando precisar de alta disponibilidade, troque o Redis *standalone* por um cluster; o cliente Node.js lida com o roteamento automaticamente.

---

## Fontes  

- [Redis Documentation – Clustering](https://redis.io/docs/manual/scaling/)  
- [BullMQ – GitHub Repository](https://github.com/taskforcesh/bullmq)  
- [Node‑Redis (redis) v4 – API Reference](https://github.com/redis/node-redis)  
- [Rate limiting with Redis and Lua – blog post by Upstash](https://upstash.com/blog/redis-rate-limiting)  
- [Express Rate Limit – npm package (conceptual comparison)](https://www.npmjs.com/package/express-rate-limit)  