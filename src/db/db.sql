
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS restaurants CASCADE;

DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS order_status CASCADE;
DROP TYPE IF EXISTS pickup_mode CASCADE;


CREATE TYPE user_role AS ENUM ('admin', 'staff', 'direction');
CREATE TYPE order_status AS ENUM ('pending', 'validated', 'preparing', 'ready', 'collected', 'cancelled');
CREATE TYPE pickup_mode AS ENUM ('onsite', 'takeaway');



-- 1. Table RESTAURANTS
CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    is_open BOOLEAN DEFAULT true,
    opening_hours TEXT, -- Peut aussi être un JSONB selon comment vous gérez les horaires
    contact VARCHAR(50)
);

-- 2. Table USERS
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    username VARCHAR(12) UNIQUE NOT NULL CHECK (char_length(username) >= 8 AND char_length(username) <= 12),
    password VARCHAR(255) NOT NULL, -- Stockera le hash généré par bcrypt/argon2
    role user_role NOT NULL,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE SET NULL
);
-- Note: 'restaurant_id' peut être NULL pour un 'admin' ou la 'direction' qui supervisent tout.

-- 3. Table PRODUCTS (Carte)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    image TEXT,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    is_available BOOLEAN DEFAULT true,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    ingredients TEXT[] -- Tableau de chaînes de caractères spécifique à PostgreSQL
);

-- 4. Table ORDERS (Commandes)
CREATE TABLE orders (
   
    order_number VARCHAR(50) PRIMARY KEY, 
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_price NUMERIC(10, 2) NOT NULL,
    status order_status DEFAULT 'pending',
    pickup_mode pickup_mode NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(150) NOT NULL
);

-- 5. Table ORDER_ITEMS (Table de jointure complexe avec quantités)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL REFERENCES orders(order_number) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL
);



-- Insertion des 3 restaurants obligatoires
INSERT INTO restaurants (name, city, address, is_open, opening_hours, contact) VALUES
('Ytasty Crousty Aix', 'Aix-en-Provence', '15 Cours Mirabeau', true, '10:00-23:00', '0401020304'),
('Ytasty Crousty Lyon', 'Lyon', '20 Place Bellecour', true, '11:00-23:30', '0405060708'),
('Ytasty Crousty Paris', 'Paris', '100 Rue de Rivoli', true, '10:00-00:00', '0102030405');

-- Insertion du compte Administrateur
-- ATTENTION: Le mot de passe ci-dessous est un HASH bcrypt généré pour "Admin@123456"
-- Ne JAMAIS stocker le mot de passe en clair.
INSERT INTO users (first_name, last_name, username, password, role, restaurant_id) VALUES
('Admin', 'Super', 'admin123', '$2b$12$L7R2a1vA/.0c.B.dM2o2z.384l0w776g53u9O5x7O.0934G1m2Ww.', 'admin', NULL);
```eof

### Les Jointures (Relations) implémentées :
Les jointures ne se font pas directement dans le schéma de création, mais sont préparées grâce aux **Clés Étrangères (`REFERENCES`)** qui permettront à SQLAlchemy (votre ORM) de faire les `JOIN` très facilement :
1. **`users.restaurant_id` -> `restaurants.id`** : Un utilisateur (staff) appartient à un restaurant.
2. **`products.restaurant_id` -> `restaurants.id`** : Un produit est lié à la carte d'un restaurant spécifique.
3. **`orders.restaurant_id` -> `restaurants.id`** : Une commande est passée dans un restaurant précis.
4. **`order_items.order_number` -> `orders.order_number`** : Lie les lignes de la commande à la commande elle-même.
5. **`order_items.product_id` -> `products.id`** : Lie la ligne de commande au produit commandé.

Vous pourrez utiliser ce script dans votre projet pour initialiser la base avec Docker (en le plaçant dans un dossier `docker-entrypoint-initdb.d/` par exemple) ou le traduire en modèles SQLAlchemy !