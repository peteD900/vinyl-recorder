FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* ./

# Install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY vinyl_recorder/ ./vinyl_recorder/

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "vinyl_recorder.web_app:app", "--host", "0.0.0.0", "--port", "8000"]