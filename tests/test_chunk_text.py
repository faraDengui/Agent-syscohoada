from ingestion.chunk_text import chunker_plan_comptable

PLAN_EXEMPLE = {
    "classes": [
        {"numero": "1", "intitule": "Comptes de ressources durables"},
        {"numero": "2", "intitule": "Comptes d'actif immobilisé"},
    ],
    "comptes": [
        {"numero": "11", "intitule": "Réserves", "classe": "1", "niveau": 2},
        {"numero": "101", "intitule": "Capital social", "classe": "1", "niveau": 3},
        {"numero": "1011", "intitule": "Capital souscrit, non appelé", "classe": "1", "niveau": 4},
        {"numero": "21", "intitule": "Immobilisations incorporelles", "classe": "2", "niveau": 2},
    ],
}


def test_un_chunk_par_classe():
    chunks = chunker_plan_comptable(PLAN_EXEMPLE)
    assert [c["id"] for c in chunks] == ["classe-1", "classe-2"]


def test_chunk_contient_intitule_classe_et_tous_ses_comptes():
    chunks = chunker_plan_comptable(PLAN_EXEMPLE)
    texte_classe_1 = chunks[0]["text"]
    assert "Classe 1 — Comptes de ressources durables" in texte_classe_1
    assert "11 Réserves" in texte_classe_1
    assert "101 Capital social" in texte_classe_1
    assert "1011 Capital souscrit, non appelé" in texte_classe_1
    assert "Immobilisations incorporelles" not in texte_classe_1


def test_ordre_hierarchique_preserve_pas_alphabetique():
    # "11" doit précéder "101" (ordre du document), pas l'inverse comme le
    # donnerait un tri alphabétique sur les chaînes de caractères.
    chunks = chunker_plan_comptable(PLAN_EXEMPLE)
    texte = chunks[0]["text"]
    assert texte.index("11 Réserves") < texte.index("101 Capital social")


def test_metadata_du_chunk():
    chunks = chunker_plan_comptable(PLAN_EXEMPLE)
    assert chunks[0]["metadata"] == {
        "type": "classe",
        "classe": "1",
        "intitule": "Comptes de ressources durables",
        "nb_comptes": 3,
    }


def test_classe_sans_compte_produit_un_chunk_vide_mais_present():
    plan = {
        "classes": [{"numero": "9", "intitule": "Comptes hors bilan"}],
        "comptes": [],
    }
    chunks = chunker_plan_comptable(plan)
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["nb_comptes"] == 0
