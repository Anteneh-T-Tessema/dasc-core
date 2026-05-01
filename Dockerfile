FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY dasc/ dasc/

RUN pip install --no-cache-dir .

EXPOSE 8000

# Run the control plane server
CMD ["uvicorn", "dasc.server:app", "--host", "0.0.0.0", "--port", "8000"]
