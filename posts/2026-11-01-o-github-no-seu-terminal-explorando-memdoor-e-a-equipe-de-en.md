---
title: "GitHub in your terminal: exploring memdoor and the LLM team that solves programming challenges"
date: "2026-11-01"
category: "tutorial"
tags: ["llm", "github", "claude-code", "automa\u00e7\u00e3o", "cli"]
excerpt: "GitHub in Your Terminal: Exploring memdoor and the LLM Team That Solves Programming Challenges"
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-11-01-o-github-no-seu-terminal-explorando-memdoor-e-a-equipe-de.jpg"
lang: "en"
translation_of: "2026-11-01-o-github-no-seu-terminal-explorando-memdoor-e-a-equipe-de"
---
# GitHub in Your Terminal: Exploring memdoor and the LLM Team That Solves Programming Challenges

You've just received a GitHub notification at 11 PM on a Friday: "PR ready for review." The diff is 847 lines, 6 changed files, and you have exactly 20 minutes before the happy hour you've been looking forward to all week. You open it, try to understand what changed, feel the anxiety rising, and simply close the tab. You'll look at it tomorrow. Probably.

This scenario is more common than we imagine. The amount of code we need to review, debug, and maintain grows exponentially, but our attention span and time don't keep up with that pace. And that's exactly where tools like memdoor come into play: not to replace the developer, but to be that night-shift colleague who's always awake and willing to puzzle over code you don't want to look at at 11 PM.

Memdoor is an open-source tool that combines the power of multiple large language models with a "specialized team" approach to solve problems directly in your terminal. Unlike generic chatbots that try to do everything, memdoor divides the work among five distinct agents, each with a specific role: Analyst, Software Engineer, Security Specialist, QA, and Reviewer. The architecture behind this division isn't arbitrary, it reflects how real development teams function, where each role brings a different perspective to the same problem.

## The invisible threat: AI extensions with backdoors

Before diving into memdoor, it's important to understand the context that motivated its creation. In 2024 and 2025, AI assistants for IDEs became mainstream. Official extensions from major companies promised to integrate Copilot, Claude, and other models directly into your editor, making life easier for millions of developers. What few knew was that some of these extensions collected data more aggressively than expected, storing browsing history, access tokens, and even unsaved commits on external servers.

The discovery of these "backdoors", undocumented functionality that exfiltrates data, generated a wave of distrust in the community. Developers began to question: to what extent can I trust tools that ask for access to my code? The honest answer is that, for sensitive projects, the answer should be "with great caution." This scenario opened space for tools that prioritize privacy and total control over data.

Memdoor was born in this context of distrust. It runs locally, doesn't require your code to leave your machine, and gives you transparency about what each agent is doing. It's not a magic solution, but it's a concrete alternative for those who want to use AI without accepting obscure terms of service.

## Memdoor: a five-model team in your terminal

The name "memdoor" is a reference to the Engram memory project, one of my personal AI infrastructure projects. The tool uses five instances of Alibaba's Qwen model, each with a well-defined role, working together to analyze and solve problems in GitHub repositories or local code.

Specialized agent architecture isn't new in the AI world, GPT‑4 with complex system prompts does something similar. But memdoor brings this idea into a concrete, reproducible workflow, where each agent passes its results to the next, creating a processing chain that mimics a professional code review.

<figure>
    <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/memdoor-architecture.png" alt="Diagram of memdoor's five‑agent architecture" loading="lazy">
    <figcaption>Memdoor architecture: five specialized agents working in pipeline</figcaption>
</figure>

The Analyst acts first. It receives the task, whether it's finding a bug, reviewing a PR, or explaining a feature, and breaks the problem into smaller pieces, identifying critical files and potential risk areas. It's like that senior developer who, looking at a huge diff, quickly points out: "The problem is here, in this function that alters global state."

Next comes the Software Engineer. With the diagnosis in hand, it proposes concrete solutions, generates code, or suggests refactors. The Security Specialist acts as a guardian, analyzing the changes through a vulnerability lens: injections, sensitive data exposure, authentication issues. The QA runs mental tests, simulating edge cases and scenarios that could break the application. Finally, the Reviewer pulls everything together into a coherent conclusion, synthesizing the findings into a readable report.

## Setting up memdoor from scratch

memdoor installation is straightforward. You'll need Git, Go (to run some support scripts), and access to Qwen models via a compatible API. The tool is available on GitHub and can be cloned directly:

```
git clone https://github.com/memdoor/memdoor-cli.git
cd memdoor-cli
cargo build --release
```

The resulting binary is your entry point for all operations. The first setup step you need to take is to define the endpoints for the Qwen models. memdoor expects five different URLs, one for each agent. If you use a local server like Ollama or LM Studio, you can configure it like this:

```
export MEMDOOR_MODEL_ANALYST="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_ENGINEER="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_SECURITY="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_QA="http://localhost:11434/api/generate"
export MEMDOOR_MODEL_REVIEWER="http://localhost:11434/api/generate"
```

Alternatively, you can create a JSON configuration file specifying all endpoints:

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

For those using commercial APIs, memdoor also accepts endpoints from Together AI or other providers compatible with the OpenAI API format.

## Automatically reviewing PRs

The most common use case for memdoor is automated pull request reviews. Imagine you receive a link to a PR and want a quick summary before diving into the code. Memdoor can analyze the diff and generate a structured report in just a few seconds:

```
memdoor pr analyze https://github.com/usuario/repositorio/pull/123
```

The output is divided into clear sections: impact of the change, identified risks, improvement suggestions, and an overall quality assessment. You can configure the level of detail you want in the output, from an executive summary to a line-by-line analysis.

