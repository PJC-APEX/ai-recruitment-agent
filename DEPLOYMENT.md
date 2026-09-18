# Deployment Guide

Deploy the Resume Screening System to production.

## Deployment Options

1. **Docker Compose** (Recommended for single server)
2. **Kubernetes** (For scalable production)
3. **Cloud Platforms** (AWS, GCP, Azure)
4. **Serverless** (AWS Lambda + API Gateway)

---

## Option 1: Docker Compose

### Prerequisites

- Docker 20+
- Docker Compose 2+

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CHROMA_PERSIST_DIRECTORY=/app/chroma_db
    volumes:
      - ./backend/data:/app/data
      - ./backend/chroma_db:/app/chroma_db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  chroma_data:
  resume_data:
```

### Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p data/resumes chroma_db

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Frontend nginx.conf

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Frontend routes
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Deploy

```bash
# Set environment variables
export OPENAI_API_KEY=your_key_here

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Option 2: Cloud Deployment (AWS)

### Architecture

```
Internet → CloudFront → ALB → ECS (Backend) + S3 (Frontend)
                              ↓
                         RDS/DynamoDB (Optional)
                              ↓
                         S3 (Resume Storage)
```

### Steps

#### 1. Setup S3 for Frontend

```bash
# Create S3 bucket
aws s3 mb s3://resume-screening-frontend

# Build frontend
cd frontend
npm run build

# Upload to S3
aws s3 sync dist/ s3://resume-screening-frontend --acl public-read

# Enable static website hosting
aws s3 website s3://resume-screening-frontend --index-document index.html
```

#### 2. Deploy Backend to ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name resume-screening-backend

# Build and push Docker image
cd backend
docker build -t resume-screening-backend .
docker tag resume-screening-backend:latest $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/resume-screening-backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/resume-screening-backend:latest

# Create ECS task definition and service
# (Use AWS Console or Terraform)
```

#### 3. Setup Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name resume-screening-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Configure target groups and listeners
```

#### 4. Environment Variables

Store in AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter \
  --name /resume-screening/openai-api-key \
  --value "your-key" \
  --type SecureString
```

---

## Option 3: Google Cloud Platform

### Steps

#### 1. Deploy Backend to Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/resume-backend backend/

# Deploy to Cloud Run
gcloud run deploy resume-backend \
  --image gcr.io/$PROJECT_ID/resume-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

#### 2. Deploy Frontend to Cloud Storage + Cloud CDN

```bash
# Build frontend
cd frontend
npm run build

# Create bucket
gsutil mb gs://resume-screening-frontend

# Upload files
gsutil -m rsync -r dist/ gs://resume-screening-frontend

# Make bucket public
gsutil iam ch allUsers:objectViewer gs://resume-screening-frontend

# Enable CDN
gcloud compute backend-buckets create resume-frontend-bucket \
  --gcs-bucket-name=resume-screening-frontend \
  --enable-cdn
```

---

## Environment Variables for Production

### Backend

```env
# Required
OPENAI_API_KEY=your_production_key

# Application
DEBUG=False
APP_NAME=Resume Screening System
APP_VERSION=1.0.0

# Database
CHROMA_PERSIST_DIRECTORY=/app/chroma_db

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Retrieval
TOP_K_RESULTS=5

# Security (add these)
ALLOWED_ORIGINS=https://yourdomain.com
API_KEY=your_api_key  # For endpoint protection
JWT_SECRET=your_jwt_secret
```

### Frontend

Update `src/services/api.js`:

```javascript
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://api.yourdomain.com/api'
  : 'http://localhost:8000/api';
```

---

## Security Checklist

- [ ] Use HTTPS/TLS certificates
- [ ] Enable CORS with specific origins
- [ ] Add API authentication (API keys or JWT)
- [ ] Rate limiting on endpoints
- [ ] Input validation and sanitization
- [ ] Secrets in environment variables (not code)
- [ ] Regular dependency updates
- [ ] Enable logging and monitoring
- [ ] Implement file upload size limits
- [ ] Scan uploaded files for malware

---

## Performance Optimization

### Backend

1. **Caching**: Add Redis for search results

```python
import redis
from functools import lru_cache

cache = redis.Redis(host='localhost', port=6379)

@lru_cache(maxsize=100)
def cached_search(query):
    # Cache search results
    pass
```

2. **Database**: Use PostgreSQL for metadata

3. **Load Balancing**: Multiple backend instances

4. **Async Workers**: Celery for background tasks

For resume ingestion, this project now supports an ARQ + Redis worker. Set
`INGESTION_QUEUE_ENABLED=true` and `REDIS_URL`, then run from `backend`:

```bash
python -m arq app.jobs.worker.WorkerSettings
```

`POST /api/upload-resume` returns a content-hash `job_id` with `queued` status;
poll `GET /api/upload-jobs/{job_id}`. Parsing/chunking/local Chroma I/O use the
bounded thread pool, Embedding calls use a semaphore, and retries use stable
`{file_hash}:{chunk_index}` vector IDs plus Redis locks.

### Frontend

1. **CDN**: Serve static files from CDN
2. **Code Splitting**: Lazy load components
3. **Compression**: Enable gzip/brotli
4. **Caching**: Service worker for offline support

---

## Monitoring & Logging

### Backend Logging

```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
logger.addHandler(handler)
```

### Application Monitoring

Use tools like:

- **Sentry** for error tracking
- **Datadog** for APM
- **Prometheus + Grafana** for metrics
- **ELK Stack** for log aggregation

### Health Checks

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "openai": await check_openai(),
            "vector_store": await check_vector_store()
        }
    }
```

---

## Scaling Considerations

### Horizontal Scaling

- Multiple backend instances behind load balancer
- Shared vector database (or separate per instance)
- Centralized resume storage (S3/GCS)

### Database Scaling

- **ChromaDB**: Not ideal for multi-instance (use Pinecone/Weaviate)
- **PostgreSQL**: For metadata and user data
- **Redis**: For caching and sessions

### Cost Optimization

- Use spot/preemptible instances
- Cache embeddings to reduce OpenAI calls
- Batch processing for bulk operations
- Auto-scaling based on load

---

## Backup & Disaster Recovery

### Backup Strategy

```bash
# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/

# Backup resumes
aws s3 sync data/resumes/ s3://backup-bucket/resumes/

# Automated backups
0 2 * * * /path/to/backup.sh
```

### Restore Procedure

```bash
# Restore ChromaDB
tar -xzf chroma_backup_20240101.tar.gz

# Restore resumes
aws s3 sync s3://backup-bucket/resumes/ data/resumes/
```

---

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Build backend
      run: |
        cd backend
        docker build -t resume-backend .
    
    - name: Push to registry
      run: |
        docker push your-registry/resume-backend
    
    - name: Deploy to production
      run: |
        kubectl apply -f k8s/
```

---

## Production Checklist

- [ ] Environment variables configured
- [ ] HTTPS enabled with valid certificates
- [ ] Database backups automated
- [ ] Monitoring and alerting setup
- [ ] Error tracking enabled
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Secrets management in place
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] Runbooks created for incidents

---

## Support & Maintenance

- Monitor error rates and performance
- Review logs regularly
- Update dependencies monthly
- Test disaster recovery procedures
- Document incidents and resolutions
- Plan for scaling based on usage

---

For more deployment options, consult your cloud provider's documentation.
