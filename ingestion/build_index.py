"""Génération des embeddings et indexation locale (Chroma) des chunks.

Utilise l'API d'embedding externe Voyage AI (cf. CLAUDE.md "Stack
technique envisagée") : aucun modèle n'est hébergé localement. Nécessite
VOYAGE_API_KEY dans l'environnement (.env, jamais versionné).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

import chromadb

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "data" / "structured" / "chunks.json"
INDEX_DIR = ROOT / "index" / "chroma_db"
COLLECTION_NAME = "plan_comptable"
MODELE_EMBEDDING = os.environ.get("SYSCOHOADA_EMBED_MODEL", "voyage-3")

EmbedderFn = Callable[[list[str]], list[list[float]]]


def obtenir_embeddings(textes: list[str], modele: str = MODELE_EMBEDDING, client=None) -> list[list[float]]:
    """Appelle l'API Voyage AI pour générer les embeddings des textes fournis."""
    if client is None:
        import voyageai

        client = voyageai.Client()  # lit VOYAGE_API_KEY dans l'environnement
    resultat = client.embed(textes, model=modele, input_type="document")
    return resultat.embeddings


def charger_chunks(chemin: Path = CHUNKS_PATH) -> list[dict]:
    with Path(chemin).open("r", encoding="utf-8") as f:
        return json.load(f)


def construire_index(
    chunks: list[dict],
    chroma_path: Path = INDEX_DIR,
    embedder: EmbedderFn = obtenir_embeddings,
    collection_name: str = COLLECTION_NAME,
):
    """Calcule les embeddings des chunks et les indexe dans une collection Chroma locale."""
    client_chroma = chromadb.PersistentClient(path=str(chroma_path))
    collection = client_chroma.get_or_create_collection(collection_name)

    if not chunks:
        return collection

    embeddings = embedder([chunk["text"] for chunk in chunks])
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        embeddings=embeddings,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )
    return collection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--index", type=Path, default=INDEX_DIR)
    args = parser.parse_args()

    chunks = charger_chunks(args.chunks)
    collection = construire_index(chunks, chroma_path=args.index)
    print(f"{collection.count()} chunks indexés dans {args.index}")


if __name__ == "__main__":
    main()
