# Réponses d'erreur réutilisables pour la documentation Swagger (paramètre responses= des routes)
from pydantic import BaseModel


class ErreurOut(BaseModel):
    detail: str  # format des erreurs renvoyées par HTTPException

ERR_400 = {400: {"model": ErreurOut, "description": "Requête métier invalide"}}
ERR_401 = {401: {"model": ErreurOut, "description": "Non authentifié (token absent ou invalide)"}}
ERR_403 = {403: {"model": ErreurOut, "description": "Authentifié mais non autorisé"}}
ERR_404 = {404: {"model": ErreurOut, "description": "Ressource inexistante"}}

# Combinaisons fréquentes (| fusionne deux dictionnaires)
REPONSES_ECRITURE = ERR_400 | ERR_401 | ERR_403 | ERR_404  # PATCH, DELETE, POST sur une ressource existante
REPONSES_CREATION = ERR_400 | ERR_401 | ERR_403            # POST /users, /products, /restaurants
REPONSES_LECTURE = ERR_404                                 # GET publics d'une ressource précise
REPONSES_LECTURE_PROTEGEE = ERR_401 | ERR_403 | ERR_404    # GET réservés au personnel