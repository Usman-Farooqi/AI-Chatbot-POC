FROM python:3.11-slim

WORKDIR /app

# PyMuPDF ships its own bundled MuPDF — no system PDF libraries needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image (~90MB)
# Avoids a model download on every cold start
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY server.py .

EXPOSE 8000

CMD ["python", "server.py"]
