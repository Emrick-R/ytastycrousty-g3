FROM python:3.12-slim
# Récupère le binaire uv officiel, pas besoin de pip install
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Deps copiées seules d'abord -> layer Docker mis en cache si le code change sans toucher aux deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# Code applicatif copié après (n'invalide le cache que si le code change)
COPY . .

EXPOSE 8000
# 0.0.0.0 = écoute toutes les interfaces (127.0.0.1 serait injoignable depuis l'hôte)
CMD ["/app/.venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# lancer le container docker:  docker build -t ytasty-g3-api .
#                              docker run -p 8000:8000 ytasty-g3-api
# utiliser  http://127.0.0.1:8000