<figure>
    <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/memdoor-pr-analysis.png" alt="Example of PR analysis by memdoor in the terminal" loading="lazy">
    <figcaption>Typical PR analysis output: five sections corresponding to the five agents</figcaption>
</figure>

For those working with multiple repositories, memdoor supports per-project configuration. You can create a `.memdoor.json` file in the repository root with specific preferences: different models for each agent, custom prompts for the project context, and filters to ignore certain types of files or folders.

## Hunting bugs in local code

Besides analyzing PRs, memdoor can work directly with code in your filesystem. The `memdoor search` command is useful when you suspect there's a bug somewhere but don't know where to look:

```
memdoor search --query "possible null pointer dereference in user authentication flow"
```

The Analyst will scan the repository, identify the relevant files for that query, and the Engineer will propose candidate fixes. The Security Specialist verifies whether the fix introduces any new attack vectors.

Another powerful command is `memdoor verify`, which you can use to confirm whether a proposed solution actually works:

```
memdoor verify --file src/auth.go --function ValidateToken --test-case "expired token"
```

The flow is always the same: analysis first, then action, then review. This cadence prevents the tool from skipping steps and offering hasty solutions.

## When AI Encounters Its Own Projects

Memdoor is particularly useful when you want a second opinion on code you wrote weeks ago. In my workflow, I regularly use it to review PRs in my personal projects, like the inventory-service, which integrates OSPOS with Mercado Livre, or the provider-health-daemon, which manages fallbacks between AI providers.

In these projects, memdoor has already identified problems that would have taken me hours to find: a race condition in inventory sync, SQL injection in a poorly constructed query, and an edge case where expired tokens weren't being handled correctly. It's not that the code is bad, it's that after weeks away from a file, you lose the perspective of someone reading it for the first time.

What differentiates memdoor from a common chatbot is specialization. When I ask Claude "it's throwing an error here," it tries to be helpful, but does everything at once. Memdoor forces a separation of concerns: the Analyst doesn't propose code, the Engineer doesn't do security analysis, each one stays in its lane. This reduces noise and increases the precision of responses.

## The Developer's Role in an AI-Powered Ecosystem

The use of tools like memdoor raises an important philosophical question: what's left for the developer to do? If AI can analyze code, find bugs, and propose fixes, what is our value-added?

The answer, I believe, lies in three areas that AI still doesn't master well. The first is business context: why a feature exists, who requested it, which user problem it solves. memdoor can analyze code, but it doesn't know that the reason you can't delete inactive users is a compliance audit that happened in 2023.

The second area is architectural judgment. When trade-offs are involved, simplicity versus performance, flexibility versus maintainability, AI can present options, but the human with knowledge of the larger system context makes the decision.

The third area is ultimate responsibility. AI-reviewed code is still code reviewed by you. If something breaks in production, it's your name on the blame line, not the tool's. That means you can't simply accept suggestions without understanding what they do.

memdoor, correctly, does not try to eliminate the developer from the workflow. It positions itself as an assistant that accelerates the mechanical parts of the work, reading extensive diffs, finding known patterns, checking for common vulnerabilities, freeing the human for the decisions that truly matter.

## Advanced settings and integrations

For those who want to customize memdoor's behavior, there are several interesting options. You can set different system prompts for each agent, fundamentally changing how they work. A more aggressive Security Specialist will report even potential false positives. A more meticulous QA agent will test more edge cases.

Memdoor can also be integrated into CI/CD pipelines. A common workflow is to run memdoor before accepting a merge, failing the build if the overall Score falls below a configurable threshold. This adds an automated review layer that complements, but does not replace, human review.

For those using GitHub Actions, there is an official action that encapsulates memdoor:

```yaml
- name: Run memdoor analysis
  uses: memdoor/action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    min-score: 70
    fail-on-critical: true
```

This allows teams to adopt automated AI-powered code analysis without needing to manually configure anything in each project.

## Limitations and considerations

To be honest, memdoor isn't a solution for everything. For complex problems that require reasoning about multiple parts of the system simultaneously, the linear approach of specialized agents can miss important connections. If the bug is at the intersection between authentication and cache, for example, you'll still need to look at the code yourself.

Furthermore, Qwen models, while competent, aren't as powerful as larger models like Claude 3.5 or GPT-4 for tasks that require deep reasoning. Choosing Qwen is a choice for cost-effectiveness and controllability, not for maximum performance.

Another point to consider is the cost of running five models locally. If you're using an API, the cost is multiplied by five. For intensive use, setting up a local server with a dedicated GPU pays off quickly, but requires maintenance that not everyone wants to handle.

## Practical takeaways

- Memdoor is an open-source alternative to AI IDE extensions, running locally and offering full transparency over processing.
- The architecture of five specialized agents (Analyst, Engineer, Security, QA, Reviewer) mimics a professional review team.
- Use Memdoor for quick PR reviews, bug hunting in local code, and as a second opinion on changes you made a while ago.
- The tool does not replace the developer, it accelerates the mechanical parts, freeing up time for business and architectural decisions.
- For sensitive projects, running models locally eliminates data exfiltration risks that exist in some official AI extensions.

## Sources

- [Official memdoor repository on GitHub](https://github.com/memdoor/memdoor-cli)
- [Qwen Model Series - Alibaba documentation](https://github.com/QwenLM/Qwen)
- [Ollama - Run LLMs locally](https://github.com/ollama/ollama)
- [Engram - Memory project for LLMs (related concept)](https://github.com/memdoor/engram)
- [GitHub Actions - Official documentation](https://docs.github.com/en/actions)
- [Architectural Patterns for Multi-Agent LLM Systems](https://www.anthropic.com/research/claude-system-prompts)