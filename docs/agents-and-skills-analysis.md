# Claude Code Agents & Skills Analysis for DCI Swarm

> Generated 2026-01-31. DCI Swarm stack: Python/FastAPI backend, React/TypeScript frontend, SQLite DB, pytest tests, agent orchestration engine.

## Table of Contents
- [Official Marketplace Agents](#official-marketplace-agents)
- [Official Marketplace Skills](#official-marketplace-skills)
- [BuildWithClaude Agents](#buildwithclaude-agents)
- [BuildWithClaude Skills](#buildwithclaude-skills)
- [Recommendations for DCI Swarm](#recommendations-for-dci-swarm)

---

## Official Marketplace Agents

17 agents across 6 plugins. All **free** — no additional subscriptions required.

### feature-dev Plugin (3 agents)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **code-explorer** | sonnet | Traces execution paths, maps architecture layers, documents dependencies. Read-only tools (Glob, Grep, Read, WebFetch, WebSearch). | **YES** — directly useful for understanding DCI's agent hierarchy and message flow |
| **code-architect** | sonnet | Designs feature architectures by analyzing existing patterns. Delivers implementation blueprints with specific files, component designs, data flows. | **YES** — valuable for planning new DCI features across the layered architecture |
| **code-reviewer** | sonnet | Reviews for bugs, security, quality, CLAUDE.md compliance. Confidence-scored (≥80 threshold) to filter false positives. | **YES** — catches issues across Python backend and React frontend |

### pr-review-toolkit Plugin (6 agents)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **comment-analyzer** | inherit | Analyzes code comments for accuracy, completeness, maintainability. Prevents comment rot. | **Consider** — useful during doc-heavy phases |
| **pr-test-analyzer** | inherit | Reviews PRs for test coverage quality. Focuses on behavioral coverage, not line coverage. Identifies critical gaps. | **YES** — DCI has extensive pytest suite, this ensures PR quality |
| **silent-failure-hunter** | inherit | Identifies silent failures, inadequate error handling, bad fallbacks. Zero tolerance policy. | **YES** — critical for agent orchestration where silent failures cause cascading issues |
| **type-design-analyzer** | inherit | Rates type design 1-10 on encapsulation, invariant expression, usefulness, enforcement. | **Consider** — more relevant to TypeScript frontend than Python backend |
| **code-reviewer** (pr-review) | opus | Reviews against CLAUDE.md with confidence scoring. Higher-fidelity than feature-dev version (uses opus). | **YES** — premium review quality |
| **code-simplifier** (pr-review) | opus | Simplifies code for clarity while preserving functionality. Applies project standards. | **Consider** — useful post-implementation |

### code-simplifier Plugin (1 agent)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **code-simplifier** | opus | Auto-triggered after coding tasks. Simplifies recently modified code for clarity and maintainability. | **Consider** — helpful but may be opinionated about DCI's domain-specific patterns |

### hookify Plugin (1 agent)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **conversation-analyzer** | inherit | Analyzes conversation transcripts to find behaviors worth preventing with hooks. Outputs severity-rated findings. Tools: Read, Grep only. | **Consider** — useful for defining project-specific guardrails |

### plugin-dev Plugin (3 agents)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **agent-creator** | sonnet | Translates requirements into agent specifications. Designs persona, instructions, identifiers. | Skip — not building Claude Code plugins |
| **plugin-validator** | inherit | Validates plugin structure, manifest, security. Tools: Read, Grep, Glob, Bash. | Skip — not building plugins |
| **skill-reviewer** | inherit | Reviews skill quality, trigger effectiveness, progressive disclosure. | Skip — not building skills |

### agent-sdk-dev Plugin (2 agents)

| Agent | Model | Summary | DCI Swarm? |
|-------|-------|---------|------------|
| **agent-sdk-verifier-ts** | sonnet | Verifies TypeScript Agent SDK apps for correct usage, type safety, deployment readiness. | Skip — DCI uses its own agent runtime, not the Agent SDK |
| **agent-sdk-verifier-py** | sonnet | Verifies Python Agent SDK apps for correct usage, code quality, security. | Skip — same reason |

---

## Official Marketplace Skills

14 skills across 7 plugins. All **free**.

### plugin-dev Plugin (7 skills)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **Agent Development** | "create an agent", "add an agent", "write a subagent" | Comprehensive guide for creating Claude Code plugin agents. Covers frontmatter, system prompts, triggering, validation. | Skip — not building CC plugins, but DCI has its own agent definitions |
| **Command Development** | "create a slash command", "add a command" | Guide for developing slash commands. YAML frontmatter, dynamic arguments, bash execution. | Skip |
| **Hook Development** | "create a hook", "add a PreToolUse hook" | Guide for creating event-driven hooks. Hook types, events, security best practices. | Skip |
| **Skill Development** | "create a skill", "add a skill to plugin" | Guide for creating effective skills. SKILL.md structure, progressive disclosure, bundled resources. | Skip |
| **MCP Integration** | "add MCP server", "integrate MCP", "configure MCP in plugin" | Integrating MCP servers into plugins. Server types (stdio, SSE, HTTP, WebSocket), auth patterns. | **Consider** — DCI already has a custom MCP server; useful reference for extending it |
| **Plugin Settings** | "plugin settings", "store plugin configuration" | Documents .local.md pattern for plugin-specific config. Reading/parsing settings from hooks/commands. | Skip |
| **Plugin Structure** | "create a plugin", "scaffold a plugin" | Plugin directory structure, manifest, component organization, auto-discovery. | Skip |

### hookify Plugin (1 skill)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **Writing Hookify Rules** | "create a hookify rule", "write a hook rule" | Guide for creating markdown-based hook rules with YAML frontmatter. Event types: bash, file, stop, prompt. | **Consider** — if hookify is installed, this teaches how to use it effectively |

### playground Plugin (1 skill)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **playground** | "make a playground", "explorer", "interactive tool" | Creates self-contained interactive HTML playgrounds with controls and live preview. Templates: design, data, concept-map, diff review, code-map. | Skip — not relevant to DCI workflow |

### frontend-design Plugin (1 skill) — INSTALLED

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **frontend-design** | "build web components", "pages", "applications" | Creates distinctive, production-grade frontend interfaces. Design thinking process, typography, color, motion, spatial composition. Anti-generic-AI-aesthetics philosophy. | **INSTALLED** — actively used for the DCI dashboard |

### claude-md-management Plugin (1 skill)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **claude-md-improver** | "check CLAUDE.md", "audit CLAUDE.md", "improve CLAUDE.md" | Audits and improves CLAUDE.md files. Discovery → Assessment → Report → Updates. Can write to CLAUDE.md after approval. | **YES** — DCI should maintain high-quality CLAUDE.md for agent context |

### claude-code-setup Plugin (1 skill)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **claude-automation-recommender** | "automation recommendations", "optimize Claude Code setup" | Analyzes codebase, recommends hooks, subagents, skills, plugins, MCP servers. Read-only — doesn't create files. | **YES** — run once to get tailored recommendations for DCI |

### stripe Plugin (1 skill)

| Skill | Triggers | Summary | DCI Swarm? |
|-------|----------|---------|------------|
| **stripe-best-practices** | "implementing payment processing", "checkout flows" | Best practices for Stripe integrations. Checkout vs Payment Element, subscriptions, Connect platforms. | Skip — no Stripe integration |

---

## BuildWithClaude Agents

117 agents across 11 packages. All **free/OSS** (MIT licensed). These are prompt-based personas with domain expertise — no external services required.

Install marketplace: `claude plugin marketplace add davepoon/buildwithclaude`

### agents-development-architecture (11 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **backend-architect** | RESTful APIs, microservice boundaries, database schemas. Reviews for scalability and performance. | **YES** — directly relevant to FastAPI backend architecture |
| **frontend-developer** | Next.js with React, shadcn/ui, Tailwind CSS. App Router, Server/Client Components. | **Consider** — React expertise useful, but DCI uses plain React not Next.js |
| **graphql-architect** | Schema design, resolvers, federation. DataLoader, subscriptions, N+1 optimization. | Skip — DCI uses REST |
| **directus-developer** | Directus CMS: data models, permissions, workflows, custom extensions. | Skip — not using Directus |
| **drupal-developer** | Drupal CMS: modules, themes, content architecture. PHP/Symfony. | Skip |
| **ios-developer** | Native iOS with Swift/SwiftUI. Core Data, networking, app lifecycle. | Skip |
| **laravel-vue-developer** | Full-stack Laravel + Vue3. PHP, Pinia, TailwindCSS. | Skip |
| **mobile-developer** | Cross-platform React Native or Flutter. Offline sync, push notifications. | Skip |
| **nextjs-app-router-developer** | Next.js 14+ App Router with Server Components, PPR, caching. | Skip — not using Next.js |
| **react-performance-optimization** | React performance: rendering, bundle analysis, memory, Core Web Vitals. | **Consider** — useful if dashboard performance becomes an issue |
| **wordpress-developer** | WordPress: themes, plugins, Gutenberg, WooCommerce. PHP/MySQL. | Skip |

### agents-language-specialists (12 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **python-expert** | Idiomatic Python: decorators, generators, async/await, type hints. Python 3.8-3.12, pytest, PEP 8. | **YES** — core backend language |
| **typescript-expert** | Advanced TypeScript: generics, utility types, strict compiler, type-safe implementations. | **YES** — core frontend language |
| **sql-expert** | Complex SQL, query optimization, schema design, index recommendations. | **Consider** — useful for SQLAlchemy/Alembic work |
| **javascript-developer** | Modern ES6+, async patterns, Node.js, performance optimization. | **Consider** — overlaps with typescript-expert |
| **golang-expert** | Idiomatic Go: goroutines, channels, interfaces, composition. | Skip |
| **rust-expert** | Ownership, lifetimes, type safety, zero-cost abstractions. | Skip |
| **java-developer** | Modern Java: streams, concurrency, Spring Boot, JVM optimization. | Skip |
| **ruby-expert** | Idiomatic Ruby: SOLID, service objects, RSpec. | Skip |
| **rails-expert** | Rails 8.0+: Hotwire, RESTful APIs, Sidekiq. | Skip |
| **php-developer** | Type-safe PHP 8.0+, PSR standards, PHPUnit, PHPStan. | Skip |
| **cpp-engineer** | Modern C++: RAII, smart pointers, template metaprogramming. | Skip |
| **c-developer** | Systems programming: memory management, hardware interaction, low-level optimization. | Skip |

### agents-quality-security (15 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **code-reviewer** | Code quality, security, maintainability. Issues, warnings, improvements. | **YES** — general purpose review |
| **debugger** | Systematic investigation, root cause analysis. Minimal corrective code, prevention strategies. | **YES** — essential for debugging agent orchestration issues |
| **error-detective** | Log analysis, pattern recognition, error correlation. Remediation steps. | **YES** — useful for DCI's multi-agent logging |
| **security-auditor** | OWASP compliance, JWT, OAuth2, CORS, CSP, encryption. Audit reports. | **YES** — DCI handles auth and agent permissions |
| **test-automator** | Test pyramid: unit, integration, e2e. CI pipelines, mocking strategies. | **YES** — supports DCI's TDD approach |
| **performance-engineer** | Profiling, load testing, caching strategies. Optimization recommendations. | **Consider** — relevant when scaling agent workloads |
| **api-security-audit** | OWASP API Security Top 10. Authentication, authorization vulnerability reports. | **Consider** — FastAPI endpoints should be audited |
| **architect-review** | Architectural consistency, SOLID, dependency analysis, pattern adherence. | **Consider** — useful for maintaining DCI's layered architecture |
| **incident-responder** | Production incidents: rapid stabilization, diagnostics, retrospectives. | Skip — not in production yet |
| **mcp-server-architect** | MCP server design: transport layers, session management, TypeScript/Python SDK. | **Consider** — DCI has a custom MCP server |
| **mcp-testing-engineer** | MCP server testing: JSON schema, protocol compliance, security testing. | **Consider** — if MCP server testing is needed |
| **mcp-security-auditor** | MCP security: auth, RBAC, compliance (SOC 2, GDPR, HIPAA). | Skip — overkill for current stage |
| **dx-optimizer** | Developer experience: tooling, setup, workflows, IDE config. | Skip — DCI already has custom CLI |
| **command-expert** | CLI design, argument parsing, task automation. | Skip — DCI CLI is already built |
| **review-agent** | QA for knowledge management systems. Report verification, metadata validation. | Skip — wrong domain |

### agents-infrastructure-operations (8 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **database-optimization** | Query analysis, indexing strategies, connection pooling. | **Consider** — relevant when migrating to PostgreSQL |
| **database-optimizer** | SQL optimization, N+1 problems, caching strategies, migration scripts. | **Consider** — overlaps with above |
| **database-admin** | Backup strategies, replication, user access, disaster recovery. | Skip — premature for SQLite stage |
| **cloud-architect** | AWS/Azure/GCP, Terraform IaC, multi-region, cost optimization. | Skip — no cloud deployment yet |
| **deployment-engineer** | CI/CD, Docker, Kubernetes, GitHub Actions. | Skip — no CI/CD yet |
| **devops-troubleshooter** | Production debugging, log analysis, incident response. | Skip — not in production |
| **network-engineer** | DNS, SSL/TLS, CDN, load balancers, traffic analysis. | Skip |
| **terraform-specialist** | Terraform modules, state management, multi-environment. | Skip |

### agents-data-ai (11 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **prompt-engineer** | LLM prompt optimization: chain-of-thought, few-shot, A/B variations, performance metrics. | **YES** — DCI's agent prompts are critical to system behavior |
| **ai-engineer** | LLM applications, RAG systems, agent orchestration. LangChain, vector databases. | **YES** — directly relevant to DCI's agent orchestration engine |
| **task-decomposition-expert** | Break complex goals into actionable tasks. Tool combinations, ChromaDB integration. | **YES** — DCI decomposes shows into movements/sets/segments |
| **context-manager** | Multi-agent context preservation, memory management. Required for 10k+ token projects. | **Consider** — DCI already has context snapshots, but this could inform improvements |
| **search-specialist** | Advanced web search, multi-source verification, fact-checking. | **Consider** — useful for research phases |
| **data-engineer** | ETL pipelines, Spark, Airflow, Kafka. | Skip — wrong domain |
| **data-scientist** | SQL, BigQuery, data insights. | Skip |
| **ml-engineer** | ML pipelines, model serving, TensorFlow/PyTorch. | Skip |
| **mlops-engineer** | MLflow, Kubeflow, experiment tracking. | Skip |
| **hackathon-ai-strategist** | Hackathon strategy and AI solution ideation. | Skip |
| **llms-maintainer** | Generates llms.txt roadmap files for AI crawlers. | Skip |

### agents-specialized-domains (41 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **api-documenter** | OpenAPI/Swagger specs, SDK generation, interactive docs. | **YES** — FastAPI endpoints need documentation |
| **agent-expert** | Creates and optimizes Claude Code agents. Prompt engineering, domain modeling. | **Consider** — could inform DCI's own agent definitions |
| **project-supervisor-orchestrator** | Multi-step workflow coordination, sequential agent management, data completeness. | **Consider** — similar to DCI's ED/PC roles |
| **legacy-modernizer** | Refactors legacy code, strangler fig pattern, backward compatibility. | **Consider** — useful if major refactors needed |
| **report-generator** | Research findings into comprehensive reports. Academic standards, citations. | **Consider** — useful for DCI show reports |
| **research-coordinator** | Plans and coordinates complex research tasks across specialists. | **Consider** — similar to DCI's coordination patterns |
| **markdown-syntax-formatter** | CommonMark/GFM formatting fixes. | Skip — trivial |
| **academic-research-synthesizer** | Literature reviews, trend analysis, source quality. | Skip — wrong domain |
| **academic-researcher** | ArXiv, PubMed, Google Scholar searches. | Skip |
| **audio-quality-controller** | Audio analysis with FFMPEG. Loudness normalization. | Skip |
| **comprehensive-researcher** | Cross-verified research reports. | Skip — generic |
| **connection-agent** | Knowledge management: entity relationships, orphaned notes. | Skip — Obsidian-specific |
| **data-analyst** | Quantitative analysis, trend analysis, benchmarking. | Skip |
| **docusaurus-expert** | Docusaurus v2/v3 configuration and theming. | Skip |
| **episode-orchestrator** | Episode-based workflow coordination. | Skip — podcast-specific |
| **game-developer** | Unity, Unreal, Godot game mechanics. | Skip |
| **market-research-analyst** | Competitive landscapes, market opportunities. | Skip |
| **mcp-deployment-orchestrator** | MCP server production deployment, K8s, autoscaling. | Skip — premature |
| **mcp-expert** | MCP server configurations, auth, error handling. | **Consider** — overlaps with mcp-server-architect |
| **mcp-registry-navigator** | MCP server discovery and evaluation. | Skip |
| **metadata-agent** | Frontmatter standardization, hierarchical tags. | Skip — Obsidian-specific |
| **moc-agent** | Maps of Content generation for knowledge management. | Skip — Obsidian-specific |
| **ocr-grammar-fixer** | OCR artifact cleanup. | Skip |
| **ocr-quality-assurance** | OCR validation and accuracy verification. | Skip |
| **podcast-content-analyzer** | Transcript analysis for viral moments. | Skip |
| **podcast-metadata-specialist** | Show notes, chapter markers, SEO. | Skip |
| **podcast-transcriber** | Audio/video transcript extraction. | Skip |
| **podcast-trend-scout** | Tech topic identification for podcasts. | Skip |
| **query-clarifier** | Research query ambiguity detection. | Skip |
| **research-brief-generator** | Structured research briefs from queries. | Skip |
| **research-orchestrator** | Multi-agent research coordination. | Skip |
| **research-synthesizer** | Cross-source finding consolidation. | Skip |
| **seo-podcast-optimizer** | Podcast SEO optimization. | Skip |
| **tag-agent** | Tag taxonomy normalization. | Skip — Obsidian-specific |
| **technical-researcher** | GitHub repo analysis, API spec review. | Skip — generic |
| **text-comparison-validator** | Text accuracy comparison. | Skip |
| **timestamp-precision-specialist** | Frame-accurate timestamp extraction. | Skip |
| **twitter-ai-influencer-manager** | Twitter engagement around AI leaders. | Skip |
| **url-context-validator** | URL validation and content evaluation. | Skip |
| **url-link-extractor** | URL cataloging within codebases. | Skip |
| **visual-analysis-ocr** | Text extraction from PNG images. | Skip |

### agents-design-experience (2 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **accessibility-specialist** | WCAG 2.1 AA/AAA: ARIA, keyboard nav, screen readers. | **Consider** — if dashboard accessibility matters |
| **ui-ux-designer** | User research, design systems, prototyping. | Skip — have frontend-design plugin |

### agents-business-finance (4 agents)

| Agent | Summary | DCI Swarm? |
|-------|---------|------------|
| **business-analyst** | Metrics, KPIs, financial modeling. | Skip — wrong domain |
| **legal-advisor** | Privacy policies, GDPR, CCPA compliance. | Skip |
| **payment-integration** | Stripe, PayPal, checkout flows. | Skip |
| **quant-analyst** | Financial models, backtesting, portfolio optimization. | Skip |

### agents-crypto-trading (5 agents)

All skip — wrong domain. Covers: crypto-analyst, crypto-trader, defi-strategist, arbitrage-bot, crypto-risk-manager.

### agents-blockchain-web3 (2 agents)

All skip — wrong domain. Covers: blockchain-developer, hyperledger-fabric-developer.

### agents-sales-marketing (6 agents)

All skip — wrong domain. Covers: content-marketer, customer-support, risk-manager, sales-automator, social-media-clip-creator, social-media-copywriter.

---

## BuildWithClaude Skills

26 skills across 4 skill packages + 1 monitoring tool. All **free/OSS** (MIT licensed).

### all-skills Package (26 skills bundled)

#### Document Processing (10 skills)

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **pdf** | PDF manipulation: extract text/tables, create, merge/split, handle forms. Uses pypdf, pdfplumber, reportlab, poppler-utils. | **Free** — OSS Python libs | **Consider** — useful if DCI generates reports |
| **xlsx** | Spreadsheet creation/editing with formulas, formatting, analysis. Zero-error mandate for financial models. Uses pandas, openpyxl. | **Free** — OSS Python libs | **Consider** — useful for scoresheet exports |
| **docx** | Word doc creation/editing with tracked changes and comments. Uses pandoc, docx-js. | **Free** — OSS tools | Skip — not generating Word docs |
| **pptx** | PowerPoint creation/editing. HTML-to-PPTX workflow. | **Free** — OSS tools | Skip |
| **image-enhancer** | Image quality improvement: resolution, sharpness, artifact reduction. | **Free** — local processing | Skip |
| **canvas-design** | Visual art in PNG/PDF using design philosophy documents. | **Free** | Skip |
| **artifacts-builder** | Single-file HTML artifacts using React, Tailwind, shadcn/ui. | **Free** | Skip — for claude.ai artifacts, not CC |
| **brand-guidelines** | Anthropic brand colors/typography for artifacts. | **Free** | Skip — DCI has its own Kilties palette |
| **theme-factory** | 10 professional themes for slides/docs/reports. | **Free** | Skip |
| **changelog-generator** | Auto-generates user-facing changelogs from git commits. Categories: features, improvements, bugs, security. | **Free** | **YES** — useful for DCI release notes |

#### Business Productivity (10 skills)

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **file-organizer** | Intelligent file/folder organization. Duplicate detection, structure suggestions, automated cleanup. | **Free** | **Consider** — useful for project cleanup |
| **developer-growth-analysis** | Analyzes ~/.claude/history.jsonl for coding patterns and improvement areas. Sends Slack report. | **Free** (Slack optional) | **Consider** — interesting for self-improvement |
| **content-research-writer** | Research-backed content writing with citations, hooks, outline iteration. Voice preservation. | **Free** | Skip — wrong domain |
| **domain-name-brainstormer** | Domain name generation with availability checking across TLDs. | **Free** | Skip |
| **competitive-ads-extractor** | Competitor ad analysis from Facebook/LinkedIn ad libraries. | **Free** | Skip |
| **internal-comms** | Internal communication templates: status reports, 3P updates, newsletters. | **Free** | Skip |
| **invoice-organizer** | Invoice/receipt organization for tax prep. PDF reading, renaming, categorization. | **Free** | Skip |
| **lead-research-assistant** | Lead identification and contact strategy generation. | **Free** | Skip |
| **meeting-insights-analyzer** | Meeting transcript behavioral analysis. Communication patterns, conflict avoidance. | **Free** | Skip |
| **raffle-winner-picker** | Cryptographically secure random winner selection from lists/spreadsheets. | **Free** | Skip |

#### Development/Code (3 skills)

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **mcp-builder** | Guide for creating MCP servers. 4-phase process: research → implementation → review → evaluation. | **Free** | **Consider** — DCI has a custom MCP server, this could improve it |
| **skill-creator** | Guide for creating Claude Code skills. SKILL.md structure, progressive disclosure, packaging. | **Free** | Skip — not building CC skills |
| **webapp-testing** | Testing local web apps with Playwright. Server lifecycle management, reconnaissance pattern. | **Free** | **YES** — directly useful for testing DCI's React frontend |

#### Creative/Collaboration (2 skills)

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **skill-share** | Creates skills and shares on Slack via Rube. | **Free** (Slack required) | Skip |
| **slack-gif-creator** | Animated GIF creation for Slack. Composable animation primitives, size optimization. | **Free** | Skip |

#### Video (1 skill)

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **video-downloader** | YouTube video download with quality/format options. Uses yt-dlp. | **Free** | Skip |

### nextjs-expert Package (5 skills)

All Next.js-specific. DCI uses plain React, not Next.js. **All skip.**

| Skill | Summary |
|-------|---------|
| **app-router** | Next.js App Router: file conventions, dynamic routes, layouts, loading states, error boundaries. |
| **server-components** | React Server Components in Next.js: server vs client, composition patterns, data fetching. |
| **route-handlers** | Next.js API routes: HTTP methods, request/response handling, streaming, CORS. |
| **server-actions** | Next.js form handling: mutations, useFormState, useFormStatus, cache revalidation. |
| **auth-patterns** | NextAuth.js v5, Clerk, Lucia, JWT, middleware protection, RBAC. |

### frontend-design-pro Package (6 skills)

Advanced frontend design. Requires **Claude in Chrome** browser integration for full functionality.

| Skill | Summary | Cost | DCI Swarm? |
|-------|---------|------|------------|
| **design-wizard** | Interactive 7-step design workflow: discovery → research → moodboard → aesthetic → color/typography → code → review. | **Free** (browser optional) | **Consider** — if doing major dashboard redesign |
| **color-curator** | Color palette selection from Coolors or curated fallbacks. 60-30-10 rule, contrast requirements, Tailwind config output. | **Free** (browser optional) | **Consider** — DCI has Kilties palette but could refine it |
| **typography-selector** | Font selection from Google Fonts. Aesthetic-based pairings, Tailwind config output. Avoids overused fonts (Inter, Roboto). | **Free** (browser optional) | **Consider** — if refining dashboard typography |
| **trend-researcher** | UI/UX trend research from Dribbble, Awwwards, Behance. Pattern recognition, color/layout analysis. | **Free** (browser required) | Skip — DCI has established aesthetic |
| **moodboard-creator** | Visual moodboard creation from collected inspiration. Iterative refinement (max 3-4 cycles). | **Free** (browser optional) | Skip |
| **inspiration-analyzer** | Website design analysis: colors, typography, layouts, patterns. Multi-viewport capture. | **Free** (browser required) | Skip |

### obsidian-skills Package (3 skills)

All Obsidian-specific. **All skip** — DCI doesn't use Obsidian.

| Skill | Summary |
|-------|---------|
| **obsidian-markdown** | Obsidian Flavored Markdown: wikilinks, embeds, callouts, properties, tags, block references. |
| **obsidian-bases** | Obsidian Bases (.base files): YAML views, filters, formulas, summaries. Table/card/list/map views. |
| **json-canvas** | JSON Canvas (.canvas): nodes, edges, groups for mind maps, flowcharts, project boards. |

### claude-hud (Monitoring Tool)

| Tool | Summary | Cost | DCI Swarm? |
|------|---------|------|------------|
| **claude-hud** | Real-time statusline: context usage bar, tool activity spinners, agent tracking, task progress. Requires Node.js 18+. | **Free** | **YES** — visibility into Claude Code session activity during development |

---

## Recommendations for DCI Swarm

### Tier 1: Install — High Value, Free, Directly Relevant

**Official Marketplace Agents:**

| Agent | Plugin | Why |
|-------|--------|-----|
| **code-explorer** | feature-dev | Trace execution paths through DCI's layered agent hierarchy |
| **code-architect** | feature-dev | Design new features respecting DCI's corps/segment/rep architecture |
| **code-reviewer** (feature-dev) | feature-dev | Catch bugs across Python and TypeScript with confidence scoring |
| **pr-test-analyzer** | pr-review-toolkit | Ensure PRs have meaningful behavioral test coverage |
| **silent-failure-hunter** | pr-review-toolkit | Critical — silent failures in agent orchestration cause cascading issues |

**BuildWithClaude Agents:**

| Agent | Package | Why |
|-------|---------|-----|
| **python-expert** | agents-language-specialists | Core backend language expertise |
| **typescript-expert** | agents-language-specialists | Core frontend language expertise |
| **debugger** | agents-quality-security | Systematic root cause analysis for agent orchestration bugs |
| **prompt-engineer** | agents-data-ai | DCI's agent prompts drive system behavior — optimization is critical |
| **ai-engineer** | agents-data-ai | Directly relevant to DCI's LLM agent orchestration |
| **task-decomposition-expert** | agents-data-ai | DCI decomposes shows → movements → sets → segments — this agent understands that pattern |
| **api-documenter** | agents-specialized-domains | FastAPI endpoints need OpenAPI documentation |

**Official Marketplace Skills:**

| Skill | Plugin | Why |
|-------|--------|-----|
| **claude-md-improver** | claude-md-management | Maintain high-quality CLAUDE.md for project context |
| **claude-automation-recommender** | claude-code-setup | Run once — get tailored recommendations for DCI |

**BuildWithClaude Skills:**

| Skill | Package | Why |
|-------|---------|-----|
| **webapp-testing** | all-skills | Test DCI's React frontend with Playwright patterns |
| **changelog-generator** | all-skills | Auto-generate release notes from git history |
| **claude-hud** | claude-hud | Real-time visibility into context usage and agent activity |

### Tier 2: Consider — Moderate Value

**Agents:**

| Agent | Source | Caveat |
|-------|--------|--------|
| **code-simplifier** | Official (code-simplifier) | May conflict with DCI's domain-specific patterns |
| **code-reviewer** (opus) | Official (pr-review-toolkit) | Higher quality but uses opus model tokens |
| **backend-architect** | BuildWithClaude | Focused on REST/microservices — relevant to FastAPI |
| **security-auditor** | BuildWithClaude | OWASP, JWT, OAuth2 — relevant to DCI auth |
| **test-automator** | BuildWithClaude | Supports TDD approach |
| **error-detective** | BuildWithClaude | Log analysis for multi-agent systems |
| **sql-expert** | BuildWithClaude | SQLAlchemy/Alembic optimization |
| **agent-expert** | BuildWithClaude | Could inform DCI's own agent definition patterns |
| **project-supervisor-orchestrator** | BuildWithClaude | Similar coordination patterns to DCI's ED/PC |
| **database-optimization** | BuildWithClaude | Useful when migrating to PostgreSQL |
| **mcp-server-architect** | BuildWithClaude | DCI has custom MCP server |
| **conversation-analyzer** | Official (hookify) | Identify behaviors to prevent with hooks |

**Skills:**

| Skill | Source | Caveat |
|-------|--------|--------|
| **mcp-builder** | BuildWithClaude | Could improve DCI's existing MCP server |
| **pdf** | BuildWithClaude | If DCI generates report PDFs |
| **xlsx** | BuildWithClaude | If exporting scoresheets |
| **design-wizard** | BuildWithClaude | Major dashboard redesign only |
| **MCP Integration** | Official (plugin-dev) | Reference for extending DCI's MCP server |
| **file-organizer** | BuildWithClaude | Project cleanup utility |

### Tier 3: Skip

**Wrong stack:** All Next.js skills (5), all non-Python/TS language agents (8), all framework-specific agents (Directus, Drupal, Laravel, WordPress, iOS, mobile)

**Wrong domain:** All crypto/blockchain agents (7), all sales/marketing agents (6), all business/finance agents (4), all podcast agents (5), all Obsidian skills (3), all OCR agents (3)

**Premature:** cloud-architect, deployment-engineer, devops-troubleshooter, network-engineer, terraform-specialist, incident-responder, mcp-deployment-orchestrator

**Plugin development (not building plugins):** All plugin-dev skills (7), agent-creator, plugin-validator, skill-reviewer, agent-sdk-verifier-ts, agent-sdk-verifier-py

**Redundant with installed or Tier 1:** ui-ux-designer (have frontend-design), brand-guidelines (have Kilties palette), artifacts-builder (for claude.ai not CC)

---

## Install Commands

```bash
# Official marketplace — plugins containing recommended agents/skills
claude plugin install feature-dev
claude plugin install pr-review-toolkit
claude plugin install claude-md-management
claude plugin install claude-code-setup

# BuildWithClaude marketplace
claude plugin marketplace add davepoon/buildwithclaude
claude plugin install agents-language-specialists@buildwithclaude
claude plugin install agents-quality-security@buildwithclaude
claude plugin install agents-data-ai@buildwithclaude
claude plugin install agents-specialized-domains@buildwithclaude
claude plugin install all-skills@buildwithclaude
claude plugin install claude-hud@buildwithclaude
```

> **Note:** Installing `agents-specialized-domains` brings all 41 agents. Only ~3 are recommended (api-documenter, agent-expert, project-supervisor-orchestrator). The rest are inert unless invoked. Same for `all-skills` — installs 26 but only a few are relevant. This is acceptable since unused agents/skills have zero runtime cost.
