# 🤖 Code Reviewer Agent

An **autonomous AI-powered code review agent** that analyzes GitHub Pull Requests using advanced language models and provides comprehensive code quality insights.

[![Tests](https://img.shields.io/badge/tests-75%20passing-green)](.)
[![Coverage](https://img.shields.io/badge/coverage-41%25-yellow)](.)
[![Python](https://img.shields.io/badge/python-3.13-blue)](.)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-green)](.)

## 🚀 Features

- **🧠 AI-Powered Analysis**: Uses OpenAI/Ollama models for intelligent code review
- **🔄 Async Processing**: Celery-based task queue for scalable analysis
- **📊 Comprehensive Reports**: Security, performance, style, and maintainability insights  
- **🐙 GitHub Integration**: Direct PR analysis with GitHub API
- **🗄️ Persistent Storage**: PostgreSQL database with SQLModel ORM
- **⚡ Redis Caching**: Fast caching and message brokering
- **🧪 Test Coverage**: 75+ tests with 41% coverage
- **📈 REST API**: FastAPI with automatic OpenAPI documentation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │    │  Celery Worker  │    │   AI Agents     │
│                 │    │                 │    │                 │
│ • REST Endpoints│────▶• Async Tasks    │────▶• LangGraph Flow │
│ • Validation    │    │ • PR Processing │    │ • Code Analysis │
│ • Error Handling│    │ • Status Updates│    │ • LLM Integration│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │  GitHub API     │
│                 │    │                 │    │                 │
│ • Task Storage  │    │ • Message Queue │    │ • PR Data       │
│ • Results Cache │    │ • Result Cache  │    │ • File Content  │
│ • Analysis Data │    │ • Session Store │    │ • Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Technology Stack

### **Backend**
- **FastAPI** - Modern async web framework
- **SQLModel** - Type-safe database ORM 
- **Celery** - Distributed task queue
- **Redis** - Caching and message broker
- **PostgreSQL** - Primary database
- **UV** - Fast Python package manager

### **AI & Analysis**
- **LangGraph** - AI workflow orchestration
- **OpenAI/Ollama** - Language model providers
- **PyGithub** - GitHub API integration
- **Custom Tools** - Code analysis utilities

### **Infrastructure**
- **Docker Compose** - Local development
- **Alembic** - Database migrations
- **Loguru** - Structured logging
- **Pytest** - Testing framework

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Docker & Docker Compose**
- **UV** package manager
- **GitHub Token** (optional)
- **OpenAI API Key** (optional)

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd code_reviewer_agent

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/code_review
REDIS_URL=redis://localhost:6379/0

# Optional: GitHub Integration
GITHUB_TOKEN=your_github_token_here

# Optional: AI Analysis
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your-secret-key-here
```

### 3. Start Services

```bash
# Start infrastructure
docker-compose up -d

# Run database migrations
uv run alembic upgrade head

# Start FastAPI server
uv run uvicorn app.main:app --reload

# Start Celery worker (new terminal)
uv run celery -A app.tasks.celery_app worker --loglevel=info
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## 📖 API Usage

### Submit PR for Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-pr" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/owner/repo",
    "pr_number": 123,
    "github_token": "optional_token"
  }'
```

**Response:**
```json
{
  "task_id": "uuid-task-id",
  "status": "pending",
  "message": "Analysis task queued successfully"
}
```

### Check Task Status

```bash
curl "http://localhost:8000/api/v1/status/uuid-task-id"
```

### Get Analysis Results

```bash
curl "http://localhost:8000/api/v1/results/uuid-task-id"
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_models/

# Run integration tests
uv run pytest tests/integration/
```

### Code Quality

```bash
# Format code
uvx ruff format

# Lint code  
uvx ruff check

# Type checking
uv run mypy app
```

### Database Operations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

## 📂 Project Structure

```
code_reviewer_agent/
├── app/
│   ├── agents/          # AI workflow logic
│   │   ├── ai_workflow.py
│   │   ├── analyzer.py
│   │   └── tools/       # Analysis tools
│   ├── api/             # FastAPI routes
│   │   └── v1/endpoints/
│   ├── config/          # Configuration management
│   ├── models/          # Database & API models
│   ├── services/        # Business logic
│   │   ├── github.py
│   │   └── llm_service.py
│   ├── tasks/           # Celery tasks
│   └── utils/           # Utilities
├── tests/               # Test suite
│   ├── fixtures/        # Test fixtures
│   ├── integration/     # Integration tests
│   └── unit/           # Unit tests
├── migrations/          # Database migrations
└── docs/               # Documentation
```

## ⚙️ Configuration

Configuration is managed via `config.toml` with environment variable substitution:

```toml
[llm]
provider = "openai"  # or "ollama"
model = "gpt-4"
openai_api_key = "$OPENAI_API_KEY"

[agent]
max_analysis_time = 300
analysis_languages = ["python", "javascript", "typescript"]

[github]
timeout = 30
max_files_per_pr = 50
```

## 🔍 Analysis Features

### **Code Issues Detected**
- 🔒 **Security vulnerabilities**
- 🐛 **Potential bugs**
- ⚡ **Performance problems**
- 🎨 **Style violations**
- 🔧 **Maintainability concerns**

### **Supported Languages**
- Python, JavaScript, TypeScript
- Java, Go, Rust, C/C++
- PHP, Ruby, C#, Kotlin
- And more...

### **AI Capabilities**
- Context-aware analysis
- Intelligent prioritization
- Detailed explanations
- Fix suggestions

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Write tests for new features
- Follow existing code style
- Update documentation
- Ensure all tests pass

## 📊 Monitoring

### **Logs**
- Application logs: `logs/app.log`
- Structured JSON logging with Loguru
- Configurable log levels

### **Health Checks**
- API health: `GET /health`
- Database connectivity
- Redis connectivity
- Celery worker status

### **Metrics** (Future)
- Analysis success rates
- Processing times
- Error frequencies
- API usage statistics

## 🔒 Security

- API key authentication
- Environment-based secrets
- Input validation with Pydantic
- Rate limiting on endpoints
- Secure GitHub token handling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent async framework
- **LangGraph** for AI workflow orchestration
- **OpenAI** for language model capabilities
- **GitHub** for comprehensive API access

---

## 📞 Support

- 📖 **Documentation**: Check `/docs` endpoint
- 🐛 **Issues**: Create GitHub issues
- 💬 **Discussions**: Use GitHub discussions
- 📧 **Contact**: [Your contact information]

---

**Happy coding! 🚀**
