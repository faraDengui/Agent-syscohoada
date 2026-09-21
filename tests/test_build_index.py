from ingestion.build_index import construire_index

CHUNKS_EXEMPLE = [
    {
        "id": "classe-1",
        "text": "Classe 1 — Comptes de ressources durables\n\n11 Réserves",
        "metadata": {"type": "classe", "classe": "1", "intitule": "Comptes de ressources durables", "nb_comptes": 1},
    },
    {
        "id": "classe-2",
        "text": "Classe 2 — Comptes d'actif immobilisé\n\n21 Immobilisations incorporelles",
        "metadata": {"type": "classe", "classe": "2", "intitule": "Comptes d'actif immobilisé", "nb_comptes": 1},
    },
]


def _faux_embedder(appels):
    def embedder(textes):
        appels.append(textes)
        return [[float(len(t) % 7), 0.0, 1.0] for t in textes]

    return embedder


def test_construire_index_indexe_tous_les_chunks(tmp_path):
    appels = []
    collection = construire_index(CHUNKS_EXEMPLE, chroma_path=tmp_path, embedder=_faux_embedder(appels))

    assert collection.count() == 2
    assert len(appels) == 1
    assert appels[0] == [c["text"] for c in CHUNKS_EXEMPLE]


def test_construire_index_ids_documents_et_metadonnees(tmp_path):
    appels = []
    collection = construire_index(CHUNKS_EXEMPLE, chroma_path=tmp_path, embedder=_faux_embedder(appels))

    resultat = collection.get(ids=["classe-1"])
    assert resultat["documents"][0] == CHUNKS_EXEMPLE[0]["text"]
    assert resultat["metadatas"][0] == CHUNKS_EXEMPLE[0]["metadata"]


def test_construire_index_est_idempotent_via_upsert(tmp_path):
    appels = []
    embedder = _faux_embedder(appels)
    construire_index(CHUNKS_EXEMPLE, chroma_path=tmp_path, embedder=embedder)
    collection = construire_index(CHUNKS_EXEMPLE, chroma_path=tmp_path, embedder=embedder)

    assert collection.count() == 2  # pas de doublons au second passage


def test_construire_index_liste_vide_ne_plante_pas_et_n_appelle_pas_l_embedder(tmp_path):
    appels = []
    collection = construire_index([], chroma_path=tmp_path, embedder=_faux_embedder(appels))

    assert collection.count() == 0
    assert appels == []
