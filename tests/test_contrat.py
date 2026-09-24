# Script de test automatique du contrat d'API Ytasty Crousty.
# Rejoue les scénarios de la fiche de tests contre une URL (locale ou ngrok) et affiche un bilan.
#
# Usage :  uv run python tests/test_contrat.py https://squishier-limelight-stimulant.ngrok-free.dev
#          (sans argument : http://localhost:8000)
#
# Aucune dépendance : uniquement la bibliothèque standard de Python.
# Le script crée ses propres comptes, produits et commandes avec des noms uniques,
# remet le restaurant d'Aix dans son état d'origine et supprime ses comptes de test à la fin.
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")

# Le plan gratuit de ngrok limite les nouvelles connexions TCP à 100 par minute, et urllib en ouvre
# une par requête : via ngrok, on espace donc les requêtes (~85/min). En local, aucune pause.
EN_LOCAL = "localhost" in BASE or "127.0.0.1" in BASE
PAUSE = 0 if EN_LOCAL else 0.7

# 4 caractères hexadécimaux : rend les noms uniques à chaque exécution (pas de conflit avec un test précédent)
SUFFIXE = secrets.token_hex(2)
MDP_TEST = "Test@12345678"  # respecte les règles du contrat
ID_INEXISTANT = 999999
NUMERO_INEXISTANT = "YC-XXXXXXXX"

CHAMPS_RESTAURANT = ("id", "name", "city", "address", "is_open", "opening_hours", "contact")
CHAMPS_PRODUIT = ("id", "name", "image", "description", "category", "price",
                  "is_available", "restaurant_id", "ingredients")
CHAMPS_COMMANDE = ("order_number", "restaurant_id", "created_at", "items",
                   "total_price", "status", "pickup_mode", "customer")

bilan = {"ok": 0, "ko": 0}
echecs = []


# ---------- Outils ----------

class Reponse:
    """Réponse HTTP simplifiée : code de statut et corps (JSON décodé, ou texte brut)."""

    def __init__(self, status, corps):
        self.status = status
        self.corps = corps


def requete(methode, chemin, token=None, body=None):
    # Envoie une requête et renvoie toujours une Reponse, y compris pour les codes 4xx/5xx
    headers = {"ngrok-skip-browser-warning": "1"}  # évite la page d'avertissement de ngrok
    donnees = None
    if body is not None:
        donnees = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(BASE + chemin, data=donnees, headers=headers, method=methode)
    time.sleep(PAUSE)
    for tentative in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                status, brut = r.status, r.read()
            break
        except urllib.error.HTTPError as e:
            # urllib lève une exception pour tout code >= 400 : on récupère quand même le code et le corps
            status, brut = e.code, e.read()
            break
        except urllib.error.URLError as e:
            # Coupure réseau ou limite ngrok atteinte : on laisse la fenêtre d'une minute se libérer, puis on réessaie
            if tentative == 2:
                return Reponse(0, f"Connexion impossible : {e.reason}")
            time.sleep(1 if EN_LOCAL else 20)

    try:
        corps = json.loads(brut) if brut else None
    except json.JSONDecodeError:
        corps = brut.decode(errors="replace")  # ex : la page HTML de /docs
    return Reponse(status, corps)


def verifier(nom, rep, codes, condition=None):
    # codes : un code ou un tuple de codes acceptés
    # condition : fonction optionnelle qui reçoit le corps et renvoie True si le contenu est correct
    if isinstance(codes, int):
        codes = (codes,)
    reussi = rep.status in codes
    if reussi and condition is not None:
        try:
            reussi = bool(condition(rep.corps))
        except Exception:  # corps inattendu : clé absente, mauvais type...
            reussi = False

    if reussi:
        bilan["ok"] += 1
        print(f"  OK     {nom}")
    else:
        bilan["ko"] += 1
        attendu = "/".join(str(c) for c in codes)
        message = f"  ECHEC  {nom} -> reçu {rep.status}, attendu {attendu} | {str(rep.corps)[:160]}"
        echecs.append(message)
        print(message)
    return reussi


def section(titre):
    print(f"\n=== {titre} ===")


def proche(a, b):
    # Comparaison de prix tolérant les arrondis des nombres à virgule
    return abs(float(a) - float(b)) < 0.001


