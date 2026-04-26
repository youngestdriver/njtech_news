FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and templates
COPY njtech_news.sh .
COPY web/ ./web/

ENV NEWS_CACHE_DIR=/data

CMD ["python", "njtech_news.sh"]
