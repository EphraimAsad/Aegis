# Aegis

[![CI](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**AI-powered academic literature review platform**

---

## What is Aegis?

Aegis automates the time-consuming process of academic literature review. Enter your research question, and Aegis searches across multiple academic databases, collects relevant papers, generates summaries, extracts key findings, and synthesizes insights - all with AI assistance.

**Built for researchers who want to spend less time searching and more time discovering.**

---

## Screenshots

> *Screenshots coming soon - run locally to see Aegis in action!*

```
+------------------+     +------------------+     +------------------+
|   Dashboard      |     |  Project View    |     |   Documents      |
|                  |     |                  |     |                  |
|  [Projects: 5]   |     |  Research Q:     |     |  [Paper 1] ★★★  |
|  [Jobs: 2]       |     |  "ML in bio..."  |     |  [Paper 2] ★★   |
|  [Status: ✓]     |     |                  |     |  [Paper 3] ★★★  |
|                  |     |  [Start Research]|     |                  |
+------------------+     +------------------+     +------------------+
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Browser                               │
│                        localhost:3000                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js 14)                          │
│   • Dashboard          • Project Management      • Document Viewer  │
│   • Search Interface   • Analytics               • Export Tools     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                             │
│   • API Endpoints      • Service Layer          • Provider Layer    │
│   • Job Orchestration  • Document Processing    • Source Adapters   │
└───────┬─────────────────────┬─────────────────────────┬─────────────┘
        │                     │                         │
        ▼                     ▼                         ▼
┌───────────────┐    ┌───────────────┐    ┌─────────────────────────┐
│  PostgreSQL   │    │     Redis     │    │      AI Providers       │
│  + pgvector   │    │   + Celery    │    │  ┌─────────────────────┐│
│               │    │               │    │  │ Ollama (default)    ││
│ • Documents   │    │ • Job Queue   │    │  │ OpenAI              ││
│ • Embeddings  │    │ • Caching     │    │  │ Anthropic           ││
│ • Projects    │    │ • Pub/Sub     │    │  │ Google Gemini       ││
└───────────────┘    └───────────────┘    │  └─────────────────────┘│
                                          └─────────────────────────┘
                                                      │
                                                      ▼
                              ┌─────────────────────────────────────┐
                              │        Academic Sources             │
                              │  OpenAlex │ Crossref │ Semantic S.  │
                              │   arXiv   │  PubMed  │              │
                              └─────────────────────────────────────┘
```

---

## Key Features

### Multi-Source Academic Search
- **OpenAlex** - Free, comprehensive coverage with inverted index abstracts
- **Crossref** - DOI metadata and citation counts
- **Semantic Scholar** - AI-enhanced features and influential citation tracking
- **arXiv** - Preprint access with full text
- **PubMed** - Biomedical literature with MeSH terms

All sources are searched concurrently with automatic deduplication.

### AI-Powered Document Analysis
- **Summarization** - Multi-level summaries (brief, standard, detailed)
- **Key Findings** - Automatic extraction of main contributions
- **Evidence Claims** - Identification of claims with confidence scores
- **Auto-Tagging** - AI and keyword-based document classification
- **Semantic Search** - Find related documents using vector similarity

### Flexible AI Providers
| Provider | Local/Cloud | Best For |
|----------|-------------|----------|
| **Ollama** | Local | Privacy, no API costs |
| **OpenAI** | Cloud | GPT-4 quality |
| **Anthropic** | Cloud | Claude reasoning |
| **Google** | Cloud | Gemini capabilities |

### Export & Citations
- **Formats**: CSV, JSON, Markdown, BibTeX
- **Citation Styles**: APA, MLA, Chicago, Harvard, IEEE
- **Annotated Bibliography**: Export with summaries included

### Robust Job System
- Real-time WebSocket progress updates
- Checkpoint and resume for long jobs
- Automatic retry on failures
- Detailed progress logs

---

## Use Cases

### Graduate Student Literature Review
> "I need to review 100+ papers on machine learning in drug discovery"

Aegis searches all major databases, collects papers, generates summaries, and helps you identify key themes and gaps.

### Lab Research Survey
> "Our lab needs a comprehensive survey of CRISPR delivery methods"

Create a project, refine the scope through AI questions, then let Aegis build your literature corpus with auto-generated tags and semantic search.

### Grant Proposal Background
> "I need to establish the state of the art for my NSF proposal"

Aegis exports formatted citations and synthesizes findings into coherent narratives.

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) [Ollama](https://ollama.ai) for local AI models

### Get Running

```bash
# Clone the repository
git clone https://github.com/EphraimAsad/Aegis.git
cd Aegis

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# (Optional) Pull a local AI model
ollama pull llama3.2:3b

# Start all services
docker-compose up -d
```

### Access Points
| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Backend** | http://localhost:8000 |

---

## Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   1. Create  │     │  2. Clarify  │     │  3. Search   │
│    Project   │────▶│    Scope     │────▶│   Sources    │
│              │     │              │     │              │
│ "How does    │     │ AI asks:     │     │ OpenAlex,    │
│  ML affect   │     │ - Time range?│     │ Crossref,    │
│  biology?"   │     │ - Subdomain? │     │ PubMed...    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
        ┌────────────────────────────────────────┘
        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  4. Process  │     │  5. Analyze  │     │  6. Export   │
│  Documents   │────▶│  & Explore   │────▶│   Results    │
│              │     │              │     │              │
│ - Chunk      │     │ - Summaries  │     │ - CSV/JSON   │
│ - Embed      │     │ - Themes     │     │ - BibTeX     │
│ - Summarize  │     │ - Gaps       │     │ - Citations  │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Configuration

### Environment Variables

```bash
# AI Provider (choose one)
DEFAULT_PROVIDER=ollama          # Local (default)
DEFAULT_PROVIDER=openai          # OpenAI
DEFAULT_PROVIDER=anthropic       # Anthropic
DEFAULT_PROVIDER=google          # Google Gemini

# API Keys (only needed for cloud providers)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: Custom model
DEFAULT_MODEL=llama3.2:3b        # For Ollama
DEFAULT_MODEL=gpt-4o             # For OpenAI
DEFAULT_MODEL=claude-3-5-sonnet  # For Anthropic
```

See `.env.example` for all options.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy 2.0, Pydantic v2 |
| **Database** | PostgreSQL 16 with pgvector extension |
| **Queue** | Redis 7, Celery |
| **AI** | Ollama, OpenAI, Anthropic, Google Gemini |
| **Infrastructure** | Docker, Docker Compose |

---

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check logs
docker-compose logs backend --tail=50

# Ensure database is ready
docker-compose logs postgres
```

**Ollama not connecting**
```bash
# If using local Ollama, ensure it's running
ollama serve

# Pull a model if none exist
ollama pull llama3.2:3b
```

**Frontend shows API errors**
```bash
# Verify backend is healthy
curl http://localhost:8000/api/v1/health
```

### Reset Everything
```bash
docker-compose down -v
docker-compose up -d
```

---

## API Documentation

Full interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Backend development
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
ruff check app && black app

# Frontend development
cd frontend
npm install
npm run lint && npm run type-check
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with care for the research community.</strong>
</p>
