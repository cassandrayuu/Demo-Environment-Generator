# Productboard Demo Generator - Runner Service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (for better caching)
COPY services/runner/requirements.txt /app/services/runner/
RUN pip install --no-cache-dir -r /app/services/runner/requirements.txt

# Copy core module
COPY core/ /app/core/

# Copy runner service
COPY services/runner/ /app/services/runner/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Default port (Railway injects PORT env var)
ENV PORT=8000

# Run the application (shell form for env var expansion)
CMD uvicorn services.runner.main:app --host 0.0.0.0 --port $PORT
