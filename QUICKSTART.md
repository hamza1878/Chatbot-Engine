# 🚀 Quick Start Guide - Moviroo AI Chatbot

Get up and running in 5 minutes!

## Option 1: Quick Local Setup (Recommended for Development)

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### Steps

1. **Clone and Enter Directory**
```bash
git clone <repository-url>
cd moviroo-chatbot
```

2. **Run Automated Setup**
```bash
chmod +x start.sh
./start.sh
```

The script will:
- Create virtual environment
- Install dependencies
- Set up database
- Create sample dataset
- Start the server

3. **Access the API**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Option 2: Docker (Recommended for Production)

### Prerequisites
- Docker
- Docker Compose

### Steps

1. **Clone and Configure**
```bash
git clone <repository-url>
cd moviroo-chatbot
cp .env.example .env
```

2. **Start Everything**
```bash
docker-compose up -d
```

3. **Initialize Data**
```bash
# Wait 30 seconds for services to start
sleep 30

# Load dataset
curl -X POST http://localhost:8000/admin/load-dataset

# Build index
curl -X POST http://localhost:8000/admin/rebuild-index
```

4. **Access Services**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PgAdmin: http://localhost:5050 (admin@moviroo.com / admin)

## First API Call

Test the chatbot with your first message:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I book a ride?",
    "user_id": "user123"
  }'
```

Expected response:
```json
{
  "response": "Booking a ride is easy: 1) Open the Moviroo app...",
  "confidence_score": 0.89,
  "detected_language": "en",
  "detected_category": "booking",
  "response_time_ms": 145
}
```

## Test All Features

Run the comprehensive test suite:

```bash
python test_api.py
```

This will test:
- ✅ Health checks
- ✅ Dataset loading
- ✅ Multilingual chat (EN/FR/AR/Franco-Arabic)
- ✅ Ticket management
- ✅ Feedback system
- ✅ Statistics

## Next Steps

1. **Customize Dataset**: Edit `data/dataset.csv` with your Q&A
2. **Configure Settings**: Update `.env` for your needs
3. **Monitor Performance**: Check `/stats` endpoint
4. **Integrate with Flutter**: Use the API endpoints in your app

## Common Commands

```bash
# Check health
curl http://localhost:8000/health

# View stats
curl http://localhost:8000/stats

# Rebuild index after adding data
curl -X POST http://localhost:8000/admin/rebuild-index

# Stop Docker services
docker-compose down

# View logs
docker-compose logs -f chatbot-api
```

## Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres
```

### Model Download Taking Long
The first run downloads the multilingual model (~500MB). This is normal and happens once.

### Low Confidence Scores
1. Load the dataset: `POST /admin/load-dataset`
2. Rebuild index: `POST /admin/rebuild-index`
3. Ensure questions in dataset match your use case

## Support

- 📚 Full documentation: See README.md
- 🐛 Issues: Open a GitHub issue
- 💬 Questions: Check API docs at /docs

---

**Ready to go!** Start building your intelligent chatbot integration. 🎉