def ids_de(liste):
    return {element["id"] for element in liste}


def numeros_de(liste):
    return {commande["order_number"] for commande in liste}


def valeur(rep, cle):
    # Lit une clé du corps si c'est un dictionnaire, sinon None (évite de planter après un échec)
    return rep.corps.get(cle) if isinstance(rep.corps, dict) else None


# ---------- 1. Santé et Swagger ----------

def tester_sante():
    section("1. Santé et Swagger")
    verifier("GET /health", requete("GET", "/health"), 200, lambda c: c == {"status": "ok"})
    verifier("GET /docs", requete("GET", "/docs"), 200)
    rep = requete("GET", "/openapi.json")
    verifier("GET /openapi.json", rep, 200, lambda c: "paths" in c)
    verifier("Schéma de sécurité Bearer déclaré", rep, 200,
             lambda c: any(s.get("scheme", "").lower() == "bearer"
                           for s in c["components"]["securitySchemes"].values()))


# ---------- 2. Authentification ----------

def tester_auth():
    section("2. Authentification")
    rep = requete("POST", "/auth/login", body={"username": "admin123", "password": "Admin@123456"})
    if not verifier("Login admin123 (access_token + bearer)", rep, 200,
                    lambda c: c["access_token"] and c["token_type"] == "bearer"):
        print("\nImpossible de continuer sans token admin.")
        sys.exit(1)
    t_admin = rep.corps["access_token"]

    verifier("Login mauvais mot de passe", requete(
        "POST", "/auth/login", body={"username": "admin123", "password": "Mauvais@12345"}), 401)
    verifier("Login utilisateur inconnu", requete(
        "POST", "/auth/login", body={"username": "inconnu123", "password": "Admin@123456"}), 401)
    verifier("Login champ manquant", requete("POST", "/auth/login", body={"username": "admin123"}), 422)
    verifier("Route protégée sans token", requete("GET", "/users"), 401)
    verifier("Route protégée avec token invalide", requete("GET", "/users", token="abc.def.ghi"), 401)
    verifier("Route protégée avec token admin", requete("GET", "/users", token=t_admin), 200)
    return t_admin


# ---------- Préparation : ids des restaurants ----------

def trouver_restaurants():
    section("Préparation : restaurants du contrat")
    rep = requete("GET", "/restaurants")
    noms = {"Ytasty Crousty Aix", "Ytasty Crousty Lyon", "Ytasty Crousty Paris"}
    if not verifier("Les 3 restaurants du contrat existent", rep, 200,
                    lambda c: noms <= {r["name"] for r in c}):
        print("\nImpossible de continuer sans les restaurants du seed.")
        sys.exit(1)
    par_nom = {r["name"]: r["id"] for r in rep.corps}
    return par_nom["Ytasty Crousty Aix"], par_nom["Ytasty Crousty Lyon"]


# ---------- 3. Utilisateurs ----------

def creer_compte(t_admin, username, role, restaurant_id):
    body = {"first_name": "Test", "last_name": "Auto", "username": username,
            "password": MDP_TEST, "role": role, "restaurant_id": restaurant_id}
    rep = requete("POST", "/users", t_admin, body)
    verifier(f"Création {role} {username} (sans mot de passe dans la réponse)", rep, 201,
             lambda c: c["username"] == username and c["role"] == role
             and "password" not in c and "hashed_password" not in c)
    return valeur(rep, "id")


def connexion(username):
    rep = requete("POST", "/auth/login", body={"username": username, "password": MDP_TEST})
    verifier(f"Login {username}", rep, 200, lambda c: c["access_token"])
    return valeur(rep, "access_token")


