# Contributing to Aegis

Thank you for your interest in contributing to Aegis! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Aegis.git`
3. Set up the development environment (see below)

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for backend development)
- Node.js 20+ (for frontend development)
- Git

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt -r requirements-dev.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## Making Changes

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guidelines below

3. Write tests for new functionality

4. Ensure all tests pass:
   ```bash
   # Backend
   cd backend && pytest tests/ -v

   # Frontend
   cd frontend && npm run lint && npm run type-check
   ```

5. Commit your changes with a clear message:
   ```bash
   git commit -m "feat: add new feature description"
   ```

## Code Style

### Python (Backend)

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Run linting before committing:
  ```bash
  cd backend
  ruff check app tests
  black app tests
  mypy app --ignore-missing-imports
  ```

### TypeScript (Frontend)

- Follow the existing ESLint configuration
- Use TypeScript strict mode
- Run linting before committing:
  ```bash
  cd frontend
  npm run lint
  npm run type-check
  ```

### Commit Messages

We follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## Pull Request Process

1. Update the README.md if your changes affect usage
2. Ensure all CI checks pass
3. Request review from maintainers
4. Address any feedback
5. Once approved, your PR will be merged

### PR Guidelines

- Keep PRs focused on a single change
- Include a clear description of what and why
- Link related issues
- Add screenshots for UI changes

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=html  # with coverage
```

### Frontend Tests

```bash
cd frontend
npm run lint
npm run type-check
npm run build
```

## Reporting Issues

When reporting issues, please include:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node version, etc.)
- Relevant logs or error messages

## Feature Requests

We welcome feature requests! Please:

- Check existing issues first to avoid duplicates
- Describe the use case and expected behavior
- Explain why this would be valuable

## Questions?

Open an issue for any questions or concerns. We're happy to help!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
