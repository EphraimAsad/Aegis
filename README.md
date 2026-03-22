# Aegis

[![CI](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**AI-powered academic literature review platform**

## What is Aegis?

Aegis automates the time-consuming process of academic literature review. Enter your research question, and Aegis searches across multiple academic databases, collects relevant papers, generates summaries, extracts key findings, and synthesizes insights - all with AI assistance.

Built for researchers who want to spend less time searching and more time discovering.

## Key Features

- **Multi-source search** - Query OpenAlex, Crossref, Semantic Scholar, arXiv, and PubMed simultaneously with automatic deduplication
- **AI-powered analysis** - Automatic summarization, key findings extraction, and evidence claim identification
- **Flexible AI providers** - Use local models (Ollama), OpenAI, Anthropic, or Google Gemini
- **Smart organization** - Auto-tagging, semantic search, and related document discovery
- **Export anywhere** - CSV, JSON, Markdown, BibTeX, and formatted citations (APA, MLA, Chicago, etc.)
- **Real-time progress** - WebSocket updates for long-running research jobs
- **Checkpoint & resume** - Fault-tolerant job execution that picks up where it left off

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) [Ollama](https://ollama.ai) for local AI models

### Get Running in 3 Steps

```bash
# 1. Clone and configure
git clone https://github.com/EphraimAsad/Aegis.git
cd Aegis
cp .env.example .env

# 2. (Optional) Pull a local model
ollama pull llama3.2:3b

# 3. Start everything
docker-compose up -d
```

Open [http://localhost:3000](http://localhost:3000) to start your first research project.

## How It Works

1. **Create a project** - Enter your research question and objectives
2. **Refine scope** - AI asks clarifying questions to narrow the search
3. **Search & collect** - Aegis searches academic databases and collects papers
4. **Process & analyze** - Documents are chunked, embedded, summarized, and tagged
5. **Explore & export** - Search semantically, discover themes, and export findings

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2.0 |
| Database | PostgreSQL with pgvector |
| Queue | Redis + Celery |
| AI | Ollama (default), OpenAI, Anthropic, Google |

## Configuration

### Using Different AI Providers

Aegis defaults to local Ollama, but supports cloud providers:

```bash
# OpenAI
DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Anthropic
DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
DEFAULT_PROVIDER=google
GOOGLE_API_KEY=...
```

See `.env.example` for all configuration options.

## API Documentation

Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) when running locally.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Run backend tests
cd backend && pytest tests/ -v

# Run linting
cd backend && ruff check app && black --check app
cd frontend && npm run lint
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with care for the research community.
