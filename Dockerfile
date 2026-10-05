FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[all]' && useradd --create-home --uid 1000 fortune && mkdir -p /app/work && chown fortune:fortune /app/work
USER fortune
EXPOSE 8766
CMD ["fortune-web", "--bind", "0.0.0.0", "--port", "8766", "--cache", "/app/work/daily.sqlite3"]
