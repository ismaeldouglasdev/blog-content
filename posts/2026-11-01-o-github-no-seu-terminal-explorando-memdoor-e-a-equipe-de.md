---
title: "O GitHub no seu terminal: explorando memdoor e a equipe de LLMs que resolve desafios de programação"
date: "2026-11-01"
category: "tutorial"
tags: ["llm", "github", "claude-code", "automa\u00e7\u00e3o", "cli"]
excerpt: "O GitHub no seu terminal: explorando memdoor e a equipe de LLMs que resolve desafios de programação."
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-11-01-o-github-no-seu-terminal-explorando-memdoor-e-a-equipe-de.jpg"
lang: "pt"
---



# O GitHub no seu terminal: explorando memdoor e a equipe de LLMs que resolve desafios de programação

Voce ja recebeu uma notification do GitHub às 23h de sexta-feira: "PR ready for review". O diff tem 847 linhas, 6 arquivos alterados, e você tem exatamente 20 minutos antes do happy hour que tanto esperou a semana toda. Você abre, tenta entender o que mudou, sente a ansiedade subindo, e simplemente fecha a aba. Amanhã você olha, Provavelmente.

Esse cenário é mais comum do que imaginamos. A quantidade de código que precisamos revisar, debugar e manter cresce exponencialmente, mas nossa capacidade de atenção e tempo não acompanha esse ritmo. E é exatamente aí que ferramentas como o memdoor entram em cena: não para substituir o desenvolvedor, mas para ser aquele colega noturno que sempre está acordado e disposto a quebrar a cabeça com código que você não quer olhar às 23h.

O memdoor é uma ferramenta open-source que combina o poder de múltiplos modelos de linguagem com uma abordagem de "equipe especializada" para resolver problemas diretamente no seu terminal. Diferente de chatbots genéricos que tentam fazer tudo, o memdoor divide o trabalho entre cinco agentes distintos, cada um com uma função específica: Analyst, Software Engineer, Security Specialist, QA e Reviewer. A arquitetura por trás dessa divisão não é arbitrária, ela reflete como equipes de desenvolvimento reais funcionam, onde cada papel traz uma perspectiva diferente para o mesmo problema.

## A ameaça invisível: extensões de IA com backdoors

Antes de mergulhar no memdoor, é importante entender o contexto que motivou sua criação. Em 2024 e 2025, assistentes de IA para IDEs se tornaram mainstream. Extensões oficiais de grandes empresas prometiam integrar Copilot, Claude e outros modelos diretamente no seu editor, facilitando a vida de milhões de desenvolvedores. O que poucos sabiam era que algumas dessas extensões coletavam dados de forma mais agressiva do que o esperado, armazenando histórico de navegação, tokens de acesso e até mesmo commits não salvos em servidores externos.

A descoberta dessas "backdoors", funcionalidade não documentada que exfiltra dados, gerou uma onda de desconfiança na comunidade. Desenvolvedores começaram a questionar: até que ponto posso confiar em ferramentas que pedem acesso ao meu código? A resposta honesta é que, para projetos sensíveis, a resposta deveria ser "com muita cautela". Esse cenário abriu espaço para ferramentas que priorizam privacidade e controle total sobre os dados.

O memdoor nasceu nesse contexto de desconfiança. Ele roda localmente, não exige que seu código saia da sua máquina, e te dá transparência sobre o que cada agente está fazendo. Não é uma solução mágica, mas é uma alternativa concreta para quem quer usar IA sem aceitar termos de serviço obscuros.

## Memdoor: uma equipe de cinco modelos no seu terminal

O nome "memdoor" é uma referência ao projeto de memória do Engram, um dos meus projetos pessoais de infraestrutura de IA. A ferramenta utiliza cinco instâncias do modelo Qwen da Alibaba, cada uma com um papel bem definido, trabalhando em conjunto para analisar e resolver problemas em repositórios GitHub ou código local.

A arquitetura de agentes especializados não é novidade no universo de IA, o GPT-4 com system prompts complexos já faz algo semelhante. Mas o memdoor leva essa ideia para um fluxo de trabalho concreto e reproduzível, onde cada agente passa seus resultados para o próximo, criando uma cadeia de processamento que mimetiza uma revisão de código profissional.

<figure>
    <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/memdoor-architecture.png" alt="Diagrama da arquitetura de cinco agentes do memdoor" loading="lazy">
    <figcaption>Arquitetura do memdoor: cinco agentes especializados trabalhando em pipeline</figcaption>
</figure>

O Analyst é o primeiro a agir. Ele recebe a tarefa, seja encontrar um bug, revisar um PR ou explicar uma funcionalidade, e quebra o problema em partes menores, identificando os arquivos críticos e as possíveis áreas de risco. É como aquele desenvolvedor sênior que, ao olhar um diff enorme, rapidamente aponta: "O problema está aqui, nessa função que altera o estado global."

