# Stage 1: Build dashboard Next.js frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build/dashboard
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

# Stage 2: Serve Python FastAPI server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for psycopg2 (PostgreSQL client)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY dasc/ dasc/

# Copy static dashboard from Stage 1 into the Python package assets folder
COPY --from=frontend-builder /build/dashboard/out/ dasc/dashboard/

RUN pip install --no-cache-dir .

EXPOSE 8000

# Run the control plane server
CMD ["uvicorn", "dasc.server:app", "--host", "0.0.0.0", "--port", "8000"]
