# 📁 Project Structure - Moviroo AI Chatbot

Complete directory structure and file descriptions.

```
moviroo-chatbot/
│
├── 📄 README.md                    # Main documentation
├── 📄 QUICKSTART.md                # Quick start guide
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment variables template
├── 📄 .gitignore                   # Git ignore rules
├── 📄 Dockerfile                   # Docker image definition
├── 📄 docker-compose.yml           # Multi-container setup
├── 📄 config.py                    # Configuration management
├── 📄 main.py                      # FastAPI application entry
├── 🚀 start.sh                     # Automated startup script
├── 🧪 test_api.py                  # API testing suite
│
├── 📂 api/                         # API Routes & Schemas
│   ├── __init__.py
│   ├── schemas.py                  # Pydantic request/response models
│   ├── chat.py                     # Chat endpoints
│   ├── tickets.py                  # Ticket management endpoints
│   ├── feedback.py                 # Feedback endpoints
│   └── health.py                   # Health & stats endpoints
│
├── 📂 database/                    # Database Layer
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy ORM models
│   │                               # - Ticket
│   │                               # - KnowledgeBase
│   │                               # - Conversation
│   │                               # - ConversationMessage
│   │                               # - Feedback
│   │                               # - Analytics
│   └── connection.py               # Async database connection
│
├── 📂 models/                      # AI Models & Vector Store
│   ├── __init__.py
│   ├── embedding.py                # SentenceTransformers service
│   │                               # - Multilingual embeddings
│   │                               # - Franco-Arabic handling
│   │                               # - Text preprocessing
│   ├── vector_store.py             # FAISS vector search
│   │                               # - Index management
│   │                               # - Similarity search
│   │                               # - Incremental updates
│   ├── faiss_index.bin             # (Generated) FAISS index file
│   └── faiss_metadata.pkl          # (Generated) Vector metadata
│
├── 📂 services/                    # Business Logic Layer
│   ├── __init__.py
│   ├── chatbot.py                  # Main chatbot service
│   │                               # - Message processing
│   │                               # - Language detection
│   │                               # - Category detection
│   │                               # - Response generation
│   ├── ticket.py                   # Ticket service
│   │                               # - Ticket CRUD
│   │                               # - Ticket learning
│   │                               # - Statistics
│   └── feedback.py                 # Feedback service
│                                   # - Feedback collection
│                                   # - Analysis
│                                   # - Improvement tracking
│
├── 📂 pipelines/                   # Data Pipelines
│   ├── __init__.py
│   └── data_loader.py              # Dataset & index loading
│                                   # - CSV loading
│                                   # - Ticket integration
│                                   # - Index rebuilding
│
├── 📂 data/                        # Data Files
│   ├── .gitkeep
│   └── dataset.csv                 # (Generated) Initial Q&A dataset
│                                   # Columns: question, answer, category, language
│
├── 📂 logs/                        # Application Logs
│   ├── .gitkeep
│   └── moviroo.log                 # (Generated) Application log file
│
└── 📂 tests/                       # Unit & Integration Tests
    ├── __init__.py
    └── (test files)
```

## Key Components

### 🎯 Entry Points

- **main.py**: FastAPI application with all routes and middleware
- **start.sh**: Automated setup and startup script
- **test_api.py**: Comprehensive API testing

### 🔌 API Layer (api/)

Routes are organized by functionality:

- **chat.py**: Real-time chat, conversation history
- **tickets.py**: Support ticket CRUD operations
- **feedback.py**: User feedback collection and analysis
- **health.py**: System health, stats, admin tools
- **schemas.py**: Pydantic models for validation

### 💾 Database Layer (database/)

SQLAlchemy async ORM:

- **models.py**: Database schema definitions
  - Tickets (support requests)
  - KnowledgeBase (Q&A dataset)
  - Conversations (chat sessions)
  - Messages (individual exchanges)
  - Feedback (user ratings)
  - Analytics (metrics)

- **connection.py**: Database connection pooling and session management

### 🧠 AI Models (models/)

Semantic search and embeddings:

- **embedding.py**: 
  - SentenceTransformers multilingual model
  - Text preprocessing
  - Franco-Arabic handling
  - Batch embedding generation

- **vector_store.py**:
  - FAISS index management
  - Similarity search
  - Incremental learning
  - Index persistence

### 🔧 Services Layer (services/)

Core business logic:

- **chatbot.py**: Main AI logic
  - Message processing
  - Language/category detection
  - Response generation
  - Confidence scoring

- **ticket.py**: Ticket management
  - Create/read/update tickets
  - Learning from resolved tickets
  - Statistics tracking

- **feedback.py**: Feedback processing
  - Collect user feedback
  - Analyze satisfaction
  - Identify improvements

### 🔄 Data Pipelines (pipelines/)

Data processing workflows:

- **data_loader.py**:
  - Load CSV datasets
  - Import to database
  - Build FAISS index
  - Incremental updates

### 📊 Data Files (data/)

- **dataset.csv**: Initial Q&A knowledge base
  - Pre-defined questions and answers
  - Multiple languages
  - Categorized content

### 🐳 Deployment Files

- **Dockerfile**: Container image definition
- **docker-compose.yml**: Multi-service orchestration
- **.env.example**: Environment configuration template

## Data Flow

```
User Request
     ↓
FastAPI Endpoint (api/)
     ↓
Service Layer (services/)
     ↓
┌────────────────┬────────────────┐
│                │                │
Embedding       Database        Vector Store
(models/)       (database/)     (models/)
     │                │                │
     └────────────────┴────────────────┘
                  ↓
            Response Generation
                  ↓
              JSON Response
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (not in repo) |
| `.env.example` | Template for .env |
| `config.py` | Settings management with Pydantic |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Files to exclude from Git |

## Generated/Runtime Files

Files created during runtime:

- `data/dataset.csv` - Sample Q&A dataset (auto-generated if missing)
- `models/faiss_index.bin` - FAISS vector index
- `models/faiss_metadata.pkl` - Vector metadata
- `logs/moviroo.log` - Application logs
- `.env` - Your environment configuration

## File Size Estimates

```
Source Code:      ~50 KB
Dependencies:     ~500 MB (first install)
Model Download:   ~500 MB (first run)
FAISS Index:      ~10 MB per 10k vectors
Database:         Variable based on usage
Logs:             Rotates at 500 MB
```

## Customization Points

To customize for your use case:

1. **Dataset**: Edit `data/dataset.csv`
2. **Categories**: Update `services/chatbot.py` → `detect_category()`
3. **Languages**: Add to Franco-Arabic mappings in `models/embedding.py`
4. **Thresholds**: Adjust in `.env` → `SIMILARITY_THRESHOLD`
5. **Endpoints**: Add routes in `api/`

## Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes to relevant files
# - API: api/
# - Logic: services/
# - Models: models/
# - Database: database/

# 3. Test locally
python test_api.py

# 4. Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# 5. Create pull request
```

---

**This structure ensures**: Modularity, Scalability, Maintainability, Testability