def tester_utilisateurs(t_admin, id_aix, id_lyon):
    section("3. Utilisateurs")
    noms = {"aix": f"aix{SUFFIXE}test", "lyon": f"lyon{SUFFIXE}tst", "dir": f"dir{SUFFIXE}test"}
    ids_users = [
        creer_compte(t_admin, noms["aix"], "staff", id_aix),
        creer_compte(t_admin, noms["lyon"], "staff", id_lyon),
        creer_compte(t_admin, noms["dir"], "direction", None),
    ]
    t_aix, t_lyon, t_dir = connexion(noms["aix"]), connexion(noms["lyon"]), connexion(noms["dir"])

    # Chaque cas modifie un seul champ d'un body valide : le refus vient forcément de ce champ
    base = {"first_name": "Test", "last_name": "Auto", "username": f"v{SUFFIXE}abc",
            "password": MDP_TEST, "role": "staff", "restaurant_id": id_aix}
    cas = [
        ("username de 7 caractères", {"username": "court12"}, 422),
        ("username de 13 caractères", {"username": "beaucouptrop1"}, 422),
        ("username non alphanumérique", {"username": "sam_staff1"}, 422),
        ("mot de passe trop court", {"password": "Court@1"}, 422),
        ("mot de passe sans chiffre", {"password": "Test@abcdefgh"}, 422),
        ("mot de passe sans majuscule", {"password": "test@12345678"}, 422),
        ("mot de passe sans caractère spécial", {"password": "Test123456789"}, 422),
        ("rôle inconnu", {"role": "chef"}, 422),
        ("staff sans restaurant", {"restaurant_id": None}, 400),
        ("restaurant inexistant", {"restaurant_id": ID_INEXISTANT}, 400),
        ("username déjà pris", {"username": noms["aix"]}, 400),
    ]
    for nom, modification, code in cas:
        verifier(f"POST /users refusé : {nom}", requete("POST", "/users", t_admin, base | modification), code)

    nouveau = base | {"username": f"x{SUFFIXE}abc"}
    verifier("POST /users sans token", requete("POST", "/users", body=nouveau), 401)
    verifier("POST /users par un staff", requete("POST", "/users", t_aix, nouveau), 403)
    verifier("POST /users par la direction", requete("POST", "/users", t_dir, nouveau), 403)

    return t_aix, t_lyon, t_dir, [i for i in ids_users if i is not None]


# ---------- 4. Restaurants ----------

def tester_restaurants(t_admin, t_aix, t_dir, id_aix):
    section("4. Restaurants")
    verifier("GET /restaurants (champs du contrat)", requete("GET", "/restaurants"), 200,
             lambda c: all(k in r for r in c for k in CHAMPS_RESTAURANT))
    avant = requete("GET", f"/restaurants/{id_aix}")
    verifier("GET /restaurants/{id}", avant, 200, lambda c: c["id"] == id_aix)
    verifier("GET /restaurants/{id} inexistant", requete("GET", f"/restaurants/{ID_INEXISTANT}"), 404)
    verifier("GET /restaurants/abc", requete("GET", "/restaurants/abc"), 422)

    chemin = f"/restaurants/{id_aix}"
    try:
        corps_contrat = {"address": "10 rue de Test", "contact": "0102030405"}
        verifier("PATCH body du contrat (admin)", requete("PATCH", chemin, t_admin, corps_contrat), 200,
                 lambda c: c["address"] == "10 rue de Test" and c["contact"] == "0102030405")
        verifier("GET après PATCH : modifications enregistrées", requete("GET", chemin), 200,
                 lambda c: c["address"] == "10 rue de Test")
        verifier("PATCH partiel : seul le contact change",
                 requete("PATCH", chemin, t_admin, {"contact": "0600000000"}), 200,
                 lambda c: c["contact"] == "0600000000" and c["address"] == "10 rue de Test")
        verifier("PATCH sans token", requete("PATCH", chemin, body={"contact": "0600000000"}), 401)
        verifier("PATCH par un staff", requete("PATCH", chemin, t_aix, {"contact": "0600000000"}), 403)
        verifier("PATCH par la direction", requete("PATCH", chemin, t_dir, {"contact": "0600000000"}), 403)
        verifier("PATCH restaurant inexistant",
                 requete("PATCH", f"/restaurants/{ID_INEXISTANT}", t_admin, {"contact": "0600000000"}), 404)

        dispo = f"{chemin}/availability"
        verifier("Fermeture (admin)", requete("PATCH", dispo, t_admin, {"is_open": False}), 200,
                 lambda c: c["is_open"] is False)
        verifier("Fermeture une seconde fois (idempotent)",
                 requete("PATCH", dispo, t_admin, {"is_open": False}), 200)
        verifier("Availability body vide", requete("PATCH", dispo, t_admin, {}), 422)
        verifier("Availability valeur invalide", requete("PATCH", dispo, t_admin, {"is_open": "peut-etre"}), 422)
        verifier("Availability par un staff", requete("PATCH", dispo, t_aix, {"is_open": True}), 403)

        verifier("POST /restaurants avec un nom existant (bonus)", requete(
            "POST", "/restaurants", t_admin,
            {"name": "Ytasty Crousty Aix", "city": "Aix", "address": "x", "opening_hours": "x", "contact": "x"}), 400)
    finally:
        # Remise en état du restaurant, même si un test a échoué entre-temps
        requete("PATCH", f"{chemin}/availability", t_admin, {"is_open": True})
        if isinstance(avant.corps, dict):
            requete("PATCH", chemin, t_admin,
                    {"address": avant.corps["address"], "contact": avant.corps["contact"]})


