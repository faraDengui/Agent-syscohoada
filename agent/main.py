"""Point d'entrée : orchestration RAG + appel à l'API Claude.

Assemble le contexte récupéré (plan de comptes structuré ; à terme les
normes narratives via index/build_index.py, non disponible pour l'instant,
voir CLAUDE.md § "À faire") avec la question de l'utilisateur, puis
interroge Claude pour l'interprétation.

Aucun calcul financier n'est jamais délégué au modèle : une écriture
comptable est toujours validée par agent/rules_engine.py (code vérifiable)
avant d'être présentée ; le LLM se limite à expliquer un résultat déjà
tranché, jamais à le recalculer (cf. CLAUDE.md, "Calculs déterministes").
"""

from __future__ import annotations

import argparse
import os

from agent.retriever import extraire_numeros_comptes, rechercher_compte, rechercher_mot_cle
from agent.rules_engine import EcritureComptable, PlanComptable, ResultatValidation, valider_ecriture

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MODELE_PAR_DEFAUT = os.environ.get("SYSCOHOADA_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = (
    "Tu es un expert-comptable spécialisé dans le système comptable "
    "SYSCOHADA (OHADA). Réponds uniquement à partir du contexte fourni "
    "(extraits du plan de comptes, résultats de validation). Si le "
    "contexte est insuffisant pour répondre avec certitude, dis-le "
    "explicitement plutôt que d'inventer un numéro de compte. Ne "
    "recalcule jamais toi-même un solde ou un équilibre débit/crédit : "
    "appuie-toi exclusivement sur le résultat de validation fourni, qui a "
    "déjà été calculé par du code vérifiable."
)


def assembler_contexte_comptes(question: str, plan: PlanComptable, limite: int = 8) -> list[dict]:
    """Récupère les entrées du plan de comptes pertinentes pour la question.

    Recherche exacte sur les numéros de compte cités dans la question,
    complétée par une recherche mot-clé sur les intitulés.
    """
    resultats: dict[str, dict] = {}

    for numero in extraire_numeros_comptes(question):
        compte = rechercher_compte(numero, plan)
        if compte:
            resultats[compte["numero"]] = compte

    for compte in rechercher_mot_cle(question, plan, limite=limite):
        resultats.setdefault(compte["numero"], compte)

    return list(resultats.values())[:limite]


def formater_contexte(comptes: list[dict]) -> str:
    if not comptes:
        return "Aucun compte du plan SYSCOHADA ne correspond à la question."
    lignes = [f"- {compte['numero']} : {compte['intitule']}" for compte in comptes]
    return "Extraits du plan de comptes SYSCOHADA pertinents :\n" + "\n".join(lignes)


def _formater_resultat_validation(ecriture: EcritureComptable, resultat: ResultatValidation) -> str:
    lignes = "\n".join(
        f"- {ligne.compte} : débit {ligne.debit} / crédit {ligne.credit}"
        for ligne in ecriture.lignes
    )
    if resultat.valide:
        verdict = "L'écriture est VALIDE (équilibrée et correctement imputée)."
    else:
        detail = "\n".join(f"  - {erreur}" for erreur in resultat.erreurs)
        verdict = f"L'écriture est INVALIDE pour les raisons suivantes :\n{detail}"

    return (
        "Résultat de validation déjà calculé par le moteur de règles "
        "(à ne pas recalculer, uniquement expliquer et commenter) :\n\n"
        f"Lignes de l'écriture :\n{lignes}\n\n{verdict}\n\n"
        "Explique ce résultat en langage clair pour un utilisateur non expert."
    )


def _client_anthropic():
    import anthropic

    return anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement


def appeler_claude(system: str, prompt: str, modele: str = MODELE_PAR_DEFAUT, client=None) -> str:
    client = client or _client_anthropic()
    message = client.messages.create(
        model=modele,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(bloc.text for bloc in message.content if bloc.type == "text")


def repondre_question(question: str, plan: PlanComptable, client=None) -> str:
    """Orchestration RAG : récupère le contexte pertinent puis interroge Claude."""
    contexte = assembler_contexte_comptes(question, plan)
    prompt = f"{formater_contexte(contexte)}\n\nQuestion : {question}"
    return appeler_claude(SYSTEM_PROMPT, prompt, client=client)


def valider_et_expliquer(ecriture: EcritureComptable, plan: PlanComptable, client=None) -> str:
    """Valide une écriture de façon déterministe, puis fait expliquer le résultat par Claude."""
    resultat = valider_ecriture(ecriture, plan)
    prompt = _formater_resultat_validation(ecriture, resultat)
    return appeler_claude(SYSTEM_PROMPT, prompt, client=client)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent expert SYSCOHOADA")
    parser.add_argument("question", help="Question à poser à l'agent")
    args = parser.parse_args()

    plan = PlanComptable.charger()
    print(repondre_question(args.question, plan))


if __name__ == "__main__":
    main()
