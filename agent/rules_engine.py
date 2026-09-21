"""Règles de validation déterministes pour les écritures comptables SYSCOHADA.

Tous les contrôles définis ici (équilibre débit/crédit, imputation) sont du
code vérifiable : conformément à CLAUDE.md, aucun calcul ni montant n'est
jamais délégué au LLM. Le LLM peut s'appuyer sur ce module pour valider une
écriture qu'il propose, mais ne se substitue jamais à lui.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN_COMPTABLE = ROOT / "data" / "structured" / "plan_comptable.json"


def _to_decimal(valeur: Decimal | int | str) -> Decimal:
    if isinstance(valeur, Decimal):
        return valeur
    try:
        return Decimal(str(valeur))
    except InvalidOperation as exc:
        raise ValueError(f"Montant invalide : {valeur!r}") from exc


@dataclass
class LigneEcriture:
    compte: str
    libelle: str = ""
    debit: Decimal | int | str = Decimal("0")
    credit: Decimal | int | str = Decimal("0")

    def __post_init__(self) -> None:
        self.compte = self.compte.strip()
        self.debit = _to_decimal(self.debit)
        self.credit = _to_decimal(self.credit)


@dataclass
class EcritureComptable:
    lignes: list[LigneEcriture] = field(default_factory=list)
    reference: str | None = None

    @property
    def total_debit(self) -> Decimal:
        return sum((ligne.debit for ligne in self.lignes), Decimal("0"))

    @property
    def total_credit(self) -> Decimal:
        return sum((ligne.credit for ligne in self.lignes), Decimal("0"))


@dataclass
class ResultatValidation:
    erreurs: list[str]

    @property
    def valide(self) -> bool:
        return not self.erreurs


class PlanComptable:
    """Charge le plan de comptes structuré produit par ingestion/extract_pdf.py."""

    def __init__(self, comptes: dict[str, dict]):
        self._comptes = comptes  # numero -> {"intitule", "classe", "niveau", ...}

    @classmethod
    def charger(cls, chemin: Path = DEFAULT_PLAN_COMPTABLE) -> "PlanComptable":
        with Path(chemin).open("r", encoding="utf-8") as f:
            data = json.load(f)
        comptes = {compte["numero"]: compte for compte in data["comptes"]}
        return cls(comptes)

    def existe(self, numero: str) -> bool:
        return numero in self._comptes

    def compte_valide(self, numero: str) -> bool:
        """Un numéro est valide s'il figure au plan, ou s'il en prolonge un
        compte existant (subdivision propre à l'entité, plus fine que le
        plan-type mais rattachée à une rubrique reconnue)."""
        if not numero.isdigit() or len(numero) < 2:
            return False
        if numero in self._comptes:
            return True
        return any(numero.startswith(existant) for existant in self._comptes)

    def intitule(self, numero: str) -> str | None:
        compte = self._comptes.get(numero)
        return compte["intitule"] if compte else None


def verifier_structure(ecriture: EcritureComptable) -> list[str]:
    """Contrôles de forme : nombre de lignes, montants, cohérence débit/crédit par ligne."""
    erreurs: list[str] = []
    if len(ecriture.lignes) < 2:
        erreurs.append("Une écriture doit comporter au moins deux lignes.")

    for i, ligne in enumerate(ecriture.lignes, start=1):
        if not ligne.compte:
            erreurs.append(f"Ligne {i} : numéro de compte manquant.")
        if ligne.debit < 0 or ligne.credit < 0:
            erreurs.append(f"Ligne {i} ({ligne.compte}) : montant négatif interdit.")
        if ligne.debit > 0 and ligne.credit > 0:
            erreurs.append(
                f"Ligne {i} ({ligne.compte}) : une ligne ne peut être "
                "débitrice et créditrice à la fois."
            )
        if ligne.debit == 0 and ligne.credit == 0:
            erreurs.append(f"Ligne {i} ({ligne.compte}) : montant nul, ligne sans effet.")

    return erreurs


def verifier_equilibre(ecriture: EcritureComptable) -> list[str]:
    """Contrôle fondamental de la partie double : total débit == total crédit."""
    total_debit = ecriture.total_debit
    total_credit = ecriture.total_credit
    if total_debit != total_credit:
        ecart = total_debit - total_credit
        return [
            f"Écriture déséquilibrée : débit {total_debit} != crédit {total_credit} "
            f"(écart de {ecart})."
        ]
    return []


def verifier_imputation(ecriture: EcritureComptable, plan: PlanComptable) -> list[str]:
    """Vérifie que chaque compte mouvementé existe dans le plan SYSCOHADA."""
    erreurs: list[str] = []
    for i, ligne in enumerate(ecriture.lignes, start=1):
        if ligne.compte and not plan.compte_valide(ligne.compte):
            erreurs.append(f"Ligne {i} : le compte {ligne.compte} n'existe pas dans le plan SYSCOHADA.")
    return erreurs


def valider_ecriture(
    ecriture: EcritureComptable, plan: PlanComptable | None = None
) -> ResultatValidation:
    """Orchestre l'ensemble des contrôles déterministes sur une écriture.

    `plan` est optionnel : sans lui, seuls la structure et l'équilibre
    débit/crédit sont vérifiés (pas de contrôle d'imputation).
    """
    erreurs = verifier_structure(ecriture)
    erreurs += verifier_equilibre(ecriture)
    if plan is not None:
        erreurs += verifier_imputation(ecriture, plan)
    return ResultatValidation(erreurs=erreurs)
