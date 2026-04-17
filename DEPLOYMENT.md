# 🚀 Deployment Checklist - Moviroo AI Chatbot

Use this checklist to ensure a smooth deployment to production.

## Pre-Deployment

### Security
- [ ] Change `SECRET_KEY` in `.env` to a strong random value
- [ ] Update database password (not 'password')
- [ ] Set `DEBUG=False` in production
- [ ] Configure CORS origins to only allowed domains
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up firewall rules (only expose necessary ports)
- [ ] Review and restrict database access
- [ ] Enable PostgreSQL SSL connections

### Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `DATABASE_URL` with production database
- [ ] Set appropriate `API_WORKERS` (4-8 for production)
- [ ] Configure `LOG_LEVEL=INFO` or `WARNING`
- [ ] Set up proper `CORS_ORIGINS`
- [ ] Adjust `SIMILARITY_THRESHOLD` based on testing
- [ ] Configure `AUTO_LEARNING_ENABLED` as needed

### Database
- [ ] Create production PostgreSQL database
- [ ] Run database migrations/initialization
- [ ] Set up automated backups
- [ ] Configure connection pooling
- [ ] Enable query performance monitoring
- [ ] Create database indexes (already in models)
- [ ] Test database connectivity

### Data Preparation
- [ ] Prepare production `dataset.csv` with real Q&A
- [ ] Review and clean data for accuracy
- [ ] Translate dataset to all supported languages
- [ ] Test Franco-Arabic phrases
- [ ] Validate categories match your use case
- [ ] Load dataset via API: `POST /admin/load-dataset`
- [ ] Build initial index: `POST /admin/rebuild-index`

## Deployment

### Docker Deployment
- [ ] Build production Docker image
- [ ] Test image locally first
- [ ] Push to container registry
- [ ] Update `docker-compose.yml` for production
- [ ] Set resource limits (CPU, memory)
- [ ] Configure restart policies
- [ ] Set up volume mounts for persistence
- [ ] Deploy with `docker-compose up -d`

### Server Setup
- [ ] Provision server (4GB+ RAM recommended)
- [ ] Install Docker and Docker Compose
- [ ] Configure firewall (ports 80, 443, 5432)
- [ ] Set up reverse proxy (Nginx/Traefik)
- [ ] Configure SSL/TLS certificates (Let's Encrypt)
- [ ] Set up domain DNS records
- [ ] Enable automatic security updates

### Monitoring
- [ ] Set up application logging
- [ ] Configure log rotation
- [ ] Set up health check monitoring
- [ ] Configure uptime monitoring (UptimeRobot, etc.)
- [ ] Set up error alerting (email, Slack, PagerDuty)
- [ ] Monitor API response times
- [ ] Track confidence score trends
- [ ] Monitor database performance
- [ ] Set up resource usage alerts (CPU, RAM, disk)

### Testing
- [ ] Run health check: `GET /health`
- [ ] Test all API endpoints
- [ ] Run full test suite: `python test_api.py`
- [ ] Test multilingual support (EN, FR, AR, Franco-Arabic)
- [ ] Verify ticket creation and management
- [ ] Test feedback submission
- [ ] Check response times under load
- [ ] Verify database persistence
- [ ] Test FAISS index persistence
- [ ] Validate backup and restore procedures

## Post-Deployment

### Initial Setup
- [ ] Load production dataset
- [ ] Build production FAISS index
- [ ] Create admin user accounts (if applicable)
- [ ] Import historical tickets (if available)
- [ ] Train on existing support data
- [ ] Verify vector store statistics

### Integration
- [ ] Integrate with Flutter mobile app
- [ ] Set up API authentication (if needed)
- [ ] Configure rate limiting
- [ ] Test end-to-end user flow
- [ ] Verify webhook/callback functionality
- [ ] Document API for frontend team

### Documentation
- [ ] Update API documentation
- [ ] Document deployment process
- [ ] Create runbook for common issues
- [ ] Document backup/restore procedures
- [ ] Create incident response plan
- [ ] Document scaling procedures

### Performance Optimization
- [ ] Enable query caching
- [ ] Optimize database queries
- [ ] Configure CDN (if serving static files)
- [ ] Set up load balancing (for high traffic)
- [ ] Optimize FAISS index parameters
- [ ] Monitor and tune worker count
- [ ] Enable gzip compression

## Ongoing Maintenance

### Daily
- [ ] Check application logs for errors
- [ ] Monitor API response times
- [ ] Review error rates
- [ ] Check system resource usage

### Weekly
- [ ] Review low-rated feedback
- [ ] Analyze improvement opportunities
- [ ] Update knowledge base from resolved tickets
- [ ] Rebuild FAISS index if significant changes
- [ ] Review and respond to unresolved tickets

### Monthly
- [ ] Analyze usage statistics
- [ ] Review and update dataset
- [ ] Optimize underperforming categories
- [ ] Update model if needed
- [ ] Review and update documentation
- [ ] Perform security audit
- [ ] Test backup restoration

### Quarterly
- [ ] Review and update system architecture
- [ ] Evaluate new model versions
- [ ] Performance benchmarking
- [ ] Capacity planning
- [ ] Security assessment
- [ ] Disaster recovery drill

## Rollback Plan

If deployment fails:

1. **Immediate Actions**
   - [ ] Stop new deployment
   - [ ] Switch back to previous version
   - [ ] Restore database backup if needed
   - [ ] Notify stakeholders

2. **Investigation**
   - [ ] Check application logs
   - [ ] Review deployment changes
   - [ ] Identify root cause
   - [ ] Document issue

3. **Resolution**
   - [ ] Fix identified issues
   - [ ] Test in staging environment
   - [ ] Plan re-deployment
   - [ ] Update deployment checklist

## Support Contacts

- **DevOps**: [contact info]
- **Database Admin**: [contact info]
- **On-call Engineer**: [contact info]
- **Product Owner**: [contact info]

## Environment Variables Checklist

```bash
# Critical Production Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<strong-random-value>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
API_WORKERS=4
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
AUTO_LEARNING_ENABLED=True
```

## Success Criteria

Deployment is successful when:

- ✅ Health endpoint returns `status: healthy`
- ✅ All API tests pass
- ✅ Confidence scores > 0.7 for test queries
- ✅ Response times < 200ms average
- ✅ No errors in last 100 requests
- ✅ Database connections stable
- ✅ FAISS index loaded with vectors
- ✅ Logs show no critical errors
- ✅ Mobile app integration working

## Quick Commands

```bash
# Check health
curl https://api.yourdomain.com/health

# Run tests
python test_api.py

# View logs
docker-compose logs -f chatbot-api

# Rebuild index
curl -X POST https://api.yourdomain.com/admin/rebuild-index

# Get stats
curl https://api.yourdomain.com/stats

# Backup database
docker-compose exec postgres pg_dump -U moviroo moviroo_chatbot > backup.sql

# Restart service
docker-compose restart chatbot-api
```

---

**Note**: Customize this checklist based on your specific infrastructure and requirements.
