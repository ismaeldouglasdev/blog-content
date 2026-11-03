---
title: "Revolut moves to self-hosted GLM: why more companies may follow"
date: "2026-11-03"
category: "tendencia"
tags: ["infraestrutura", "fintech", "open-source", "autonomia"]
excerpt: "Revolut Moves to Self-Hosted GLM: Why More Companies Could Follow This Path?"
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-11-03-revolut-muda-para-glm-auto-hospedado-por-que-mais-empresas.jpg"
lang: "en"
translation_of: "2026-11-03-revolut-muda-para-glm-auto-hospedado-por-que-mais-empresas"
---
# Revolut Moves to Self-Hosted GLM: Why More Companies Could Follow This Path?

When a European fintech valued at $33 billion decides to replace a third-party API with its own artificial intelligence infrastructure, the market takes notice. Revolut did exactly that: it ditched external generative language model services to run its own GLM in-house. This wasn't a trivial decision, and the reasons behind this choice reveal a trend that developers and system architects need to understand.

Revolut's move is not an isolated one. Goldman Sachs, Apple, and other large companies are exploring or have already implemented similar strategies. What's driving this migration? And more importantly: what does it mean for those building products today?

## What is GLM and why it matters

GLM stands for Generative Language Model, and it's the technical name behind systems like ChatGPT, Claude, and similar models. These models process natural language and generate text, code, summaries, translations, and much more. For companies offering customer service, document analysis, or virtual assistants, a GLM is critical infrastructure, as essential as a database or an authentication server.

The crucial point is that language models are not interchangeable commodities. A GLM trained on financial data responds differently, and more accurately, to questions about transactions and investments than a general-purpose model. When Revolut decided to control its own GLM, it was seeking exactly this specificity: a model that understands the vocabulary, workflows, and needs of its financial users.

Dependence on external providers creates vulnerabilities that aren't always immediately obvious. Costs that seem predictable become volatile when the provider adjusts prices. Usage limits restrict the ability to scale during demand spikes. And privacy policies, however robust, always leave a margin of doubt when customer data is passing through third-party servers.

## The Four Forces Pushing Companies Toward Self-Hosting

The decision to run a GLM in-house is rarely ideological. It's almost always a sum of practical factors that, at some point, tip the balance between convenience and control.

The first factor is cost at scale. For a company processing millions of requests per day, the API bill can become prohibitively expensive very quickly. Revolut, with its base of over 35 million users, couldn't ignore this math. When volume is high enough, the investment in proprietary infrastructure pays off, provided the team knows how to operationalize it.

The second factor is latency. Applications requiring real-time responses can't depend on requests crossing oceans to a provider's servers. A model running locally eliminates that bottleneck. For critical operations like fraud detection or transaction approval, milliseconds matter.

The third factor is data control. Financial information is sensitive by definition. Even with data processing agreements and privacy guarantees, many organizations, especially those in regulated sectors, cannot assume the risk of exposure. A self-hosted model guarantees that data never leaves the company's controlled environment.

The fourth factor is customization. Generalist models are great for generic tasks, but when the domain is specific, financial, medical, legal, precision depends on specialized knowledge. A GLM trained or fine-tuned with internal data understands terms like "margin booking" or "invoice rollover" in a way a public model never could.

<figure>
<img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/fintech-architecture-diagram.png" alt="Architecture diagram showing the separation between external APIs and internal AI infrastructure" loading="lazy">
<figcaption>Comparison between an architecture using an external API and a self-hosted GLM infrastructure. The migration moves critical processing inside the company's security perimeter.</figcaption>
</figure>

## The Hidden Side of Self-Managed Infrastructure

Rolling out a GLM internally is not just about buying GPUs and pointing to a GitHub repository. The operational complexity is substantial and frequently underestimated by teams that have never managed this type of infrastructure.

First, there is the hardware question. Modern language models require powerful GPUs for inference at an acceptable speed. We're not talking about a graphics card for gaming, but specialized hardware with price tags that start in the thousands of dollars and go up to tens of thousands. Revolut has the resources for this. An early-stage startup, not necessarily.

Second, ongoing maintenance. Models need to be updated, security patches applied, logs monitored, metrics collected. A third-party API does this for you. When you are the operator, that responsibility is yours, and it requires people with specific expertise to fulfill it adequately.

Third, specialized knowledge. Training, fine-tuning, and deploying language models is not common knowledge. Professionals who master these skills are scarce and well-compensated. For many organizations, hiring or building that team is as or more difficult than justifying the hardware investment.