Em seguida entra o Software Engineer. Com o diagnóstico em mãos, ele propõe soluções concretas, gera código ou sugere refatorações. O Security Specialist age como um guardião, analisando as mudanças sob a ótica de vulnerabilidades: injeções, exposição de dados sensíveis, problemas de autenticação. O QA executa testes mentais, simulando edge cases e cenários que poderiam quebrar a aplicação. Finalmente, o Reviewer junta tudo isso em uma conclusão coerente, sintetizando os achados em um relatório legível.

## Configurando o memdoor do zero

A instalação do memdoor é direto ao ponto. Você vai precisar do Git, Go (para rodar alguns scripts de suporte) e acesso a modelos Qwen via API compatível. A ferramenta está disponível no GitHub e pode ser clonada diretamente:

```
git clone https://github.com/memdoor/memdoor-cli.git
cd memdoor-cli
cargo build --release
```

O binário resultante é o seu ponto de entrada para todas as operações. A primeira configuração que você precisa fazer é definir os endpoints dos modelos Qwen. O memdoor espera cinco URLs diferentes, uma para cada agente. Se você usa um servidor local como Ollama ou LM Studio, pode configurar assim:

```
export MEMDOOR_MODEL_ANALYST="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_ENGINEER="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_SECURITY="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_QA="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_REVIEWER="http://localhost:11434/api/generate"
```

Alternativamente, você pode criar um arquivo de configuração em JSON que especifica todos os endpoints:

```
{
  "models": {
    "analyst": "http://localhost:11434/api/generate",
    "engineer": "http://localhost:11434/api/generate",
    "security": "http://localhost:11434/api/generate",
    "qa": "http://localhost:11434/api/generate",
    "reviewer": "http://localhost:11434/api/generate"
  },
  "timeout": 120,
  "temperature": 0.7
}
```

Para quem usa APIs comerciais, o memdoor também aceita endpoints do Together AI ou outros provedores compatíveis com OpenAI-compatible API.

## Revisando PRs automaticamente

O caso de uso mais comum do memdoor é a revisão automática de pull requests. Imagine que você recebe um link para um PR e quer um resumo rápido antes de mergulhar no código. O memdoor pode analisar o diff e gerar um relatório estruturado em poucos segundos:

```
memdoor pr analyze https://github.com/usuario/repositorio/pull/123
```

O output é divido em seções claras: impacto da mudança, riscos identificados, sugestões de melhoria e uma avaliação geral de qualidade. Você pode configurar o nível de detalhe que quer no output, desde um resumo executivo até uma análise linha por linha.

<figure>
    <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/memdoor-pr-analysis.png" alt="Exemplo de análise de PR pelo memdoor no terminal" loading="lazy">
    <figcaption>Saída típica de análise de PR: cinco seções correspondentes aos cinco agentes</figcaption>
</figure>

Para quem trabalha com múltiplos repositórios, o memdoor suporta configuração por projeto. Você pode criar um arquivo `.memdoor.json` na raiz do repositório com preferências específicas: modelos diferentes para cada agente, prompts customizados para o contexto do projeto, e filtros para ignorar certos tipos de arquivo ou pasta.

## Caçando bugs em código local

Além de analisar PRs, o memdoor pode trabalhar diretamente com código no seu filesystem. O comando `memdoor search` é útil quando você suspeita que existe um bug em algum lugar, mas não sabe onde procurar:

```
memdoor search --query "possible null pointer dereference in user authentication flow"
```

O Analyst vai escanear o repositório, identificar os arquivos relevantes para essaquery, e o Engineer vai propor correções candidatas. O Security Specialist verifica se a correção introduz algum novo vetor de ataque.

Outro comando poderoso é o `memdoor verify`, que você pode usar para confirmar se uma solução proposta realmente funciona:

```
memdoor verify --file src/auth.go --function ValidateToken --test-case "expired token"
```

O fluxo é sempre o mesmo: análise primeiro, depois ação, depois revisão. Essa cadência impede que a ferramenta pule etapas e ofereça soluções precipitadas.

## Quando a IA encontra seus próprios projetos

O memdoor é particularmente útil quando você quer uma segunda opinião sobre código que escreveu há semanas. No meu workflow, uso ele regularmente para revisar PRs nos meus projetos pessoais, como o inventory-service, que integra OSPOS com Mercado Livre, ou o provider-health-daemon, que gerencia fallbacks entre provedores de IA.

Nesses projetos, o memdoor já identificou problemas que eu teria levado horas para encontrar: um race condition no sync de estoque, uma injeção de SQL em uma query mal construída, e um caso de borda onde tokens expirados não eram tratados corretamente. Não é que o código seja ruim, é que, depois de semanas longe de um arquivo, você perde a perspectiva de quem está lendo pela primeira vez.

