# ============================================================
# SunsetBot Backend — Dockerfile
# ============================================================
# Image will be ~2-3 GB due to PyTorch + SentenceTransformers.
# First startup downloads the embedding model (~90 MB).
# ============================================================

FROM python:3.11-slim

# System dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Port (Railway injects $PORT, default 8000)
EXPOSE 8000

# Run the server
CMD ["python", "main.py"]
