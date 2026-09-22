# Ytasty Crousty — Backend FastAPI

API REST pour la chaîne de restaurants Ytasty Crousty : gestion des restaurants, des produits, des commandes et de l'authentification. Construite avec FastAPI, SQLAlchemy et PostgreSQL, conteneurisée avec Docker.

## Stack technique

- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker / docker-compose
- Gestion des dépendances : [uv](https://docs.astral.sh/uv/)
- Authentification : JWT ([PyJWT](https://pyjwt.readthedocs.io/)), hash des mots de passe ([passlib](https://passlib.readthedocs.io/) + bcrypt)

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé — **seul prérequis nécessaire pour lancer le projet.**
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installé — uniquement si tu veux ajouter/modifier des dépendances en dehors de Docker.

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

Le `.env` doit contenir :
- `DATABASE_URL` — laisser la valeur par défaut (`postgresql://...@db:5432/...`), `db` est le nom du service PostgreSQL dans Docker.
- `SECRET_KEY` — **obligatoire, sans valeur par défaut** (l'API refuse de démarrer si elle est absente). Génère-en une avec `uv run python -c "import secrets; print(secrets.token_hex(32))"`.
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` — identifiants de la base, utilisés à la fois par le service `db` et par `DATABASE_URL`.

Ne jamais commiter `.env` — il est déjà exclu par `.gitignore`.

### 3. Lancer le projet

```bash
docker compose up --build
```

Lance l'API **et** PostgreSQL, crée automatiquement les tables au démarrage (via un `lifespan` FastAPI), et seed un compte administrateur par défaut. N'exige rien d'autre installé sur la machine que Docker.

> Le projet est pensé pour tourner **uniquement via Docker** (pas de lancement local `uv run uvicorn` supporté) — `SECRET_KEY` doit être disponible dans l'environnement du process, et Docker s'en charge nativement via `docker-compose.yml`. Après toute modification de code, relance `docker compose up --build` (pas de hot-reload configuré).

## Compte administrateur par défaut

Seedé automatiquement au premier démarrage :

| Champ | Valeur |
| --- | --- |
| `username` | `admin123` |
| `password` | `Admin@123456` |
| `role` | `admin` |

## Authentification

1. `POST /auth/login` avec `{"username": "...", "password": "..."}` → renvoie `{"access_token": "...", "token_type": "bearer"}` (JWT signé HS256, valide 30 minutes).
2. Sur `/docs`, bouton **Authorize** (en haut à droite) → coller l'`access_token` (sans le préfixe `Bearer`) → toutes les routes protégées de Swagger l'utilisent automatiquement ensuite.
3. Rôles disponibles : `admin`, `staff`, `direction` — certaines routes sont réservées à un ou plusieurs rôles précis.

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
  main.py             # point d'entrée FastAPI, lifespan (création des tables + seed admin au démarrage)
  db/
    database.py       # engine SQLAlchemy, session par requête (get_db), Base
  models/
    __init__.py       # centralise l'import de tous les modèles
    restaurant.py
    user.py
    produit.py
    ingredient.py      # + table d'association produit_ingredient
    order.py
    order_item.py
  core/
    security.py        # hashing (bcrypt/passlib), création/vérification JWT — logique pure, sans FastAPI
    deps.py             # dépendances FastAPI : get_current_user, require_role(*roles)
  routers/
    auth.py             # /auth/login, /users (CRUD complet), schémas Pydantic associés
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
- Un utilisateur (`users`) a un rôle (`admin`/`staff`/`direction`) et, optionnellement, un restaurant de rattachement (`restaurant_id`, absent pour `admin`).

## État actuel du projet

- [x] Structure du projet et gestion des dépendances (`uv`)
- [x] Conteneurisation (Docker + docker-compose)
- [x] Connexion SQLAlchemy + PostgreSQL
- [x] Modèles de données et relations (6 tables)
- [x] `GET /health`
- [x] Authentification JWT (`POST /auth/login`)
- [x] Gestion des utilisateurs et rôles (`POST /users` + CRUD complet en bonus : `GET /users`, `GET /users/{id}`, `PATCH /users/{id}`, `DELETE /users/{id}`)
- [ ] Endpoints Restaurants
- [ ] Endpoints Produits
- [ ] Endpoints Commandes
- [ ] Déploiement public

## Commandes utiles

| Commande | Effet |
| --- | --- |
| `docker compose up --build` | reconstruit et lance l'API + PostgreSQL (à refaire après chaque changement de code) |
| `docker compose down` | arrête les conteneurs (les données PostgreSQL sont conservées, volume nommé) |
| `docker compose down -v` | arrête les conteneurs **et supprime les données** (repart de zéro) |
| `docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` | ouvre une session SQL dans le container PostgreSQL |
| `docker compose exec api uv run python -c "..."` | exécute une commande Python ponctuelle dans le container API |
| `TRUNCATE TABLE users RESTART IDENTITY;` (dans `psql`) | vide la table `users` et réinitialise les ID (admin123 sera reseedé au prochain démarrage) |