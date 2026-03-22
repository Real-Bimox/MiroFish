FROM python:3.11

# Install Node.js (>=18) and necessary tools
RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm \
  && rm -rf /var/lib/apt/lists/*

# Copy uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# jupyterlab-pygments 0.4.0 ships a wheel named 0.3.0 — skip the mismatch check
ENV UV_SKIP_WHEEL_FILENAME_CHECK=1

WORKDIR /app

# Copy dependency description files first to leverage cache
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install dependencies (Node + Python)
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# Copy project source code
COPY . .

EXPOSE 3000 5001

# Start both frontend and backend (development mode)
CMD ["npm", "run", "dev"]