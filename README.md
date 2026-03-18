# Aegis

**Research-focused agentic AI wrapper for academia**

Aegis is a model-agnostic orchestration system that helps researchers conduct comprehensive academic literature reviews. It handles project intake, clarification, source search, organization, storage, retrieval, and long-running research jobs.

## Current Status

**Phase**: 6 - Long-running Jobs (Next)

| Phase | Status |
|-------|--------|
| Phase 0: Bootstrap | Complete |
| Phase 1: Scaffold | Complete |
| Phase 2: Provider Abstraction | Complete |
| Phase 3: Project Intake | Complete |
| Phase 4: Source Adapters | Complete |
| Phase 5: Document Processing | Complete |
| Phase 6: Long-running Jobs | Next |
| Phase 7: Retrieval & Exports | Pending |
| Phase 8: Polish & Testing | Pending |

## Features

### Implemented
- **Multi-provider support**: Ollama (default), OpenAI, Anthropic
- **Provider abstraction**: Unified interface for chat, completion, embeddings
- **Health monitoring**: Provider health checks and status
- **Project management**: Create, update, delete research projects
- **Clarification workflow**: AI-generated questions to refine research scope
- **Scope definition**: Keywords, disciplines, date ranges, document types
- **Academic source adapters**: OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed
- **Multi-source search**: Concurrent search with result deduplication
- **Normalized paper schema**: Consistent format across all sources
- **Document storage**: Document and chunk models with full metadata
- **Chunking strategies**: Fixed-size, sentence, paragraph, and section-based
- **Embedding generation**: Batch processing with provider abstraction
- **Summarization**: Multi-level summaries with key findings extraction
- **Evidence extraction**: Claim identification with confidence scoring
- **Auto-tagging**: AI-powered and keyword-based document tagging
- **Semantic search**: Vector similarity search across document chunks

### Planned
- **Additional providers**: Gemini support
- **Long-running jobs**: Background research tasks with progress tracking
- **Export options**: CSV, JSON, Markdown, annotated bibliography

## Architecture

```
Frontend (Next.js 14+)     Backend (FastAPI)
        |                         |
        +---- REST API -----------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
         PostgreSQL            Redis             Ollama
         (pgvector)           (Queue)        (Local LLM)
```

### Tech Stack

**Frontend**
- Next.js 14+ with App Router
- TypeScript
- Tailwind CSS
- shadcn/ui components

**Backend**
- FastAPI
- Python 3.11+
- SQLAlchemy 2.0 (async)
- Alembic migrations
- Pydantic v2

**Infrastructure**
- PostgreSQL with pgvector
- Redis + Celery
- Docker Compose
- Ollama (local LLM default)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Aegis
```

2. Copy environment files:
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

3. Start all services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

See `.env.example` files in root, `backend/`, and `frontend/` directories for all configuration options.

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | See .env.example |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `OLLAMA_BASE_URL` | Ollama API endpoint | http://localhost:11434 |
| `DEFAULT_PROVIDER` | Default LLM provider | ollama |
| `DEFAULT_MODEL` | Default model name | llama2 |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |

### Provider Configuration

Aegis uses a provider abstraction layer that supports multiple AI providers:

- **Ollama** (default): Local LLM inference, no API key required
- **OpenAI**: Requires `OPENAI_API_KEY` environment variable
- **Anthropic**: Requires `ANTHROPIC_API_KEY` environment variable

Set the `DEFAULT_PROVIDER` to choose which provider to use by default. Providers are only registered if their API keys are configured (except Ollama, which is always available).

## API Endpoints

### Health Check
- `GET /api/v1/health` - Backend health status with DB/Redis connectivity
- `GET /api/v1/health/live` - Kubernetes liveness probe
- `GET /api/v1/health/ready` - Kubernetes readiness probe

### Providers
- `GET /api/v1/providers` - List all registered AI providers
- `GET /api/v1/providers/health` - Check health of all providers
- `GET /api/v1/providers/{name}` - Get provider details and capabilities
- `GET /api/v1/providers/{name}/models` - List available models for a provider
- `POST /api/v1/providers/chat` - Send chat completion request
- `POST /api/v1/providers/embed` - Generate text embeddings

### Projects
- `POST /api/v1/projects` - Create a new research project
- `GET /api/v1/projects` - List all projects (with pagination)
- `GET /api/v1/projects/{id}` - Get project details
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project
- `PUT /api/v1/projects/{id}/scope` - Update project scope
- `PUT /api/v1/projects/{id}/status` - Update project status
- `POST /api/v1/projects/{id}/clarify` - Start clarification (generates AI questions)
- `GET /api/v1/projects/{id}/questions` - Get clarification questions
- `PUT /api/v1/projects/{id}/questions/{qid}` - Answer a question
- `GET /api/v1/projects/{id}/clarification-status` - Get clarification progress

### Academic Search
- `GET /api/v1/search/sources` - List available academic sources
- `GET /api/v1/search/sources/health` - Check health of all sources
- `GET /api/v1/search` - Multi-source search with deduplication
- `GET /api/v1/search/doi/{doi}` - Look up paper by DOI
- `GET /api/v1/search/source/{name}` - Search single source

### Documents
- `POST /api/v1/documents` - Create a document manually
- `POST /api/v1/documents/add-paper` - Add paper from search results
- `POST /api/v1/documents/bulk-add` - Add multiple papers
- `GET /api/v1/documents` - List documents (with filters)
- `GET /api/v1/documents/{id}` - Get document details
- `PATCH /api/v1/documents/{id}` - Update document
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents/{id}/chunks` - Get document chunks
- `POST /api/v1/documents/{id}/process` - Process document (chunk, embed, summarize)
- `POST /api/v1/documents/{id}/summarize` - Generate summary
- `POST /api/v1/documents/{id}/auto-tag` - Auto-generate tags
- `GET /api/v1/documents/{id}/related` - Find related documents
- `POST /api/v1/documents/search/semantic` - Semantic search
- `GET /api/v1/documents/stats/{project_id}` - Document statistics

### Academic Sources

| Source | Features |
|--------|----------|
| **OpenAlex** | Free, comprehensive, inverted index abstracts |
| **Crossref** | DOI metadata, citation counts |
| **Semantic Scholar** | AI features, influential citations |
| **arXiv** | Preprints, full text access |
| **PubMed** | Biomedical focus, MeSH terms |

## Project Structure

```
Aegis/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── core/      # Core utilities
│   │   ├── db/        # Database setup
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   ├── providers/ # LLM provider abstraction
│   │   └── sources/   # Academic source adapters
│   ├── alembic/       # Database migrations
│   └── tests/         # Backend tests
├── frontend/          # Next.js frontend
│   ├── app/           # App Router pages
│   ├── components/    # React components
│   ├── lib/           # Utilities
│   └── types/         # TypeScript types
├── docker-compose.yml # Service orchestration
└── README.md
```

## Contributing

This project is under active development. See `Currentprogress.txt` for current status and `Masterprompt.txt` for full specifications.

## License

[License TBD]
