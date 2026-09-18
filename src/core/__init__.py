# Centralise l'import de tous les middlewares de core\.
from src.core.security import hashing_mdp, verif_hash

# uv run python -c "from src.core import hashing_mdp, verif_hash; hashed = hashing_mdp('hello'); print(hashed); print(verif_hash('hello', hashed))"