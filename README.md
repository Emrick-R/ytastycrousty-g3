# Ytasty Crousty — Backend FastAPI

## Présentation

API REST de commande en ligne pour les 3 restaurants Ytasty Crousty (Aix, Lyon, Paris) : carte des produits, prise et suivi de commandes, gestion des restaurants. Authentification JWT et trois rôles : `admin`, `staff` et `direction`.

### Stack technique

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- JWT ([PyJWT](https://pyjwt.readthedocs.io/))
- Hash des mots de passe : bcrypt / [passlib](https://passlib.readthedocs.io/)
- Gestion des dépendances : [uv](https://docs.astral.sh/uv/)
- Docker et Docker Compose

## Prérequis et installation

### Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé — **seul prérequis nécessaire pour lancer le projet.**
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installé — uniquement si tu veux ajouter/modifier des dépendances en dehors de Docker.

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
- `SECRET_KEY` — **obligatoire, sans valeur par défaut** : l'API refuse de démarrer si elle est absente. Génère-en une avec `uv run python -c "import secrets; print(secrets.token_hex(32))"`.
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` — identifiants de la base, utilisés à la fois par le service `db` et par `DATABASE_URL`.

Voir `.env.example` pour la liste complète et des valeurs d'exemple (aucun secret réel).

Ne jamais commiter `.env` — il est déjà exclu par `.gitignore`.

### 3. Lancer le projet

```bash
docker compose up --build
```

Lance l'API **et** PostgreSQL, crée automatiquement les tables au démarrage (via un `lifespan` FastAPI) et initialise les données de base (voir ci-dessous). L'API est alors disponible sur `http://localhost:8000` et Swagger sur `http://localhost:8000/docs`.

Le projet est pensé pour tourner **uniquement via Docker** (pas de lancement local `uv run uvicorn` supporté) — `SECRET_KEY` doit être disponible dans l'environnement du process, et Docker s'en charge nativement via `docker-compose.yml`. Après toute modification de code, relance `docker compose up --build` (pas de hot-reload configuré).

Pour repartir d'une base vide :

```bash
docker compose down -v
docker compose up --build
```

C'est **nécessaire après toute modification d'un modèle** : `create_all` crée les tables manquantes mais ne modifie pas les tables existantes.

## Données initialisées et authentification

### Données initialisées automatiquement

Au premier démarrage, l'API crée le compte administrateur imposé par le contrat :

| Champ | Valeur |
| --- | --- |
| `username` | `admin123` |
| `password` | `Admin@123456` |
| `role` | `admin` |

Les 3 restaurants :

| id | Nom |
| --- | --- |
| 1 | Ytasty Crousty Aix |
| 2 | Ytasty Crousty Lyon |
| 3 | Ytasty Crousty Paris |

Ainsi que 8 produits de démonstration répartis sur les 3 restaurants, pour tester `/products` et ses filtres dès le démarrage.

### Créer des comptes de test

Aucun compte `staff` ou `direction` n'est créé automatiquement. Pour en ajouter, se connecter en `admin123` puis appeler `POST /users` avec le token admin.

Exemple : un `staff` rattaché au restaurant 1 (Aix) :

```json
{
  "first_name": "Alice",
  "last_name": "Martin",
  "username": "staffaix1",
  "password": "<mot-de-passe-conforme>",
  "role": "staff",
  "restaurant_id": 1
}
```

Exemple : un compte `direction` (sans restaurant de rattachement) :

```json
{
  "first_name": "Paul",
  "last_name": "Durand",
  "username": "direction1",
  "password": "<mot-de-passe-conforme>",
  "role": "direction"
}
```

Règles de validation :

- `username` alphanumérique, de 8 à 12 caractères ;
- `password` de 12 à 64 caractères, avec au moins un chiffre, une majuscule et un caractère spécial ;
- un `staff` doit obligatoirement être rattaché à un restaurant existant (`restaurant_id`).

Ces comptes sont stockés en base : ils disparaissent après un `docker compose down -v` et sont à recréer.

### Authentification et utilisation de Swagger

Dans Swagger (`/docs`), les routes sont regroupées par sections : **Santé**, **Auth & Users**, **Restaurants**, **Produits** et **Commandes**. Chaque route est documentée avec un résumé, une description et ses codes d'erreur possibles.

1. `POST /auth/login` avec `{"username": "...", "password": "..."}` → renvoie `{"access_token": "...", "token_type": "bearer"}` (JWT signé HS256, valide 30 minutes).
2. Bouton **Authorize** (en haut à droite) → coller l'`access_token` (sans le préfixe `Bearer`) → toutes les routes protégées l'utilisent ensuite automatiquement. Le token est conservé après un rechargement de la page.
3. Rôles disponibles : `admin`, `staff`, `direction` — certaines routes sont réservées à un ou plusieurs rôles précis.

## Endpoints disponibles

| Domaine | Méthode | Route | Accès |
| --- | --- | --- | --- |
| Santé | GET | `/health` | Public |
| Auth & Users | POST | `/auth/login` | Public |
| Auth & Users | POST | `/users` | admin |
| Auth & Users | GET | `/users` | admin (bonus) |
| Auth & Users | GET / PATCH / DELETE | `/users/{id}` | admin (bonus) |
| Restaurants | GET | `/restaurants` | Public |
| Restaurants | GET | `/restaurants/{id}` | Public |
| Restaurants | PATCH | `/restaurants/{id}` | admin |
| Restaurants | PATCH | `/restaurants/{id}/availability` | admin |
| Restaurants | POST | `/restaurants` | admin (bonus) |
| Produits | GET | `/products` — filtres `category`, `q`, `restaurant_id`, `is_available`, combinables | Public |
| Produits | GET | `/products/{id}` | Public |
| Produits | POST | `/products` | admin partout, staff sur son restaurant |
| Produits | PATCH | `/products/{id}` | admin partout, staff sur son restaurant |
| Produits | DELETE | `/products/{id}` | admin partout, staff sur son restaurant |
| Produits | PATCH | `/products/{id}/availability` | admin partout, staff sur son restaurant |
| Commandes | POST | `/orders` | Public |
| Commandes | GET | `/orders/{order_number}` | Public |
| Commandes | GET | `/restaurants/{id}/orders` — filtre `?status=` | admin et direction (tous restaurants), staff (son restaurant) |
| Commandes | PATCH | `/orders/{order_number}/status` | admin, staff de son restaurant |
| Commandes | POST | `/orders/{order_number}/cancel` | admin, staff de son restaurant |

## Règles métier principales

- Le total d'une commande est **calculé par le serveur** à partir des prix en base ; le client n'envoie jamais de prix. Le prix de chaque produit est **figé** dans la commande au moment où elle est passée.
- Une commande est refusée si le restaurant est fermé, si un produit est inexistant, appartient à un autre restaurant ou est indisponible, ou si une quantité est inférieure ou égale à 0.
- Le numéro de suivi est aléatoire, au format `YC-XXXXXXXX` (8 caractères majuscules/chiffres).
- Statuts possibles : `pending`, `validated`, `preparing`, `ready`, `collected`, `cancelled`.
- Une commande `collected` ou `cancelled` ne change plus de statut.
- Un produit déjà commandé ne peut pas être supprimé : il faut le rendre indisponible via `PATCH /products/{id}/availability`.

## Droits par rôle

| Rôle | Droits |
| --- | --- |
| `admin` | Tout : utilisateurs, restaurants, produits et commandes de tous les restaurants |
| `staff` | Écriture limitée à son propre restaurant (`restaurant_id`) : produits, statut et annulation des commandes |
| `direction` | Lecture seule : consultation des commandes de tous les restaurants |

## Vérifier que ça fonctionne

| URL | Attendu |
| --- | --- |
| `http://127.0.0.1:8000/health` | `{"status": "ok"}` |
| `http://127.0.0.1:8000/docs` | Documentation Swagger interactive |
| `http://127.0.0.1:8000/openapi.json` | Schéma OpenAPI brut |

Sur Windows, préférer `127.0.0.1` à `localhost` (résolution IPv6 parfois capricieuse avec Docker Desktop).

## Exposition publique (ngrok)

L'API tourne en local et est exposée publiquement en HTTPS avec [ngrok](https://ngrok.com/) :

```bash
ngrok http 8000
```

Le plan gratuit de ngrok limite les nouvelles connexions à **100 par minute**.

| Élément | URL |
| --- | --- |
| API publique (ngrok) | `https://<à-compléter>` |
| Swagger | `https://<à-compléter>/docs` |

## Tests

Le script `tests/test_contrat.py` rejoue **135 scénarios** du contrat d'API. Il n'utilise que la bibliothèque standard Python.

```bash
# contre l'API locale
uv run python tests/test_contrat.py

# contre l'API exposée via ngrok
uv run python tests/test_contrat.py https://<url-ngrok>
```

- Il crée ses propres données avec des noms uniques, pour ne pas entrer en collision avec l'existant.
- Il remet le restaurant d'Aix dans son état d'origine et supprime les comptes de test qu'il a créés.
- Via ngrok, il espace ses requêtes pour respecter la limite du plan gratuit.
- Code de sortie `0` si tous les scénarios passent.

## Structure du projet

```
src/
  main.py             # point d'entrée FastAPI, lifespan (création des tables + seeds au démarrage)
  core/               # sécurité (hash, JWT), dépendances d'autorisation, réponses d'erreur Swagger
  db/                 # connexion SQLAlchemy (session par requête), seed (admin, restaurants, produits)
  models/             # modèles SQLAlchemy : restaurant, user, produit, order, order_item
  routers/            # auth & users, restaurants, products, orders
tests/
  test_contrat.py     # 135 scénarios du contrat d'API
Dockerfile
docker-compose.yml
.env.example
pyproject.toml / uv.lock
```

## Modèle de données

5 tables : `restaurants`, `users`, `produits`, `orders`, `order_items`. Les ingrédients d'un produit sont stockés dans une colonne `ARRAY(String)` PostgreSQL.

- Un restaurant a plusieurs utilisateurs, produits et commandes.
- Un produit appartient à un restaurant et porte sa liste d'ingrédients.
- Une commande appartient à un restaurant et contient plusieurs lignes (`order_items`), chacune figeant le prix du produit au moment de la commande.
- Un utilisateur (`users`) a un rôle (`admin`/`staff`/`direction`) et, optionnellement, un restaurant de rattachement (`restaurant_id`, obligatoire pour `staff`).

## État actuel du projet

- [x] Structure du projet et gestion des dépendances (`uv`)
- [x] Conteneurisation (Docker + Docker Compose)
- [x] Connexion SQLAlchemy + PostgreSQL
- [x] Modèles de données et relations
- [x] `GET /health`
- [x] Authentification JWT (`POST /auth/login`)
- [x] Gestion des utilisateurs et rôles (`POST /users` + CRUD complet en bonus)
- [x] Endpoints Restaurants
- [x] Endpoints Produits (CRUD, filtres, autorisation par restaurant)
- [x] Endpoints Commandes
- [x] Documentation Swagger (sections, résumés, codes d'erreur)
- [x] Tests du contrat (`tests/test_contrat.py`)
- [x] Exposition publique en HTTPS (ngrok)

## Commandes utiles

| Commande | Effet |
| --- | --- |
| `docker compose up --build` | reconstruit et lance l'API + PostgreSQL (à refaire après chaque changement de code) |
| `docker compose down` | arrête les conteneurs (les données PostgreSQL sont conservées, volume nommé) |
| `docker compose down -v` | arrête les conteneurs **et supprime les données** (repart de zéro) |
| `docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` | ouvre une session SQL dans le container PostgreSQL |
| `docker compose exec api uv run python -c "..."` | exécute une commande Python ponctuelle dans le container API |
| `TRUNCATE TABLE users RESTART IDENTITY;` (dans `psql`) | vide la table `users` et réinitialise les ID (admin123 sera reseedé au prochain démarrage) |

## Contributeurs

### RIVET Emrick : 
- Structure/dependence
- conteneurisation
- database (SQLAlchemy + PSQL)
- modèles et relations de donées
- routing FASTAPI 
- logique endpoint: Auth, Users, Restaurants, Produits, commandes

### DALLIER Robin
- Création du repository Github