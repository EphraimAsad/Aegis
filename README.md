# Aegis

**Research-focused agentic AI wrapper for academia**

Aegis is a model-agnostic orchestration system that helps researchers conduct comprehensive academic literature reviews. It handles project intake, clarification, source search, organization, storage, retrieval, and long-running research jobs.

## Current Status

**Phase**: 1 - Scaffold and Core Architecture (In Progress)

| Phase | Status |
|-------|--------|
| Phase 0: Bootstrap | Complete |
| Phase 1: Scaffold | In Progress |
| Phase 2: Provider Abstraction | Pending |
| Phase 3: Project Intake | Pending |
| Phase 4: Source Adapters | Pending |
| Phase 5: Document Processing | Pending |
| Phase 6: Long-running Jobs | Pending |
| Phase 7: Retrieval & Exports | Pending |
| Phase 8: Polish & Testing | Pending |

## Features (Planned)

- **Multi-provider support**: Ollama (default), OpenAI, Anthropic, Gemini
- **Academic source coverage**: OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed
- **Project workflow**: Intake, clarification, search, organize, retrieve
- **Long-running jobs**: Background research tasks with progress tracking
- **Document processing**: Chunking, embeddings, summarization, evidence extraction
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

## API Endpoints

### Health Check
- `GET /api/v1/health` - Backend health status with DB/Redis connectivity

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
│   │   └── providers/ # LLM provider abstraction
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
