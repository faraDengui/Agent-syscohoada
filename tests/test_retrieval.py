import pytest

from agent.retriever import extraire_numeros_comptes, rechercher_compte, rechercher_mot_cle
from agent.rules_engine import PlanComptable


@pytest.fixture(scope="module")
def plan() -> PlanComptable:
    return PlanComptable.charger()


def test_extraire_numeros_comptes_ignore_le_texte():
    # "5" (trop court) et "12345678" (trop long, jamais suivi d'une frontière
    # de mot avant 6 chiffres) ne sont pas retenus.
    numeros = extraire_numeros_comptes("Le compte 411 et le compte 701, pas 5 ni 12345678.")
    assert numeros == ["411", "701"]


def test_rechercher_compte_exact(plan):
    compte = rechercher_compte("411", plan)
    assert compte == {"numero": "411", "intitule": "CLIENTS"}


def test_rechercher_compte_retombe_sur_le_parent(plan):
    # 4111 n'est pas listé, mais 411 (CLIENTS) l'est.
    compte = rechercher_compte("41199", plan)
    assert compte["numero"] == "411"


def test_rechercher_compte_inexistant_renvoie_none(plan):
    assert rechercher_compte("0500", plan) is None


def test_rechercher_mot_cle_trouve_le_compte_pertinent(plan):
    resultats = rechercher_mot_cle("Quel compte pour les ventes de marchandises ?", plan)
    numeros = [c["numero"] for c in resultats]
    assert "701" in numeros
    assert numeros[0] == "701"  # meilleur score en tête


def test_rechercher_mot_cle_sans_mot_significatif_est_vide(plan):
    assert rechercher_mot_cle("Le compte pour ceci ?", plan) == []
