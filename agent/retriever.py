"""Recherche dans le plan de comptes structuré.

Le plan de comptes se prête à une recherche exacte par numéro de compte et
à une recherche mot-clé sur les intitulés (cf. CLAUDE.md, "Séparation
données structurées / narratives"). La recherche sémantique par embeddings
sur les normes narratives sera ajoutée par index/build_index.py une fois ce
corpus disponible (voir CLAUDE.md § "À faire") ; elle n'existe pas encore,
donc ce module ne fait volontairement que de la recherche exacte/mot-clé.
"""

from __future__ import annotations

import re
import unicodedata

from agent.rules_engine import PlanComptable

_NUMERO_RE = re.compile(r"\b\d{2,6}\b")
_MOT_RE = re.compile(r"[a-zA-Zàâäéèêëïîôöùûüç']+")

_MOTS_VIDES = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou", "en",
    "pour", "sur", "dans", "par", "avec", "quel", "quels", "quelle",
    "quelles", "comment", "est", "sont", "que", "qui", "quoi", "ce",
    "cette", "compte", "comptes", "numero", "numéro",
}


def extraire_numeros_comptes(texte: str) -> list[str]:
    """Extrait les numéros de compte potentiels (2 à 6 chiffres) cités dans un texte."""
    return _NUMERO_RE.findall(texte)


def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    return sans_accents.lower()


def _mots_significatifs(texte: str) -> set[str]:
    mots = (_normaliser(m) for m in _MOT_RE.findall(texte))
    return {m for m in mots if len(m) >= 4 and m not in _MOTS_VIDES}


def rechercher_compte(numero: str, plan: PlanComptable) -> dict | None:
    """Recherche exacte d'un compte par numéro.

    Si le numéro exact n'est pas répertorié, retombe sur le compte parent
    le plus proche (préfixe le plus long connu) plutôt que de ne rien
    renvoyer.
    """
    if plan.existe(numero):
        return {"numero": numero, "intitule": plan.intitule(numero)}
    for longueur in range(len(numero) - 1, 1, -1):
        prefixe = numero[:longueur]
        if plan.existe(prefixe):
            return {"numero": prefixe, "intitule": plan.intitule(prefixe)}
    return None


def rechercher_mot_cle(texte: str, plan: PlanComptable, limite: int = 10) -> list[dict]:
    """Renvoie les comptes dont l'intitulé partage des mots significatifs
    avec `texte`, triés par nombre de mots en commun (score décroissant)."""
    mots_question = _mots_significatifs(texte)
    if not mots_question:
        return []

    scores = []
    for compte in plan.tous():
        score = len(mots_question & _mots_significatifs(compte["intitule"]))
        if score > 0:
            scores.append((score, compte))

    scores.sort(key=lambda paire: (-paire[0], len(paire[1]["numero"])))
    return [compte for _, compte in scores[:limite]]
