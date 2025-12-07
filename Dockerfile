# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.12.10
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN apt-get update && \
    apt-get install -y gcc portaudio19-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the dependency management files (lockfile and pyproject.toml) first
# This allows Docker to cache the dependency installation layer separately
COPY uv.lock pyproject.toml /app/

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install the application dependencies using uv
# This replaces the pip install from requirements.txt to avoid conflicts
RUN uv sync --frozen --no-cache


# Set the virtual environment variables.
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy the source code into the container.
# This is done after dependency installation to leverage Docker layer caching
COPY src/ /app/

# Install the application in editable mode.
RUN uv pip install -e .

# Change ownership of /app to appuser for proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-privileged user
USER appuser

# Expose the port that the application listens on.
EXPOSE 8080

# Run the FastAPI application using uvicorn
# Using uvicorn directly as it's more reliable than fastapi CLI
CMD ["/app/.venv/bin/uvicorn", "ai_companion.interfaces.telegram.webhook_endpoint:app", "--port", "8080", "--host", "0.0.0.0"]