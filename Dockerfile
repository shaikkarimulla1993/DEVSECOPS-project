# ------------------------------------------------------
# Base Image (Pinned)
# ------------------------------------------------------
FROM python:3.11.13-slim-bookworm

# ------------------------------------------------------
# Environment Variables
# ------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ------------------------------------------------------
# Patch OS Packages (Trivy: libssl3, libgnutls30 CVEs)
# ------------------------------------------------------
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------
# Create Non-Root User
# ------------------------------------------------------
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --create-home appuser

# ------------------------------------------------------
# Working Directory
# ------------------------------------------------------
WORKDIR /app

# ------------------------------------------------------
# Install Python Dependencies
# ------------------------------------------------------
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ------------------------------------------------------
# Copy Application
# ------------------------------------------------------
COPY app/ ./app

# ------------------------------------------------------
# Set Ownership
# ------------------------------------------------------
RUN chown -R appuser:appgroup /app

# ------------------------------------------------------
# Run as Non-Root User
# ------------------------------------------------------
USER appuser

# ------------------------------------------------------
# Expose Port
# ------------------------------------------------------
EXPOSE 8000

# ------------------------------------------------------
# Health Check
# ------------------------------------------------------
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=20s \
            --retries=3 \
CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ------------------------------------------------------
# Start Application
# ------------------------------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "app"]
