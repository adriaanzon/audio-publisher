# -------------- Builder --------------
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

# Copy and install only dependencies first
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the project and install it
COPY . /app
RUN uv sync --frozen --no-dev

# ------------ Final image ------------
FROM python:3.13-alpine

WORKDIR /app

# Install ffmpeg in runtime
RUN apk add --no-cache ffmpeg

# Copy over virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/main.py"]
