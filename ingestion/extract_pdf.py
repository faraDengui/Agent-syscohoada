"""Extraction du texte du PDF SYSCOHADA et structuration du plan de comptes.

Le PDF source (`data/raw/`) est un texte natif organisé par classe : chaque
classe débute par une ligne "Classe N — <intitulé>", suivie des comptes
(codes à 2, 3 ou 4+ chiffres) sous la forme "<numéro> <intitulé>". Un
intitulé trop long pour tenir sur une ligne se poursuit sur la ou les
lignes suivantes tant qu'elles ne débutent pas par un nouveau code ou une
nouvelle classe.

Sortie :
- data/extracted/<nom>.txt   : texte brut concaténé (une entrée par page)
- data/structured/plan_comptable.json
- data/structured/plan_comptable.csv
"""

import argparse
import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = ROOT / "data" / "raw" / "plan-comptable-syscohada-revise.pdf"
EXTRACTED_DIR = ROOT / "data" / "extracted"
STRUCTURED_DIR = ROOT / "data" / "structured"

CLASS_RE = re.compile(r"^Classe\s+(\d+)\s*[—-]\s*(.+)$")
ACCOUNT_RE = re.compile(r"^(\d{2,6})\s+(.+)$")
FOOTER_RE = re.compile(r"^plan-comptable-ohada\.com\s*—\s*page\s+\d+\s*/\s*\d+$")

# Artefact d'extraction récurrent : la police du PDF source scinde le "T"
# initial de certains mots ("Terrains" -> "T errains", "Taxes" -> "T axes").
LIGATURE_GLITCH_RE = re.compile(r"\bT (?=[a-zéèêàûôîç])")


def extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def save_raw_text(pages: list[str], pdf_path: Path, out_dir: Path = EXTRACTED_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pdf_path.stem}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for i, page_text in enumerate(pages, start=1):
            f.write(f"=== PAGE {i} ===\n")
            f.write(page_text.rstrip() + "\n")
    return out_path


def _clean(text: str) -> str:
    text = LIGATURE_GLITCH_RE.sub("T", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_plan_comptable(pages: list[str]) -> tuple[list[dict], list[dict]]:
    """Parcourt le texte extrait et isole classes + comptes du plan comptable."""
    classes: dict[str, dict] = {}
    accounts: list[dict] = []
    current_target: dict | None = None  # dernier enregistrement en cours de lecture
    started = False  # devient True à la première classe rencontrée (ignore la page de garde)

    for page_num, page_text in enumerate(pages, start=1):
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line or line == "Sommaire" or FOOTER_RE.match(line):
                continue

            class_match = CLASS_RE.match(line)
            if class_match:
                started = True
                numero, intitule = class_match.groups()
                entry = classes.setdefault(
                    numero, {"numero": numero, "intitule": _clean(intitule)}
                )
                entry["intitule"] = _clean(intitule)
                current_target = entry
                continue

            if not started:
                continue

            account_match = ACCOUNT_RE.match(line)
            if account_match:
                numero, intitule = account_match.groups()
                entry = {
                    "numero": numero,
                    "intitule": _clean(intitule),
                    "classe": numero[0],
                    "niveau": len(numero),
                    "page": page_num,
                }
                accounts.append(entry)
                current_target = entry
                continue

            # Ligne de continuation : l'intitulé précédent se poursuit.
            if current_target is not None:
                current_target["intitule"] = _clean(
                    f"{current_target['intitule']} {line}"
                )

    return [classes[k] for k in sorted(classes, key=int)], accounts


def save_structured(
    classes: list[dict], accounts: list[dict], out_dir: Path = STRUCTURED_DIR
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "plan_comptable.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"classes": classes, "comptes": accounts}, f, ensure_ascii=False, indent=2)

    csv_path = out_dir / "plan_comptable.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["numero", "intitule", "classe", "niveau", "page"])
        writer.writeheader()
        writer.writerows(accounts)

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Chemin du PDF source")
    args = parser.parse_args()

    pages = extract_pages(args.pdf)
    raw_path = save_raw_text(pages, args.pdf)
    print(f"Texte brut : {raw_path}")

    classes, accounts = parse_plan_comptable(pages)
    json_path, csv_path = save_structured(classes, accounts)
    print(f"Plan de comptes structuré : {json_path}, {csv_path}")
    print(f"{len(classes)} classes, {len(accounts)} comptes extraits")


if __name__ == "__main__":
    main()
