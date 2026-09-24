# Centralise l'import de tous les middlewares de core\.
from src.core.security import hashing_mdp, verif_hash, creer_jwt, verif_jwt
from src.core.deps import get_current_user, require_role, verifier_acces_restaurant, verifier_lecture_restaurant
from src.core.docs import ERR_400, ERR_401, ERR_403, REPONSES_ECRITURE, REPONSES_CREATION, REPONSES_LECTURE, REPONSES_LECTURE_PROTEGEE

# uv run python -c "from src.core import hashing_mdp, verif_hash; hashed = hashing_mdp('hello'); print(hashed); print(verif_hash('hello', hashed))"