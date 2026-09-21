"""Découpage du contenu en chunks logiques en vue de l'indexation.

Pour l'instant, seul le plan de comptes structuré
(data/structured/plan_comptable.json) est disponible : un chunk = une
classe de comptes, conformément à CLAUDE.md ("une norme = un chunk, une
classe de comptes = un chunk"). Le découpage des normes narratives sera
ajouté ici une fois ce corpus ingéré (voir CLAUDE.md § "À faire") ; il
n'existe pas encore.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_COMPTABLE_PATH = ROOT / "data" / "structured" / "plan_comptable.json"
CHUNKS_PATH = ROOT / "data" / "structured" / "chunks.json"


def chunker_plan_comptable(plan_comptable: dict) -> list[dict]:
    """Construit un chunk par classe : son intitulé et tous ses comptes."""
    comptes_par_classe: dict[str, list[dict]] = {}
    for compte in plan_comptable["comptes"]:
        comptes_par_classe.setdefault(compte["classe"], []).append(compte)

    chunks = []
    for classe in plan_comptable["classes"]:
        numero = classe["numero"]
        # Ordre du document conservé (déjà groupé par niveau : rubriques à 2
        # chiffres, puis comptes à 3, puis sous-comptes à 4+), pas un tri
        # alphabétique qui casserait cette hiérarchie ("11" > "101" en texte).
        comptes = comptes_par_classe.get(numero, [])
        lignes_comptes = "\n".join(f"{compte['numero']} {compte['intitule']}" for compte in comptes)
        texte = f"Classe {numero} — {classe['intitule']}\n\n{lignes_comptes}"
        chunks.append(
            {
                "id": f"classe-{numero}",
                "text": texte,
                "metadata": {
                    "type": "classe",
                    "classe": numero,
                    "intitule": classe["intitule"],
                    "nb_comptes": len(comptes),
                },
            }
        )
    return chunks


def sauvegarder_chunks(chunks: list[dict], out_path: Path = CHUNKS_PATH) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    return out_path


def main() -> None:
    with PLAN_COMPTABLE_PATH.open("r", encoding="utf-8") as f:
        plan_comptable = json.load(f)

    chunks = chunker_plan_comptable(plan_comptable)
    out_path = sauvegarder_chunks(chunks)
    print(f"{len(chunks)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