# ---------- 5. Produits ----------

def body_produit(nom, restaurant_id, prix=9.9, categorie="burgers"):
    return {"name": nom, "image": "https://example.com/burger.jpg", "description": "Produit créé pour les tests",
            "category": categorie, "price": prix, "is_available": True,
            "restaurant_id": restaurant_id, "ingredients": ["pain", "poulet"]}


def creer_produit(nom_test, token, body):
    rep = requete("POST", "/products", token, body)
    verifier(nom_test, rep, 201, lambda c: all(k in c for k in CHAMPS_PRODUIT)
             and proche(c["price"], body["price"]) and c["ingredients"] == body["ingredients"])
    return valeur(rep, "id")


def tester_produits(t_admin, t_aix, t_lyon, t_dir, id_aix, id_lyon):
    section("5. Produits")
    nom_p1 = f"Burger Test {SUFFIXE}"
    p1 = creer_produit("POST body du contrat (admin)", t_admin, body_produit(nom_p1, id_aix))
    p_frites = creer_produit("POST second produit Aix (admin)", t_admin,
                             body_produit(f"Frites {SUFFIXE}", id_aix, prix=3.5, categorie="sides"))
    p_lyon = creer_produit("POST produit Lyon (admin)", t_admin, body_produit(f"Wrap Lyon {SUFFIXE}", id_lyon))
    p_staff = creer_produit("POST par le staff sur son restaurant", t_aix,
                            body_produit(f"Staff {SUFFIXE}", id_aix))

    refus = body_produit(f"Refus {SUFFIXE}", id_aix)
    verifier("POST staff sur un autre restaurant", requete("POST", "/products", t_aix, refus | {"restaurant_id": id_lyon}), 403)
    verifier("POST par la direction", requete("POST", "/products", t_dir, refus), 403)
    verifier("POST sans token", requete("POST", "/products", body=refus), 401)
    verifier("POST restaurant inexistant", requete("POST", "/products", t_admin, refus | {"restaurant_id": ID_INEXISTANT}), 400)
    verifier("POST prix négatif", requete("POST", "/products", t_admin, refus | {"price": -5}), 422)
    verifier("POST prix nul", requete("POST", "/products", t_admin, refus | {"price": 0}), 422)
    sans_nom = {k: v for k, v in refus.items() if k != "name"}
    verifier("POST sans nom", requete("POST", "/products", t_admin, sans_nom), 422)

    # Filtres (sur les produits créés ci-dessus, identifiés par leur id)
    def lister(**filtres):
        return requete("GET", "/products?" + urlencode(filtres))

    verifier("GET /products", requete("GET", "/products"), 200, lambda c: p1 in ids_de(c))
    verifier("Filtre category", lister(category="burgers"), 200,
             lambda c: p1 in ids_de(c) and all(p["category"] == "burgers" for p in c))
    verifier("Filtre q (nom, insensible à la casse)", lister(q=nom_p1.upper()), 200, lambda c: ids_de(c) == {p1})
    verifier("Filtre q (ingrédients)", lister(q="poulet"), 200, lambda c: p1 in ids_de(c))
    verifier("Filtre restaurant_id", lister(restaurant_id=id_aix), 200,
             lambda c: p1 in ids_de(c) and p_lyon not in ids_de(c) and all(p["restaurant_id"] == id_aix for p in c))
    verifier("Filtre is_available", lister(is_available="true"), 200, lambda c: all(p["is_available"] for p in c))
    verifier("Filtres combinés", lister(q=SUFFIXE, restaurant_id=id_lyon, category="burgers"), 200,
             lambda c: ids_de(c) == {p_lyon})
    verifier("Filtre sans résultat : 200 et liste vide", lister(category=f"inexistante{SUFFIXE}"), 200, lambda c: c == [])
    verifier("Filtre is_available invalide", lister(is_available="peut-etre"), 422)
    verifier("GET /products/{id}", requete("GET", f"/products/{p1}"), 200, lambda c: c["id"] == p1)
    verifier("GET /products/{id} inexistant", requete("GET", f"/products/{ID_INEXISTANT}"), 404)

    # Modification
    verifier("PATCH prix (admin)", requete("PATCH", f"/products/{p1}", t_admin, {"price": 10.9}), 200,
             lambda c: proche(c["price"], 10.9) and c["name"] == nom_p1)
    verifier("PATCH par le staff sur son restaurant",
             requete("PATCH", f"/products/{p1}", t_aix, {"description": "Modifié par le staff"}), 200)
    verifier("PATCH staff sur un produit d'un autre restaurant",
             requete("PATCH", f"/products/{p_lyon}", t_aix, {"price": 0.5}), 403)
    verifier("PATCH staff en changeant restaurant_id dans le body",
             requete("PATCH", f"/products/{p_lyon}", t_aix, {"restaurant_id": id_aix, "price": 0.5}), 403)
    verifier("PATCH par la direction", requete("PATCH", f"/products/{p1}", t_dir, {"price": 1}), 403)
    verifier("PATCH sans token", requete("PATCH", f"/products/{p1}", body={"price": 1}), 401)
    verifier("PATCH prix négatif", requete("PATCH", f"/products/{p1}", t_admin, {"price": -5}), 422)
    verifier("PATCH produit inexistant", requete("PATCH", f"/products/{ID_INEXISTANT}", t_admin, {"price": 1}), 404)

    # Disponibilité
    dispo = f"/products/{p_staff}/availability"
    verifier("Indisponible (staff)", requete("PATCH", dispo, t_aix, {"is_available": False}), 200,
             lambda c: c["is_available"] is False)
    verifier("Indisponible une seconde fois (idempotent)", requete("PATCH", dispo, t_aix, {"is_available": False}), 200)
    verifier("Availability body vide", requete("PATCH", dispo, t_admin, {}), 422)
    verifier("Availability staff sur un autre restaurant",
             requete("PATCH", f"/products/{p_lyon}/availability", t_aix, {"is_available": False}), 403)

    return p1, p_frites, p_lyon, p_staff


