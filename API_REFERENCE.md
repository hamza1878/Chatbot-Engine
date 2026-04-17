# 📡 API Endpoint Reference - Moviroo AI Chatbot

Complete reference for all API endpoints with examples.

## 🔗 Base URL

```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

## 📋 Table of Contents

- [Chat Endpoints](#chat-endpoints)
- [Ticket Endpoints](#ticket-endpoints)
- [Feedback Endpoints](#feedback-endpoints)
- [Health & Stats Endpoints](#health--stats-endpoints)
- [Admin Endpoints](#admin-endpoints)

---

## 💬 Chat Endpoints

### POST /chat

Send a message and get AI response.

**Request:**
```json
{
  "message": "My payment failed. What should I do?",
  "user_id": "user123",
  "conversation_id": "conv-abc-123",  // Optional
  "language": "en"  // Optional, auto-detected
}
```

**Response (200 OK):**
```json
{
  "response": "If your payment failed, please check: 1) Your card has sufficient funds...",
  "confidence_score": 0.89,
  "detected_language": "en",
  "detected_category": "payment",
  "matched_source": "knowledge_base",
  "matched_id": 1,
  "response_time_ms": 145,
  "conversation_id": "conv-abc-123",
  "timestamp": "2024-04-16T10:30:00Z",
  "suggestions": [
    "Try rephrasing your question",
    "Create a support ticket"
  ],
  "alternatives": [
    {
      "answer": "You can also contact your bank...",
      "score": 0.75,
      "category": "payment"
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I book a ride?",
    "user_id": "user123"
  }'
```

---

### GET /chat/history/{conversation_id}

Get conversation history.

**Parameters:**
- `conversation_id` (path): Conversation ID
- `limit` (query): Max messages (default: 20)

**Response (200 OK):**
```json
{
  "conversation_id": "conv-abc-123",
  "user_id": "user123",
  "total_messages": 5,
  "avg_confidence": 0.85,
  "messages": [
    {
      "user_message": "How do I book a ride?",
      "bot_response": "Booking a ride is easy...",
      "confidence_score": 0.92,
      "detected_language": "en",
      "detected_category": "booking",
      "timestamp": "2024-04-16T10:30:00Z"
    }
  ]
}
```

**Curl Example:**
```bash
curl http://localhost:8000/chat/history/conv-abc-123?limit=10
```

---

### DELETE /chat/conversation/{conversation_id}

End a conversation.

**Parameters:**
- `conversation_id` (path): Conversation ID
- `user_satisfaction` (query): Rating 1-5 (optional)

**Response (200 OK):**
```json
{
  "message": "Conversation ended successfully",
  "conversation_id": "conv-abc-123",
  "total_messages": 5,
  "avg_confidence": 0.85
}
```

**Curl Example:**
```bash
curl -X DELETE http://localhost:8000/chat/conversation/conv-abc-123?user_satisfaction=5
```

---

## 🎫 Ticket Endpoints

### POST /ticket

Create a support ticket.

**Request:**
```json
{
  "user_id": "user123",
  "question": "Driver charged me extra after cancelling the ride",
  "category": "payment",  // Optional
  "language": "en"  // Optional, default: en
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "ticket_id": "TICKET-ABC12345",
  "user_id": "user123",
  "question": "Driver charged me extra after cancelling the ride",
  "answer": null,
  "category": "payment",
  "language": "en",
  "status": "open",
  "priority": "medium",
  "created_at": "2024-04-16T10:30:00Z",
  "updated_at": null,
  "resolved_at": null,
  "resolution_time_minutes": null
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/ticket \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "question": "App keeps crashing when I try to book",
    "category": "bug"
  }'
```

---

### GET /ticket/{ticket_id}

Get ticket details.

**Response (200 OK):**
```json
{
  "id": 1,
  "ticket_id": "TICKET-ABC12345",
  "user_id": "user123",
  "question": "Driver charged me extra...",
  "answer": "We apologize for the inconvenience...",
  "category": "payment",
  "language": "en",
  "status": "resolved",
  "priority": "high",
  "created_at": "2024-04-16T10:30:00Z",
  "updated_at": "2024-04-16T11:00:00Z",
  "resolved_at": "2024-04-16T11:00:00Z",
  "resolution_time_minutes": 30
}
```

**Curl Example:**
```bash
curl http://localhost:8000/ticket/TICKET-ABC12345
```

---

### PUT /ticket/{ticket_id}

Update ticket (admin only).

**Request:**
```json
{
  "answer": "We apologize for the inconvenience. The extra charge has been refunded.",
  "status": "resolved",
  "priority": "high",
  "admin_id": "admin001"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "ticket_id": "TICKET-ABC12345",
  "status": "resolved",
  ...
}
```

**Curl Example:**
```bash
curl -X PUT http://localhost:8000/ticket/TICKET-ABC12345 \
  -H "Content-Type: application/json" \
  -d '{
    "answer": "Issue resolved",
    "status": "resolved",
    "admin_id": "admin001"
  }'
```

---

### GET /ticket/user/{user_id}

Get user's tickets.

**Parameters:**
- `user_id` (path): User ID
- `limit` (query): Max tickets (default: 10, max: 100)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "ticket_id": "TICKET-ABC12345",
    "status": "resolved",
    ...
  },
  {
    "id": 2,
    "ticket_id": "TICKET-DEF67890",
    "status": "open",
    ...
  }
]
```

**Curl Example:**
```bash
curl http://localhost:8000/ticket/user/user123?limit=5
```

---

### GET /ticket

Get open tickets (admin only).

**Parameters:**
- `category` (query): Filter by category
- `priority` (query): Filter by priority
- `limit` (query): Max tickets (default: 50, max: 100)

**Curl Example:**
```bash
curl http://localhost:8000/ticket?category=payment&priority=high&limit=20
```

---

### GET /ticket/stats/overview

Get ticket statistics (admin only).

**Response (200 OK):**
```json
{
  "total_tickets": 150,
  "by_status": {
    "open": 25,
    "in_progress": 15,
    "resolved": 100,
    "closed": 10
  },
  "avg_resolution_time_minutes": 45.5,
  "by_category": {
    "payment": 50,
    "booking": 40,
    "account": 30,
    "bug": 20,
    "other": 10
  }
}
```

**Curl Example:**
```bash
curl http://localhost:8000/ticket/stats/overview
```

---

## 💬 Feedback Endpoints

### POST /feedback

Submit user feedback.

**Request:**
```json
{
  "conversation_id": "conv-abc-123",
  "rating": 5,
  "feedback_type": "helpful",
  "user_message": "How do I book a ride?",
  "bot_response": "Booking a ride is easy: 1) Open the app...",
  "comment": "Very helpful response!",
  "message_id": 1,  // Optional
  "user_id": "user123"  // Optional
}
```

**Feedback Types:**
- `helpful` - Response was helpful
- `not_helpful` - Response was not helpful
- `wrong_answer` - Incorrect information
- `incomplete_answer` - Missing information
- `good_response` - Excellent response
- `needs_improvement` - Could be better

**Response (201 Created):**
```json
{
  "id": 1,
  "conversation_id": "conv-abc-123",
  "rating": 5,
  "feedback_type": "helpful",
  "comment": "Very helpful response!",
  "created_at": "2024-04-16T10:30:00Z",
  "is_processed": false
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv-abc-123",
    "rating": 5,
    "feedback_type": "helpful",
    "user_message": "Payment issue",
    "bot_response": "Try these steps...",
    "user_id": "user123"
  }'
```

---

### GET /feedback/stats

Get feedback statistics (admin only).

**Parameters:**
- `days` (query): Days to analyze (default: 30, max: 365)

**Response (200 OK):**
```json
{
  "total_feedback": 250,
  "average_rating": 4.2,
  "by_rating": {
    "1": 10,
    "2": 15,
    "3": 30,
    "4": 95,
    "5": 100
  },
  "by_type": {
    "helpful": 150,
    "not_helpful": 50,
    "wrong_answer": 20,
    "incomplete_answer": 15,
    "good_response": 10,
    "needs_improvement": 5
  },
  "processed_count": 180,
  "processing_rate": 72.0
}
```

**Curl Example:**
```bash
curl http://localhost:8000/feedback/stats?days=7
```

---

### GET /feedback/low-rated

Get low-rated feedback (admin only).

**Parameters:**
- `max_rating` (query): Max rating (default: 2, range: 1-5)
- `limit` (query): Max results (default: 20, max: 100)

**Curl Example:**
```bash
curl http://localhost:8000/feedback/low-rated?max_rating=2&limit=10
```

---

### GET /feedback/analysis/improvements

Analyze improvement opportunities (admin only).

**Parameters:**
- `days` (query): Days to analyze (default: 7, max: 30)

**Response (200 OK):**
```json
{
  "total_low_rated": 25,
  "analysis_period_days": 7,
  "top_issues": [
    {
      "issue": "payment",
      "count": 10
    },
    {
      "issue": "booking",
      "count": 8
    },
    {
      "issue": "account",
      "count": 7
    }
  ],
  "needs_attention": true
}
```

**Curl Example:**
```bash
curl http://localhost:8000/feedback/analysis/improvements?days=7
```

---

## 🏥 Health & Stats Endpoints

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-04-16T10:30:00Z",
  "database": "connected",
  "vector_store": {
    "total_vectors": 1250,
    "dimension": 768,
    "is_trained": true,
    "by_source": {
      "knowledge_base": 1000,
      "ticket": 250
    }
  }
}
```

**Curl Example:**
```bash
curl http://localhost:8000/health
```

---

### GET /stats

Get system statistics.

**Response (200 OK):**
```json
{
  "chatbot": {
    "vector_store": {
      "total_vectors": 1250,
      "by_source": {
        "knowledge_base": 1000,
        "ticket": 250
      }
    },
    "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "embedding_dimension": 768,
    "supported_languages": ["en", "fr", "ar", "franco-arabic"],
    "similarity_threshold": 0.65
  },
  "tickets": {
    "total_tickets": 150,
    "by_status": {...},
    "avg_resolution_time_minutes": 45.5
  },
  "feedback": {
    "total_feedback": 250,
    "average_rating": 4.2,
    ...
  }
}
```

**Curl Example:**
```bash
curl http://localhost:8000/stats
```

---

### GET /info

Get system information.

**Response (200 OK):**
```json
{
  "app_name": "Moviroo AI Chatbot",
  "version": "1.0.0",
  "environment": "production",
  "supported_languages": ["en", "fr", "ar", "franco-arabic"],
  "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
  "similarity_threshold": 0.65,
  "auto_learning_enabled": true,
  "features": {
    "multilingual": true,
    "semantic_search": true,
    "incremental_learning": true,
    "feedback_system": true,
    "ticket_system": true
  }
}
```

**Curl Example:**
```bash
curl http://localhost:8000/info
```

---

## 🔧 Admin Endpoints

### POST /admin/load-dataset

Load initial dataset from CSV.

**Response (200 OK):**
```json
{
  "message": "Dataset loaded successfully",
  "entries_loaded": 50,
  "timestamp": "2024-04-16T10:30:00Z"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/admin/load-dataset
```

---

### POST /admin/rebuild-index

Rebuild FAISS vector index.

**Response (200 OK):**
```json
{
  "message": "Index rebuilt successfully",
  "total_vectors": 1250,
  "by_source": {
    "knowledge_base": 1000,
    "ticket": 250
  },
  "timestamp": "2024-04-16T10:30:00Z"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/admin/rebuild-index
```

---

## 🚨 Error Responses

### 400 Bad Request

Invalid input data.

```json
{
  "error": "Validation Error",
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "timestamp": "2024-04-16T10:30:00Z"
}
```

---

### 404 Not Found

Resource not found.

```json
{
  "error": "Not Found",
  "detail": "Ticket TICKET-XYZ not found",
  "timestamp": "2024-04-16T10:30:00Z"
}
```

---

### 500 Internal Server Error

Server error.

```json
{
  "error": "Internal Server Error",
  "detail": "An unexpected error occurred",
  "timestamp": "2024-04-16T10:30:00Z"
}
```

---

## 📊 Rate Limiting

Currently no rate limiting is enforced, but consider implementing:

- **Chat**: 60 requests/minute per user
- **Tickets**: 10 requests/minute per user
- **Feedback**: 20 requests/minute per user

---

## 🔐 Authentication

Currently no authentication is required. For production:

1. Add API key header: `X-API-Key`
2. Use JWT tokens for user sessions
3. Implement OAuth 2.0 for third-party apps

---

## 📝 Notes

- All timestamps are in ISO 8601 format (UTC)
- Confidence scores range from 0.0 to 1.0
- Ratings range from 1 to 5
- All endpoints return JSON responses
- CORS is enabled for configured origins

---

**For interactive documentation, visit: http://localhost:8000/docs**
