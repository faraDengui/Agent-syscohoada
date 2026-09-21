from decimal import Decimal

import pytest

from agent.rules_engine import (
    EcritureComptable,
    LigneEcriture,
    PlanComptable,
    valider_ecriture,
    verifier_equilibre,
    verifier_imputation,
    verifier_structure,
)


@pytest.fixture(scope="module")
def plan() -> PlanComptable:
    return PlanComptable.charger()


def test_ecriture_equilibree_et_imputee_est_valide(plan):
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", libelle="Client X", debit="119000"),
            LigneEcriture(compte="701", libelle="Vente de marchandises", credit="100000"),
            LigneEcriture(compte="443", libelle="TVA facturée", credit="19000"),
        ]
    )
    resultat = valider_ecriture(ecriture, plan)
    assert resultat.valide
    assert resultat.erreurs == []


def test_ecriture_desequilibree_est_rejetee():
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="100"),
            LigneEcriture(compte="701", credit="90"),
        ]
    )
    erreurs = verifier_equilibre(ecriture)
    assert len(erreurs) == 1
    assert "déséquilibrée" in erreurs[0]
    assert "10" in erreurs[0]


def test_compte_inexistant_est_rejete(plan):
    # Aucune classe SYSCOHADA ne commence par "0" : ni un compte existant,
    # ni une extension valide d'un compte existant.
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="0500", debit="100"),
            LigneEcriture(compte="701", credit="100"),
        ]
    )
    erreurs = verifier_imputation(ecriture, plan)
    assert len(erreurs) == 1
    assert "0500" in erreurs[0]


def test_compte_plus_detaille_que_le_plan_est_accepte(plan):
    # 4111 n'est pas au plan-type mais prolonge le compte 411 (CLIENTS) existant.
    assert plan.compte_valide("41199")


def test_ligne_avec_debit_et_credit_simultanes_est_rejetee():
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="100", credit="100"),
            LigneEcriture(compte="701", credit="100"),
        ]
    )
    erreurs = verifier_structure(ecriture)
    assert any("débitrice et créditrice" in e for e in erreurs)


def test_ligne_montant_negatif_est_rejetee():
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="-100"),
            LigneEcriture(compte="701", credit="100"),
        ]
    )
    erreurs = verifier_structure(ecriture)
    assert any("négatif" in e for e in erreurs)


def test_ecriture_moins_de_deux_lignes_est_rejetee():
    ecriture = EcritureComptable(lignes=[LigneEcriture(compte="411", debit="100")])
    erreurs = verifier_structure(ecriture)
    assert any("au moins deux lignes" in e for e in erreurs)


def test_montants_decimaux_exacts_sans_erreur_de_flottant(plan):
    # 3 lignes de 0.10 doivent équilibrer exactement 0.30 en Decimal.
    ecriture = EcritureComptable(
        lignes=[
            LigneEcriture(compte="411", debit="0.30"),
            LigneEcriture(compte="701", credit="0.10"),
            LigneEcriture(compte="443", credit="0.10"),
            LigneEcriture(compte="521", credit="0.10"),
        ]
    )
    assert ecriture.total_debit == Decimal("0.30")
    assert verifier_equilibre(ecriture) == []
