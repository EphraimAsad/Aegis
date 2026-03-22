# Aegis

[![CI](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/EphraimAsad/Aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Research-focused agentic AI wrapper for academia**

Aegis is a model-agnostic orchestration system that helps researchers conduct comprehensive academic literature reviews. It handles project intake, clarification, source search, organization, storage, retrieval, and long-running research jobs.

## Current Status

**Phase**: 9 - Production Ready

| Phase | Status |
|-------|--------|
| Phase 0: Bootstrap | Complete |
| Phase 1: Scaffold | Complete |
| Phase 2: Provider Abstraction | Complete |
| Phase 3: Project Intake | Complete |
| Phase 4: Source Adapters | Complete |
| Phase 5: Document Processing | Complete |
| Phase 6: Long-running Jobs | Complete |
| Phase 6.5: Agent Memory | Complete |
| Phase 7: Retrieval & Exports | Complete |
| Phase 8: Polish & Testing | Complete |
| Phase 8.5: Integration | Complete |
| **Phase 9: Production Ready** | **Complete** |

### System Components

| Component | Status | Notes |
|-----------|--------|-------|
| Source Adapters (5) | **Working** | OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed |
| ChunkingService | **Working** | Fixed-size, sentence, paragraph, section strategies |
| EmbeddingService | **Working** | Batch processing with provider abstraction |
| SummarizationService | **Working** | Multi-level summaries with key findings |
| Research Worker Task | **Working** | Full agentic workflow: search → collect → process → synthesize |
| Document Processing | **Working** | Automatic chunking, embedding, summarization, tagging |
| Frontend/Backend Types | **Aligned** | TypeScript types match Pydantic schemas |
| Export System | **Working** | CSV, JSON, Markdown, BibTeX with error handling |
| Analytics | **Working** | Project-level statistics and trends |

## Features

### Implemented
- **Multi-provider support**: Ollama (default), OpenAI, Anthropic, Google/Gemini
- **Provider abstraction**: Unified interface for chat, completion, embeddings, streaming
- **Health monitoring**: Provider health checks and status
- **Real-time updates**: WebSocket support for live job progress
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
- **Background jobs**: Celery-based task queue with Redis
- **Research workflow**: Automated search, collection, and processing
- **Job tracking**: Real-time progress, statistics, and history
- **Batch processing**: Process multiple documents concurrently
- **Agent memory**: Progress logs for long-running jobs with checkpoint/resume capability
- **Job checkpointing**: Persistent state snapshots for fault-tolerant job execution
- **Export functionality**: CSV, JSON, Markdown, BibTeX, and annotated bibliography formats
- **Citation generation**: APA, Chicago, MLA, Harvard, IEEE, and BibTeX citation styles
- **Advanced search**: Filters by year, author, journal, tags, citations with faceted results
- **Analytics dashboard**: Publication trends, top authors, keyword analysis, source distribution

### Planned
- **Library organization**: Collections and folders
- **Team collaboration**: Multi-user support

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

3. Pull the default LLM model (if using Ollama):
```bash
ollama pull llama3.2:3b
```

4. Start all services:
```bash
docker-compose up -d
```

5. Access the application:
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
| `DEFAULT_MODEL` | Default model name | llama3.2:3b |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |
| `GOOGLE_API_KEY` | Google AI API key (optional) | - |

### Provider Configuration

Aegis uses a provider abstraction layer that supports multiple AI providers:

| Provider | API Key Required | Models |
|----------|------------------|--------|
| **Ollama** (default) | No (local) | llama2, mistral, codellama, etc. |
| **OpenAI** | `OPENAI_API_KEY` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-3-5-sonnet, claude-3-opus |
| **Google/Gemini** | `GOOGLE_API_KEY` | gemini-1.5-pro, gemini-1.5-flash |

#### Switching Providers

To change the default AI provider, update your `.env` file:

```bash
# Use Ollama (default, no API key needed)
DEFAULT_PROVIDER=ollama
DEFAULT_MODEL=llama3.2:3b

# Use OpenAI
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Use Anthropic
DEFAULT_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Use Google Gemini
DEFAULT_PROVIDER=google
DEFAULT_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=...
```

After changing providers, restart the backend:
```bash
docker compose restart backend
```

Verify the provider is active:
```bash
curl http://localhost:8000/api/v1/providers | jq
```

### Rebuilding After Code Changes

If you modify the code, you need to rebuild the Docker containers:

```bash
# Rebuild and restart all services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Or rebuild specific services
docker-compose build --no-cache backend celery-worker frontend
docker-compose up -d
```

Check container health:
```bash
docker-compose ps
docker-compose logs backend --tail=20
```

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
- `POST /api/v1/documents/advanced-search` - Advanced search with filters and facets
- `GET /api/v1/documents/stats/{project_id}` - Document statistics

### Exports
- `POST /api/v1/exports` - Export documents (CSV, JSON, Markdown, BibTeX)
- `POST /api/v1/exports/download` - Download export as file
- `GET /api/v1/exports/preview` - Preview export content
- `GET /api/v1/exports/formats` - List available export formats

### Citations
- `POST /api/v1/citations/format` - Format citations for documents
- `GET /api/v1/citations/document/{id}` - Get all citation formats for a document
- `GET /api/v1/citations/styles` - List available citation styles

### Analytics
- `GET /api/v1/analytics/overview` - Project overview statistics
- `GET /api/v1/analytics/dashboard` - Full analytics dashboard
- `GET /api/v1/analytics/trends` - Publication trends over time
- `GET /api/v1/analytics/authors` - Top authors statistics
- `GET /api/v1/analytics/keywords` - Keyword and tag analysis

### Jobs
- `GET /api/v1/jobs` - List jobs (with filters)
- `GET /api/v1/jobs/stats` - Job statistics
- `GET /api/v1/jobs/{id}` - Get job details
- `POST /api/v1/jobs/{id}/cancel` - Cancel a job
- `POST /api/v1/jobs/{id}/retry` - Retry a failed job
- `POST /api/v1/jobs/research` - Start research job
- `POST /api/v1/jobs/batch-process` - Start batch processing
- `GET /api/v1/jobs/{id}/progress` - Get job progress log entries
- `GET /api/v1/jobs/{id}/progress/summary` - Get aggregated progress summary
- `POST /api/v1/jobs/{id}/resume` - Resume job from checkpoint
- `GET /api/v1/jobs/project/{id}/active` - Get active jobs
- `GET /api/v1/jobs/project/{id}/history` - Get job history

### WebSocket
- `WS /api/v1/ws/jobs` - Real-time job status updates

Connect via WebSocket and send JSON messages:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/jobs');

// Subscribe to a specific job
ws.send(JSON.stringify({ action: 'subscribe', job_id: 123 }));

// Receive real-time updates
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Job update:', update);
};
```

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
│   │   ├── sources/   # Academic source adapters
│   │   └── worker/    # Celery tasks and jobs
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

## Using Local Ollama

To use a local Ollama installation instead of Docker's:

1. Create `docker-compose.override.yml`:
```yaml
services:
  ollama:
    profiles:
      - disabled
  backend:
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - DEFAULT_MODEL=llama3.2:3b
  celery-worker:
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - DEFAULT_MODEL=llama3.2:3b
```

2. Ensure Ollama is running locally: `ollama serve`

3. Start Docker services: `docker-compose up -d`

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `cd backend && pytest tests/ -v`
5. Run linting: `cd backend && ruff check app tests && black --check app tests`
6. Commit your changes: `git commit -m 'feat: add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Style

- **Backend**: Python code follows [Ruff](https://github.com/astral-sh/ruff) and [Black](https://github.com/psf/black) formatting
- **Frontend**: TypeScript/React follows ESLint configuration
- All code must pass CI checks before merging

## Security

If you discover a security vulnerability, please open an issue with the `security` label instead of a public disclosure.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