# ---------- 6. Commandes ----------

def tester_commandes(t_admin, t_aix, t_lyon, t_dir, id_aix, id_lyon, p1, p_frites, p_lyon, p_staff):
    section("6. Commandes")
    commande = {"restaurant_id": id_aix, "items": [{"product_id": p1, "quantity": 2}], "pickup_mode": "takeaway",
                "customer": {"name": "Client Test", "email": "client@example.com"}}

    rep = requete("POST", "/orders", body=commande)
    verifier("POST /orders (public, total calculé par le serveur)", rep, 201,
             lambda c: all(k in c for k in CHAMPS_COMMANDE) and proche(c["total_price"], 21.8)
             and c["status"] == "pending" and c["customer"]["email"] == "client@example.com"
             and c["items"][0]["product_id"] == p1)
    n1 = valeur(rep, "order_number")
    n2 = valeur(requete("POST", "/orders", body=commande), "order_number")
    verifier("Deux commandes ont des numéros différents", Reponse(201, None), 201, lambda _: n1 and n2 and n1 != n2)

    plusieurs = commande | {"items": [{"product_id": p1, "quantity": 2}, {"product_id": p_frites, "quantity": 1}]}
    verifier("Commande de plusieurs produits", requete("POST", "/orders", body=plusieurs), 201,
             lambda c: proche(c["total_price"], 25.3))
    verifier("Prix envoyé par le client ignoré", requete("POST", "/orders", body=commande | {"total_price": 0.01}), 201,
             lambda c: proche(c["total_price"], 21.8))

    def avec_item(product_id, quantity=1):
        return commande | {"items": [{"product_id": product_id, "quantity": quantity}]}

    verifier("Refus : produit inexistant", requete("POST", "/orders", body=avec_item(ID_INEXISTANT)), 400)
    verifier("Refus : produit d'un autre restaurant", requete("POST", "/orders", body=avec_item(p_lyon)), 400)
    verifier("Refus : produit indisponible", requete("POST", "/orders", body=avec_item(p_staff)), 400)
    verifier("Refus : restaurant inexistant", requete("POST", "/orders", body=commande | {"restaurant_id": ID_INEXISTANT}), 400)
    verifier("Refus : quantité 0", requete("POST", "/orders", body=avec_item(p1, 0)), (400, 422))
    verifier("Refus : quantité négative", requete("POST", "/orders", body=avec_item(p1, -1)), (400, 422))
    verifier("Refus : aucun produit", requete("POST", "/orders", body=commande | {"items": []}), (400, 422))
    verifier("Refus : mode de retrait invalide", requete("POST", "/orders", body=commande | {"pickup_mode": "livraison"}), 422)
    verifier("Refus : email invalide", requete(
        "POST", "/orders", body=commande | {"customer": {"name": "Client", "email": "pas-un-email"}}), 422)

    dispo = f"/restaurants/{id_aix}/availability"
    try:
        requete("PATCH", dispo, t_admin, {"is_open": False})
        verifier("Refus : restaurant fermé", requete("POST", "/orders", body=commande), 400)
    finally:
        requete("PATCH", dispo, t_admin, {"is_open": True})

    # Prix figé : un changement de prix du produit ne modifie pas une commande passée
    requete("PATCH", f"/products/{p1}", t_admin, {"price": 12.5})
    verifier("Prix figé dans la commande", requete("GET", f"/orders/{n1}"), 200,
             lambda c: proche(c["items"][0]["unit_price"], 10.9) and proche(c["total_price"], 21.8))

    # Suivi et liste
    verifier("GET /orders/{n} (public)", requete("GET", f"/orders/{n1}"), 200, lambda c: c["order_number"] == n1)
    verifier("GET /orders/{n} inexistant", requete("GET", f"/orders/{NUMERO_INEXISTANT}"), 404)
    liste = f"/restaurants/{id_aix}/orders"
    verifier("Liste sans token", requete("GET", liste), 401)
    verifier("Liste par le staff du restaurant (plus récentes en premier)", requete("GET", liste, t_aix), 200,
             lambda c: {n1, n2} <= numeros_de(c)
             and [o["created_at"] for o in c] == sorted((o["created_at"] for o in c), reverse=True))
    verifier("Liste par l'admin", requete("GET", liste, t_admin), 200, lambda c: n1 in numeros_de(c))
    verifier("Liste par la direction", requete("GET", liste, t_dir), 200, lambda c: n1 in numeros_de(c))
    verifier("Liste d'un autre restaurant par la direction", requete("GET", f"/restaurants/{id_lyon}/orders", t_dir), 200)
    verifier("Liste par le staff d'un autre restaurant", requete("GET", liste, t_lyon), 403)
    verifier("Liste d'un restaurant inexistant", requete("GET", f"/restaurants/{ID_INEXISTANT}/orders", t_admin), 404)
    verifier("Filtre ?status=pending", requete("GET", f"{liste}?status=pending", t_aix), 200,
             lambda c: n1 in numeros_de(c) and all(o["status"] == "pending" for o in c))
    verifier("Filtre ?status invalide", requete("GET", f"{liste}?status=inconnu", t_aix), 422)

    # Statut
    def statut(numero, token, valeur_statut):
        return requete("PATCH", f"/orders/{numero}/status", token, {"status": valeur_statut})

    verifier("Statut preparing (staff)", statut(n1, t_aix, "preparing"), 200, lambda c: c["status"] == "preparing")
    verifier("Statut sans token", statut(n1, None, "ready"), 401)
    verifier("Statut par la direction", statut(n1, t_dir, "ready"), 403)
    verifier("Statut par le staff d'un autre restaurant", statut(n1, t_lyon, "ready"), 403)
    verifier("Statut invalide", statut(n1, t_aix, "livree"), 422)
    verifier("Statut d'une commande inexistante", statut(NUMERO_INEXISTANT, t_admin, "ready"), 404)
    verifier("Statut ready (admin)", statut(n1, t_admin, "ready"), 200)
    verifier("Statut collected", statut(n1, t_aix, "collected"), 200)
    verifier("Sortir d'un statut final refusé", statut(n1, t_aix, "preparing"), 400)
    verifier("Même statut final (idempotent)", statut(n1, t_aix, "collected"), 200)

    # Annulation
    annuler = f"/orders/{n2}/cancel"
    verifier("Annulation sans token", requete("POST", annuler), 401)
    verifier("Annulation par la direction", requete("POST", annuler, t_dir), 403)
    verifier("Annulation par le staff d'un autre restaurant", requete("POST", annuler, t_lyon), 403)
    verifier("Annulation (staff)", requete("POST", annuler, t_aix), 200, lambda c: c["status"] == "cancelled")
    verifier("Annulation une seconde fois (idempotent)", requete("POST", annuler, t_aix), 200)
    verifier("Annulation d'une commande retirée", requete("POST", f"/orders/{n1}/cancel", t_admin), 400)
    verifier("Changer le statut d'une commande annulée", statut(n2, t_aix, "pending"), 400)
    verifier("Annulation d'une commande inexistante", requete("POST", f"/orders/{NUMERO_INEXISTANT}/cancel", t_admin), 404)


