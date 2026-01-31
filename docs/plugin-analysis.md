# Claude Code Plugin & Extension Analysis for DCI Swarm

> Generated 2026-01-31. DCI Swarm stack: Python/FastAPI backend, React/TypeScript frontend, SQLite DB, pytest tests.

## Table of Contents
- [Official Marketplace Plugins](#official-marketplace-plugins)
  - [LSP Plugins](#lsp-plugins)
  - [Workflow & Development Plugins](#workflow--development-plugins)
  - [External / Partner Plugins](#external--partner-plugins)
- [BuildWithClaude Community Marketplace](#buildwithclaude-community-marketplace)
  - [Agent Packages](#agent-packages)
  - [Command Packages](#command-packages)
  - [Hook Packages](#hook-packages)
  - [Skill Packages](#skill-packages)
  - [Utilities](#utilities)
- [Recommendations for DCI Swarm](#recommendations-for-dci-swarm)

---

## Official Marketplace Plugins

Source: `anthropics/claude-plugins-official` — 56 plugins total.

### LSP Plugins

Language Server Protocol plugins provide code intelligence (diagnostics, go-to-definition, completions) for specific languages. All are **free/OSS** — they wrap open-source language servers that run locally.

| Plugin | Installs | Language | Server | Cost | DCI Swarm? |
|--------|----------|----------|--------|------|------------|
| **typescript-lsp** | 48,026 | TS/JS (.ts, .tsx, .js, .jsx) | `typescript-language-server` | Free | **YES — install** |
| **pyright-lsp** | 25,345 | Python (.py, .pyi) | `pyright-langserver` | Free | **YES — install** |
| **csharp-lsp** | 8,787 | C# (.cs) | `csharp-ls` | Free | Skip — not in stack |
| **gopls-lsp** | 9,450 | Go (.go) | `gopls` | Free | Skip — not in stack |
| **rust-analyzer-lsp** | 8,176 | Rust (.rs) | `rust-analyzer` | Free | Skip — not in stack |
| **jdtls-lsp** | 7,062 | Java (.java) | `jdtls` | Free | Skip — not in stack |
| **php-lsp** | 7,087 | PHP (.php) | `intelephense` | Free | Skip — not in stack |
| **clangd-lsp** | 6,129 | C/C++ (.c, .cpp, .h) | `clangd` | Free | Skip — not in stack |
| **swift-lsp** | 5,970 | Swift (.swift) | `sourcekit-lsp` | Free | Skip — not in stack |
| **lua-lsp** | 3,711 | Lua (.lua) | `lua-language-server` | Free | Skip — not in stack |
| **kotlin-lsp** | 3,372 | Kotlin (.kt, .kts) | `kotlin-lsp` | Free | Skip — not in stack |

### Workflow & Development Plugins

These are Anthropic-authored plugins that extend Claude Code with agents, commands, hooks, and skills. All are **free** — no additional subscriptions required beyond Claude Code access.

| Plugin | Installs | Type | Summary | DCI Swarm? |
|--------|----------|------|---------|------------|
| **frontend-design** | 141,226 | Skill | Production-grade UI generation. Avoids generic AI aesthetics. | **INSTALLED** |
| **code-review** | 68,604 | Command + Agents | `/code-review` runs 4 parallel review agents (CLAUDE.md compliance, bug detection, git history analysis). Confidence-scored (threshold ≥80) to filter false positives. | **YES — install** |
| **feature-dev** | 63,312 | Command + Agents | `/feature-dev` 7-phase workflow: discovery → exploration (2-3 parallel agents) → questions → architecture design → implementation → quality review → summary. | **Consider** |
| **code-simplifier** | 50,966 | Agent | Simplifies recently modified code for clarity and maintainability. Preserves functionality. | **Consider** |
| **ralph-loop** | 49,856 | Command | Iterative self-referential development loops. Claude works on the same task repeatedly, seeing previous output, until done. | **Consider** |
| **playwright** | 43,949 | MCP Server | Browser automation via `npx @playwright/mcp@latest`. Screenshots, clicks, form fills, E2E testing. | **INSTALLED** |
| **commit-commands** | 42,189 | Commands | Slash commands for git commit, push, PR workflows. | **YES — install** |
| **security-guidance** | 37,088 | Hook | Pre-edit hooks that warn about command injection, XSS, SQL injection, and other security issues. | **YES — install** |
| **pr-review-toolkit** | 28,370 | Agents (6) | Specialized reviewers: comment-analyzer, test-analyzer, silent-failure-hunter, type-design-analyzer, code-reviewer, code-simplifier. | **Consider** |
| **agent-sdk-dev** | 23,466 | Dev Kit | Tools for building with the Claude Agent SDK. | Skip — not building SDK agents |
| **explanatory-output-style** | 17,072 | Hook | Educational insights on implementation choices. Mimics deprecated output style. | Skip — noise |
| **plugin-dev** | 16,985 | Skills (7) | Toolkit for developing Claude Code plugins. Hooks, MCP, commands, agents, best practices. | Skip — not building plugins now |
| **hookify** | 14,821 | Agent + Commands | Create custom hooks from conversation patterns or markdown rules. | **Consider** |
| **learning-output-style** | 11,289 | Hook | Interactive learning mode at decision points. | Skip — noise |
| **claude-md-management** | 10,055 | Commands + Skills | Audit CLAUDE.md quality, capture session learnings, keep project memory current. | **Consider** |
| **claude-code-setup** | 7,707 | Analysis | Analyzes codebase and recommends hooks, skills, MCP servers, subagents. | **Consider** — run once |
| **playground** | — | Skill | Interactive single-file HTML playgrounds with visual controls and live preview. | Skip — not relevant |

### External / Partner Plugins

Third-party integrations, mostly MCP servers. Cost depends on the external service.

| Plugin | Installs | Author | Summary | Cost | DCI Swarm? |
|--------|----------|--------|---------|------|------------|
| **context7** | 93,538 | Upstash | Up-to-date, version-specific documentation lookup from source repos. Pulls docs into LLM context. | **Free** | **YES — install** |
| **github** | 65,584 | GitHub | Official GitHub MCP: issues, PRs, code review, repo search, full API. | **Freemium** — free for public repos, GitHub account required | **Consider** — already have `gh` CLI |
| **superpowers** | 34,811 | obra (community) | Brainstorming, subagent-driven dev with code review, systematic debugging, red/green TDD. Teaches Claude to author/test skills. | **Free/OSS** | **YES — install** |
| **serena** | 41,906 | Oraios | Semantic code analysis MCP: intelligent code understanding, refactoring suggestions, codebase navigation via LSP. | **Free/OSS** | **Consider** — overlaps with LSPs |
| **figma** | 24,638 | Figma | Access design files, extract components, read tokens, translate designs to code. | **Requires Figma subscription** | Skip — no Figma in workflow |
| **supabase** | 26,504 | Supabase | Database ops, auth, storage, real-time. Manage Supabase projects + SQL queries. | **Requires Supabase account** | Skip — using SQLite/PostgreSQL |
| **atlassian** | 21,859 | Atlassian | Jira + Confluence: issues, docs, sprints. | **Requires Atlassian subscription** | Skip — not using Atlassian |
| **Notion** | 14,848 | Notion | Search pages, create docs, manage databases, access knowledge base. | **Requires Notion account** | Skip — not using Notion |
| **greptile** | 15,175 | Greptile | AI-powered codebase search. Natural language queries over repos. | **Requires Greptile account** | Skip — have built-in search |
| **linear** | 12,680 | Linear | Issue tracking: create issues, manage projects, search workspaces. | **Requires Linear subscription** | Skip |
| **vercel** | 11,634 | Vercel | Deployment management, build status, logs, domains. | **Requires Vercel account** | Skip — not deploying to Vercel |
| **sentry** | 10,026 | Sentry | Error monitoring: error reports, stack traces, issue search. | **Requires Sentry subscription** | Skip |
| **slack** | 9,528 | Slack | Search messages, channels, threads. | **Requires Slack workspace** | Skip |
| **gitlab** | 8,353 | GitLab | Repos, MRs, CI/CD, issues, wikis. | **Requires GitLab account** | Skip — using GitHub |
| **laravel-boost** | 8,292 | Community | Laravel dev: Artisan, Eloquent, routing, migrations. | Free | Skip — not using Laravel |
| **stripe** | 7,973 | Stripe | Stripe API integration. | **Requires Stripe account** | Skip |
| **firebase** | 5,913 | Google | Firestore, auth, cloud functions, hosting, storage. | **Requires Firebase account** | Skip |
| **huggingface-skills** | 4,901 | Hugging Face | Build, train, evaluate open-source AI models, datasets, spaces. | **Free** (HF account) | Skip — not training models |
| **posthog** | — | PostHog | Product analytics. 10 slash commands, OAuth auth. | **Requires PostHog account** | Skip |
| **coderabbit** | — | CodeRabbit | Code review with AI + 40 static analyzers. | **Requires CodeRabbit account** | Skip — have code-review plugin |
| **asana** | 2,434 | Asana | Task/project management. | **Requires Asana subscription** | Skip |
| **pinecone** | 2,029 | Pinecone | Vector database management, index ops, querying. | **Requires Pinecone account** | Skip — using ChromaDB |
| **circleback** | 2,088 | Circleback | Meeting/email/calendar context search. | **Requires Circleback account** | Skip |

---

## BuildWithClaude Community Marketplace

Source: `davepoon/buildwithclaude` — MIT licensed, community-driven.
Install: `claude plugin marketplace add davepoon/buildwithclaude`

All plugins in this marketplace are **free/OSS**. They are prompt-based extensions (agents, commands, hooks, skills) that don't require external services unless noted.

### Agent Packages

11 packages, 117 total agents. Each agent is a specialized AI persona with domain expertise.

| Package | Agents | Summary | DCI Swarm? |
|---------|--------|---------|------------|
| **agents-development-architecture** | 11 | backend-architect, frontend-developer, graphql-architect, nextjs/react/laravel/drupal/wordpress devs, ios-developer, mobile-developer | **Consider** — backend-architect, frontend-developer relevant |
| **agents-language-specialists** | 12 | python-expert, typescript-expert, javascript-developer, golang, rust, java, ruby, rails, php, cpp, c, sql | **Consider** — python-expert, typescript-expert relevant |
| **agents-quality-security** | 15 | code-reviewer, debugger, error-detective, security-auditor, performance-engineer, test-automator, api-security-audit, mcp-server-architect, mcp-testing-engineer, incident-responder, review-agent, dx-optimizer, command-expert, architect-review, mcp-security-auditor | **YES — install** |
| **agents-infrastructure-operations** | 8 | cloud-architect, database-admin, database-optimization, deployment-engineer, devops-troubleshooter, network-engineer, terraform-specialist, database-optimizer | **Consider** — database agents relevant |
| **agents-data-ai** | 11 | ai-engineer, prompt-engineer, ml-engineer, data-engineer, data-scientist, context-manager, search-specialist, mlops-engineer, hackathon-ai-strategist, task-decomposition-expert, llms-maintainer | **Consider** — prompt-engineer, ai-engineer, task-decomposition-expert relevant |
| **agents-specialized-domains** | 41 | academic-researcher, api-documenter, game-developer, legacy-modernizer, project-supervisor-orchestrator, research-coordinator, report-generator, mcp-expert, mcp-registry-navigator, and 32 more | **Consider** — api-documenter, project-supervisor-orchestrator relevant |
| **agents-design-experience** | 2 | accessibility-specialist, ui-ux-designer | Skip — have frontend-design |
| **agents-business-finance** | 4 | business-analyst, legal-advisor, payment-integration, quant-analyst | Skip — wrong domain |
| **agents-crypto-trading** | 5 | crypto-analyst, crypto-trader, defi-strategist, arbitrage-bot, crypto-risk-manager | Skip — wrong domain |
| **agents-blockchain-web3** | 2 | blockchain-developer, hyperledger-fabric-developer | Skip — wrong domain |
| **agents-sales-marketing** | 6 | content-marketer, customer-support, risk-manager, sales-automator, social-media-clip-creator, social-media-copywriter | Skip — wrong domain |

### Command Packages

22 packages, 175 total commands.

| Package | Commands | Summary | DCI Swarm? |
|---------|----------|---------|------------|
| **commands-code-analysis-testing** | 18 | /tdd, /test-coverage, /generate-tests, /write-tests, /check, /clean, /optimize, /e2e-setup, /generate-test-cases, mutation testing, property-based testing, load testing, visual testing | **YES — install** |
| **commands-version-control-git** | 12 | /commit, /commit-fast, /create-pr, /bug-fix, /fix-issue, /fix-pr, /pr-review, /update-branch-name, /husky, /create-worktrees, /fix-github-issue, /create-pull-request | **Consider** — overlaps with commit-commands |
| **commands-documentation-changelogs** | 10 | /create-docs, /update-docs, /docs, /migration-guide, /troubleshooting-guide, /create-architecture-documentation, /create-onboarding-guide, /explain-issue-fix, /add-to-changelog, /load-llms-txt | **Consider** |
| **commands-project-task-management** | 16 | /create-feature, /create-prd, /init-project, /milestone-tracker, /project-health-check, /todo, /pac-* (project-as-code), /project-timeline-simulator, /add-package, /create-command, /create-jtbd, /create-prp | **Consider** |
| **commands-security-audit** | 4 | /security-audit, /security-hardening, /dependency-audit, /add-authentication-system | **Consider** |
| **commands-team-collaboration** | 12 | /architecture-review, /sprint-planning, /standup-report, /dependency-mapper, /issue-triage, /migration-assistant, /retrospective-analyzer, /session-learning-capture, /estimate-assistant, /decision-quality-analyzer, /memory-spring-cleaning, /team-workload-balancer | **Consider** — /architecture-review, /dependency-mapper relevant |
| **commands-utilities-debugging** | 14 | /debug-error, /explain-code, /refactor-code, /code-review, /check-file, /ultra-think, /all-tools, /directory-deep-dive, /architecture-scenario-explorer, /code-permutation-tester, /git-status, /code-to-task, /clean-branches, /generate-linear-worklog | **Consider** — /debug-error, /ultra-think useful |
| **commands-performance-optimization** | 6 | /performance-audit, /optimize-build, /optimize-bundle-size, /implement-caching-strategy, /setup-cdn-optimization, /system-behavior-simulator | Skip — premature |
| **commands-api-development** | 4 | /design-rest-api, /doc-api, /generate-api-documentation, /implement-graphql-api | **Consider** — /doc-api relevant for FastAPI |
| **commands-ci-deployment** | 11 | /ci-setup, /prepare-release, /release, /changelog, /containerize-application, /hotfix-deploy, /rollback-deploy, /setup-kubernetes-deployment, /run-ci, /setup-automated-releases, /add-changelog | Skip — no CI/CD yet |
| **commands-database-operations** | 3 | /design-database-schema, /create-database-migrations, /optimize-database-performance | **Consider** — relevant for Alembic workflow |
| **commands-context-loading-priming** | 4 | /context-prime, /initref, /prime, /rsi | **Consider** |
| **commands-automation-workflow** | 1 | /act | Skip — too vague |
| **commands-workflow-orchestration** | 9 | /start, /status, /find, /log, /move, /remove, /report, /resume, /sync | Skip — overlaps with dci CLI |
| **commands-monitoring-observability** | 2 | /add-performance-monitoring, /setup-monitoring-observability | Skip — have custom monitoring |
| **commands-project-setup** | 6 | /setup-development-environment, /setup-linting, /setup-formatting, /setup-monorepo, /modernize-deps, /setup-rate-limiting | Skip — project already set up |
| **commands-integration-sync** | 12 | Linear integration commands, sync automation | Skip — not using Linear |
| **commands-framework-svelte** | 16 | Svelte/SvelteKit commands | Skip — not using Svelte |
| **commands-game-development** | 1 | /unity-project-setup | Skip |
| **commands-simulation-modeling** | 8 | /business-scenario-explorer, /decision-tree-explorer, /digital-twin-creator, /future-scenario-generator, and 4 more | Skip — wrong domain |
| **commands-miscellaneous** | 3 | /five, /mermaid, /use-stepper | Skip |
| **interview** | 1 | Interview command for feature planning | **Consider** |

### Hook Packages

8 packages, 28 total hooks. Event-driven automation that fires on Claude Code actions.

| Package | Hooks | Summary | DCI Swarm? |
|---------|-------|---------|------------|
| **hooks-testing** | 2 | run-tests-after-changes, test-runner — auto-run tests after file edits | **YES — install** |
| **hooks-security** | 3 | file-protection, file-protection-hook, security-scanner — block edits to sensitive files, scan for vulnerabilities | **Consider** — overlaps with security-guidance |
| **hooks-git** | 3 | auto-git-add, git-add-changes, smart-commit — automated staging and commit messages | **Consider** |
| **hooks-development** | 4 | change-tracker, file-backup, lint-on-save, smart-formatting | **Consider** — lint-on-save useful |
| **hooks-formatting** | 2 | format-javascript-files, format-python-files — auto-format on save | **Consider** |
| **hooks-notifications** | 12 | Slack, Discord, Telegram notifications (basic, detailed, error-only variants), notify-before-bash, simple-notifications | Skip — no notification channels set up |
| **hooks-automation** | 4 | automation, build-on-change, dependency-checker, slack-notifications | Skip |
| **hooks-performance** | 1 | performance-monitor | Skip — have custom monitoring |

### Skill Packages

5 packages, 26 total skills.

| Package | Summary | DCI Swarm? |
|---------|---------|------------|
| **all-skills** | Bundle of 26 skills: document processing, dev workflows, business productivity, creative collaboration | **Consider** — broad utility |
| **claude-hud** | Real-time statusline: context usage, tool activity, agent tracking, todo progress | **YES — install** |
| **frontend-design-pro** | Advanced design wizard, moodboards, WCAG accessibility, color/typography selection | Skip — have frontend-design |
| **nextjs-expert** | Next.js App Router, Server Components, Route Handlers, Server Actions | Skip — not using Next.js |
| **obsidian-skills** | Obsidian markdown, wikilinks, embeds, callouts, Bases, Canvas | Skip — not using Obsidian |

---

## Recommendations for DCI Swarm

### Tier 1: Install Immediately

High value, free, directly relevant to the Python/FastAPI + React/TypeScript stack.

| Plugin | Source | Why |
|--------|--------|-----|
| **pyright-lsp** | Official | Python code intelligence for the entire backend. Diagnostics, completions, go-to-def. |
| **typescript-lsp** | Official | TypeScript code intelligence for the React frontend. |
| **code-review** | Official | Automated PR review with 4 parallel agents and confidence scoring. Catches bugs before merge. |
| **security-guidance** | Official | Pre-edit security hooks. Warns about injection, XSS, and OWASP issues in real time. |
| **context7** | Official | Pull up-to-date FastAPI, React, SQLAlchemy docs directly into context. No more stale knowledge. |
| **commit-commands** | Official | Streamlined `/commit`, `/push`, `/pr` workflows. |
| **superpowers** | Official | Brainstorming, subagent-driven dev, systematic debugging, red/green TDD. |
| **commands-code-analysis-testing** | BuildWithClaude | /tdd, /test-coverage, /generate-tests, /write-tests — directly supports the project's TDD approach. |
| **hooks-testing** | BuildWithClaude | Auto-run tests after changes. Catches regressions immediately. |
| **claude-hud** | BuildWithClaude | Context usage monitoring in statusline. Know when you're running low. |

### Tier 2: Consider Installing

Moderate value, may overlap with Tier 1 or existing workflows.

| Plugin | Source | Why | Caveat |
|--------|--------|-----|--------|
| **feature-dev** | Official | Structured 7-phase feature workflow with parallel agents. | Heavy — may be overkill for small features. |
| **code-simplifier** | Official | Auto-simplification of recently modified code. | Can be opinionated. |
| **hookify** | Official | Create custom hooks from markdown rules. | Useful once workflow is stable. |
| **claude-md-management** | Official | Keep CLAUDE.md current and high quality. | Run periodically, not always-on. |
| **agents-quality-security** | BuildWithClaude | 15 agents: debugger, error-detective, security-auditor, test-automator, performance-engineer. | Overlaps with code-review + security-guidance. |
| **agents-language-specialists** | BuildWithClaude | python-expert, typescript-expert agents. | Overlaps with LSPs. |
| **agents-data-ai** | BuildWithClaude | prompt-engineer, ai-engineer, task-decomposition-expert. | Relevant for DCI's agent orchestration work. |
| **commands-documentation-changelogs** | BuildWithClaude | /create-docs, /update-docs. | Useful for maintaining docs/. |
| **commands-database-operations** | BuildWithClaude | /design-database-schema, /create-database-migrations. | Relevant for Alembic workflow. |
| **pr-review-toolkit** | Official | 6 specialized reviewers including silent-failure-hunter. | Overlaps with code-review. |
| **ralph-loop** | Official | Iterative self-referential loops. | Interesting for complex multi-step work. |
| **serena** | Official | Semantic code analysis via LSP. | Overlaps with pyright-lsp + typescript-lsp. |
| **claude-code-setup** | Official | Run once to get tailored recommendations. | One-time use. |
| **hooks-development** | BuildWithClaude | lint-on-save, change-tracker. | May conflict with existing linting setup. |

### Tier 3: Skip

Wrong stack, wrong domain, or requires paid third-party subscriptions not in use.

**Wrong language:** gopls-lsp, rust-analyzer-lsp, clangd-lsp, swift-lsp, kotlin-lsp, csharp-lsp, jdtls-lsp, lua-lsp, php-lsp

**Requires paid subscription:** figma, linear, asana, atlassian, slack, notion, supabase, firebase, pinecone, vercel, sentry, stripe, posthog, coderabbit, circleback, greptile

**Wrong framework:** laravel-boost, nextjs-expert, svelte commands, unity commands, obsidian-skills

**Wrong domain:** agents-crypto-trading, agents-blockchain-web3, agents-sales-marketing, agents-business-finance, commands-simulation-modeling

**Redundant or low value:** explanatory-output-style, learning-output-style, plugin-dev, agent-sdk-dev, playground, frontend-design-pro (have frontend-design), commands-workflow-orchestration (have dci CLI), hooks-notifications (no channels configured), hooks-performance (have custom monitoring)

---

## Install Commands

```bash
# Tier 1 — Official marketplace
claude plugin install pyright-lsp
claude plugin install typescript-lsp
claude plugin install code-review
claude plugin install security-guidance
claude plugin install context7
claude plugin install commit-commands
claude plugin install superpowers

# Tier 1 — BuildWithClaude (add marketplace first)
claude plugin marketplace add davepoon/buildwithclaude
claude plugin install commands-code-analysis-testing@buildwithclaude
claude plugin install hooks-testing@buildwithclaude
claude plugin install claude-hud@buildwithclaude
```