<figure>
<img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/ml-infrastructure-complexity.png" alt="Diagram showing the components of an ML production pipeline" loading="lazy">
<figcaption>A typical ML production pipeline: from data collection to model monitoring in a production environment. Each stage requires specific tools and expertise.</figcaption>
</figure>

Anyone who has operated systems in production knows that theory is different from practice. In theory, you set up the model, point it to the data, and you're ready. In practice, you discover that prompt optimization is continuous work, that models hallucinate in specific scenarios you didn't anticipate, and that quality evaluation requires metrics you hadn't thought to collect before.

## The middle path: pragmatic alternatives

The binary decision between an external API and building your own infrastructure isn’t the only option available. There are middle‑ground paths that can make sense depending on the context.

Open‑source models like Llama, Mistral, or Falcon can be downloaded and run locally. They don’t match the capability of the most advanced models from OpenAI or Anthropic, but they are surprisingly competent for many tasks. Meta has released Llama under a permissive license, and the community has created optimized versions that run on modest hardware. For specific, well‑defined use cases, this can be an efficient solution.

Another alternative is fine‑tuning smaller models. Instead of running a 70‑billion‑parameter model, you can take a 7‑billion‑parameter model and adapt it to your specific domain. The result is smaller, faster, and potentially more accurate for the tasks you’ve defined, provided you have quality training data.

Model proxies and gateways also deserve consideration. Tools such as LiteLLM or models sold as Anthropic’s Claude or OpenAI’s API through specialized providers let you swap the backend without changing your application code. This doesn’t solve the problem of external‑vendor dependence, but at least it reduces vendor lock‑in at the application level.

For those just starting out, the pragmatic recommendation is clear: begin with established providers’ APIs, validate that the product solves a real problem, and only migrate to your own infrastructure when the math justifies it. Building an ML Ops team before achieving product‑market fit is a common mistake for startups.

## What This Trend Means for Developers

The movement of major companies toward self-hosting language models has practical implications for those building software today.

The job market is fragmenting. On one hand, demand is growing for professionals who know how to integrate generative AI APIs, a knowledge base that is increasingly common and accessible. On the other hand, demand is growing for specialists in ML infrastructure, model deployment, and inference optimization. Both skill sets have a place, but they represent very different profiles.

System architecture is incorporating AI as a fundamental component. Just as we learned to design systems that use relational databases, message queues, and caches, we now need to design systems that use language models, with all the implications for latency, cost, and state management that this entails.

Observability gains a new dimension. When a language model returns an incorrect or unsuitable response, how do you detect that? Traditional metrics for uptime and latency do not capture content errors. Tools like LangSmith, arize-ai, and similar are emerging to fill this gap, but they are still immature ecosystems compared to what we have for traditional infrastructure.

## The Question That Matters

Revolut's decision wasn't about technology in the abstract. It was about strategic control over a critical component of their product. When artificial intelligence is at the core of a company's value proposition, handing that control over to third parties is a trade-off that warrants careful consideration.

For some organizations, a provider's API will always be the right choice. The resources don't justify the operational complexity, or the provider's specialization is superior to what they could build in-house. There is no shame in that choice, it's pragmatic.

For others, migration to owned infrastructure is inevitable. The volume justifies the costs, data sensitivity is incompatible with external processing, or competitive differentiation depends on a model only they can build.

The question isn't which path is right, but which path is right for you. And answering that question requires a deep understanding of your context, your resources, and your constraints, not blindly following what large companies are doing.

## Practical Takeaways

- Evaluate the real cost before migrating: add up API consumption, hardware costs, energy, specialized personnel, and compare with the third-party alternative. Migration only justifies itself at a significant scale.

- Don't underestimate operational complexity: a model in production requires monitoring, updates, prompt optimization, and failure management. Ensure you have or can build the necessary expertise.

- Consider the middle path: open-source models or fine-tuning smaller versions can offer a good balance between cost and performance for specific use cases.

- Separate what is a commodity from what is a differentiator: generic tasks can use external APIs; critical or differentiating tasks may justify your own infrastructure.

- Invest in observability from the start: response quality metrics are as important as latency and uptime when your product depends on language models.

## Sources

- [Revolut's AI Infrastructure Evolution - The Financial Times](https://www.ft.com/content/revolut-ai-infrastructure)
- [OpenAI API Documentation](https://platform.openai.com/docs/introduction)
- [Meta Llama Model Weights](https://llama.meta.com/)
- [Hugging Face Model Hub](https://huggingface.co/models)
- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)