# ---------- Suppressions et nettoyage ----------

def tester_suppressions(t_admin, t_aix, t_lyon, t_dir, p1, p_lyon, p_staff):
    section("7. Suppression des produits")
    verifier("DELETE d'un produit déjà commandé", requete("DELETE", f"/products/{p1}", t_admin), 400)
    verifier("DELETE staff sur un autre restaurant", requete("DELETE", f"/products/{p_staff}", t_lyon), 403)
    verifier("DELETE par la direction", requete("DELETE", f"/products/{p_staff}", t_dir), 403)
    verifier("DELETE sans token", requete("DELETE", f"/products/{p_staff}"), 401)
    verifier("DELETE par le staff sur son restaurant", requete("DELETE", f"/products/{p_staff}", t_aix), (200, 204))
    verifier("GET après DELETE", requete("GET", f"/products/{p_staff}"), 404)
    verifier("DELETE (admin)", requete("DELETE", f"/products/{p_lyon}", t_admin), (200, 204))
    verifier("DELETE produit inexistant", requete("DELETE", f"/products/{ID_INEXISTANT}", t_admin), 404)


def nettoyer(t_admin, ids_users):
    # Supprime les comptes de test via la route bonus DELETE /users/{id} (hors bilan)
    for user_id in ids_users:
        requete("DELETE", f"/users/{user_id}", t_admin)


