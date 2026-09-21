import pytest

from agent.main import (
    appeler_claude,
    assembler_contexte_comptes,
    formater_contexte,
    repondre_question,
    valider_et_expliquer,
)
from agent.rules_engine import EcritureComptable, LigneEcriture, PlanComptable


class FauxBlocTexte:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class FauxMessage:
    def __init__(self, text: str):
        self.content = [FauxBlocTexte(text)]


class FauxClientAnthropic:
    """Simule le client `anthropic.Anthropic` sans appel réseau."""

    def __init__(self, reponse: str = "réponse simulée"):
        self.reponse = reponse
        self.derniers_kwargs: dict | None = None
        self.messages = self

    def create(self, **kwargs):
        self.derniers_kwargs = kwargs
        return FauxMessage(self.reponse)


@pytest.fixture(scope="module")
def plan() -> PlanComptable:
    return PlanComptable.charger()


def test_assembler_contexte_par_numero(plan):
    contexte = assembler_contexte_comptes("Que signifie le compte 411 ?", plan)
    numeros = [c["numero"] for c in contexte]
    assert "411" in numeros


def test_assembler_contexte_par_mot_cle(plan):
    contexte = assembler_contexte_comptes("Quel compte pour les ventes de marchandises ?", plan)
    numeros = [c["numero"] for c in contexte]
    assert "701" in numeros


def test_formater_contexte_vide():
    assert "Aucun compte" in formater_contexte([])


def test_appeler_claude_transmet_le_prompt_et_extrait_le_texte():
    client = FauxClientAnthropic(reponse="voici la réponse")
    resultat = appeler_claude("system", "prompt utilisateur", client=client)
    assert resultat == "voici la réponse"
    assert client.derniers_kwargs["system"] == "system"
    assert client.derniers_kwargs["messages"] == [{"role": "user", "content": "prompt utilisateur"}]


def test_repondre_question_inclut_le_contexte_recupere_dans_le_prompt(plan):
    client = FauxClientAnthropic()
    repondre_question("Que signifie le compte 411 ?", plan, client=client)
    prompt_envoye = client.derniers_kwargs["messages"][0]["content"]
    assert "411" in prompt_envoye
    assert "CLIENTS" in prompt_envoye


def test_valider_et_expliquer_ne_delegue_jamais_le_calcul_au_llm(plan):
    """L'écriture est déséquilibrée : le LLM ne doit voir qu'un verdict déjà
    tranché par rules_engine, jamais les montants bruts à recalculer seul."""
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="100"),
            LigneEcriture(compte="701", credit="90"),
        ]
    )
    client = FauxClientAnthropic()
    valider_et_expliquer(ecriture, plan, client=client)
    prompt_envoye = client.derniers_kwargs["messages"][0]["content"]
    assert "INVALIDE" in prompt_envoye
    assert "déséquilibrée" in prompt_envoye
    assert "ne pas recalculer" in prompt_envoye


def test_valider_et_expliquer_ecriture_valide(plan):
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="100"),
            LigneEcriture(compte="701", credit="100"),
        ]
    )
    client = FauxClientAnthropic()
    valider_et_expliquer(ecriture, plan, client=client)
    prompt_envoye = client.derniers_kwargs["messages"][0]["content"]
    assert "VALIDE" in prompt_envoye
    assert "INVALIDE" not in prompt_envoye