O que diferencia o memdoor de um chatbot comum é a especialização. Quando pergunto ao Claude "tá dando erro aqui", ele tenta ser útil, mas faz tudo ao mesmo tempo. O memdoor força uma separação de concerns: o Analyst não propõe código, o Engineer não faz análise de segurança, cada um fica no seu quadrado. Isso reduz o ruído e aumenta a precisão das respostas.

## O papel do desenvolvedor em um ecossistema com IA

O uso de ferramentas como o memdoor levanta uma questão filosófica importante: o que sobra para o desenvolvedor fazer? Se a IA pode analisar código, encontrar bugs e propor correções, qual é o nosso valor-added?

A resposta, acredito, está em três áreas que a IA ainda não domina bem. A primeira é contexto de negócio: por que essa feature existe, quem pediu, qual problema do usuário ela resolve. O memdoor pode analisar código, mas não sabe que a razão pela qual você não pode deletar usuários inativos é uma auditoria de compliance que aconteceu em 2023.

A segunda área é julgamento arquitetural. Quando há trade-offs envolvidos, simplicidade versus performance, flexibilidade versus manutenibilidade, a IA pode apresentar opções, mas quem decide é o humano com conhecimento do contexto maior do sistema.

A terceira área é responsabilidade final. Código revisado por IA ainda é código revisado por você. Se algo quebra em produção, é seu nome na línea de blame, não da ferramenta. Isso significa que você não pode simplesmente aceitar sugestões sem entender o que elas fazem.

O memdoor, corretamente, não tenta eliminar o desenvolvedor do fluxo. Ele se posiciona como um assistente que acelera as partes mecânicas do trabalho, ler diffs extensos, encontrar padrões conhecidos, verificar vulnerabilidades comuns, liberando o humano para as decisões que realmente importam.

## Configurações avançadas e integrações

Para quem quer customizar o comportamento do memdoor, existem várias opções interessantes. Você pode definir system prompts diferentes para cada agente, alterando fundamentalmente como eles trabalham. Um Security Specialist mais agressivo vai reportar até falsos positivos em potencial. Um QA mais detalhista vai testar mais edge cases.

O memdoor também pode ser integrado em pipelines de CI/CD. Um workflow comum é rodar o memdoor antes de aceitar um merge, failando o build se o Score geral cair abaixo de um threshold configurável. Isso adiciona uma camada automática de review que complementa, mas não substitui, a revisão humana.

Para quem usa GitHub Actions, há um action oficial que encapsula o memdoor:

```yaml
- name: Run memdoor analysis
  uses: memdoor/action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    min-score: 70
    fail-on-critical: true
```

Isso permite que equipes adotem análise automática de código por IA sem precisar configurar nada manualmente em cada projeto.

## Limitações e cuidados

Sendo honesto, o memdoor não é solução para tudo. Para problemas complexos que exigem raciocínio sobre múltiplas partes do sistema simultaneamente, a abordagem linear de agentes especializados pode perder conexões importantes. Se o bug está na intersecção entre autenticação e cache, por exemplo, você ainda vai precisar olhar o código você mesmo.

Além disso, modelos Qwen, embora competentes, não são tão poderosos quanto modelos maiores como Claude 3.5 ou GPT-4 para tarefas que exigem reasoning profundo. A escolha do Qwen é uma escolha por custo-benefício e controlabilidade, não por performance máxima.

Outro ponto de atenção é o custo de rodar cinco modelos localmente. Se você está usando API, o custo é multiplicado por cinco. Para uso intensivo, configurar um servidor local com GPU dedicada se paga rapidamente, mas exige manutenção que nem todo mundo quer assumir.

## Takeaways praticos

- O memdoor é uma alternativa open-source às extensões de IA para IDEs, rodando localmente e oferecendo transparência total sobre o processamento.
- A arquitetura de cinco agentes especializados (Analyst, Engineer, Security, QA, Reviewer) mimetiza uma equipe de revisão profissional.
- Use o memdoor para reviews rápidos de PRs, busca de bugs em código local, e como segunda opinião sobre mudanças que você fez há tempo.
- A ferramenta não substitui o desenvolvedor, ela acelera as partes mecânicas, liberando tempo para decisões de negócio e arquitetura.
- Para projetos sensíveis, rodar modelos localmente elimina riscos de exfiltração de dados que existem em algumas extensões oficiais de IA.

## Fontes

- [Repositório oficial do memdoor no GitHub](https://github.com/memdoor/memdoor-cli)
- [Qwen Model Series - Documentação da Alibaba](https://github.com/QwenLM/Qwen)
- [Ollama - Rodada de LLMs localmente](https://github.com/ollama/ollama)
- [Engram - Projeto de memória para LLMs (conceito relacionado)](https://github.com/memdoor/engram)
- [GitHub Actions - Documentação oficial](https://docs.github.com/en/actions)
- [Architectural Patterns for Multi-Agent LLM Systems](https://www.anthropic.com/research/claude-system-prompts)