# ---------- Programme principal ----------

def main():
    print(f"Tests du contrat sur {BASE} (suffixe {SUFFIXE})")
    rep = requete("GET", "/health")
    if rep.status == 0:  # code 0 = aucune réponse du serveur (voir requete)
        print(f"API injoignable : {rep.corps}")
        sys.exit(2)

    tester_sante()
    t_admin = tester_auth()
    id_aix, id_lyon = trouver_restaurants()
    t_aix, t_lyon, t_dir, ids_users = tester_utilisateurs(t_admin, id_aix, id_lyon)
    try:
        tester_restaurants(t_admin, t_aix, t_dir, id_aix)
        p1, p_frites, p_lyon, p_staff = tester_produits(t_admin, t_aix, t_lyon, t_dir, id_aix, id_lyon)
        tester_commandes(t_admin, t_aix, t_lyon, t_dir, id_aix, id_lyon, p1, p_frites, p_lyon, p_staff)
        tester_suppressions(t_admin, t_aix, t_lyon, t_dir, p1, p_lyon, p_staff)
    finally:
        nettoyer(t_admin, ids_users)

    total = bilan["ok"] + bilan["ko"]
    print(f"\n=== Bilan : {bilan['ok']}/{total} tests réussis ===")
    if echecs:
        print("\nÉchecs :")
        for message in echecs:
            print(message)
    sys.exit(1 if echecs else 0)  # code de sortie non nul si au moins un échec


if __name__ == "__main__":
    main()