# Ytasty Crousty — Backend FastAPI

API REST pour la chaîne de restaurants Ytasty Crousty : gestion des restaurants, des produits, des commandes et de l'authentification. Construite avec FastAPI, SQLAlchemy et PostgreSQL, conteneurisée avec Docker.

## Stack technique

- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker / docker-compose
- Gestion des dépendances : [uv](https://docs.astral.sh/uv/)

## Prérequis

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installé
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé (recommandé pour le lancement local)

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-depot>
cd ytastycrousty-g3
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Le fichier `.env` par défaut fonctionne tel quel pour un lancement 100 % local (identifiants de dev, pas de vrai secret). Ne jamais commiter `.env` — il est déjà exclu par `.gitignore`.

### 3. Lancer le projet (avec Docker — recommandé)

```bash
docker compose up --build
```

Cette commande lance l'API **et** PostgreSQL, crée automatiquement les tables au démarrage (via un `lifespan` FastAPI), et n'exige rien d'autre installé sur la machine que Docker.

### 4. Lancer le projet sans Docker (dev local)

```bash
uv sync
uv run uvicorn src.main:app --reload
```

⚠️ Nécessite une base PostgreSQL accessible sur `127.0.0.1:5432` — le plus simple est de garder le service `db` de `docker-compose.yml` actif (`docker compose up db`) et de lancer l'API à côté avec la commande ci-dessus.

## Vérifier que ça fonctionne

| URL | Attendu |
| --- | --- |
| `http://127.0.0.1:8000/health` | `{"status": "ok"}` |
| `http://127.0.0.1:8000/docs` | Documentation Swagger interactive |
| `http://127.0.0.1:8000/openapi.json` | Schéma OpenAPI brut |

Sur Windows, préférer `127.0.0.1` à `localhost` (résolution IPv6 parfois capricieuse avec Docker Desktop).

## Structure du projet

```
src/
  main.py            # point d'entrée FastAPI, lifespan (création des tables au démarrage)
  db/
    database.py      # engine SQLAlchemy, session par requête (get_db), Base
  models/
    __init__.py      # centralise l'import de tous les modèles
    restaurant.py
    user.py
    produit.py
    ingredient.py     # + table d'association produit_ingredient
    order.py
    order_item.py
Dockerfile
docker-compose.yml
.env.example
pyproject.toml / uv.lock
```

## Modèle de données

6 tables : `restaurants`, `users`, `produits`, `ingredients`, `orders`, `order_items`, plus la table d'association `produit_ingredient` (relation plusieurs-à-plusieurs entre produits et ingrédients).

- Un restaurant a plusieurs utilisateurs, produits et commandes.
- Un produit appartient à un restaurant et peut avoir plusieurs ingrédients.
- Une commande appartient à un restaurant et contient plusieurs lignes (`order_items`), chacune figeant le prix du produit au moment de la commande.

## État actuel du projet

- [x] Structure du projet et gestion des dépendances (`uv`)
- [x] Conteneurisation (Docker + docker-compose)
- [x] Connexion SQLAlchemy + PostgreSQL
- [x] Modèles de données et relations (6 tables)
- [x] `GET /health`
- [ ] Authentification JWT
- [ ] Gestion des utilisateurs et rôles
- [ ] Endpoints Restaurants
- [ ] Endpoints Produits
- [ ] Endpoints Commandes
- [ ] Déploiement public

## Commandes utiles

| Commande | Effet |
| --- | --- |
| `uv sync` | installe les dépendances depuis `pyproject.toml` / `uv.lock` |
| `uv add <package>` | ajoute une nouvelle dépendance |
| `docker compose up --build` | reconstruit et lance l'API + PostgreSQL |
| `docker compose exec db psql -U ytastyg3 -d ytastyg3` | ouvre une session SQL dans le container PostgreSQL |
| `uv run python -c "import src.models; print('OK')"` | vérifie que tous les modèles se chargent sans erreur |