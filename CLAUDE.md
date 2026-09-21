# CLAUDE.md — Agent Expert SYSCOHOADA

Ce fichier documente le contexte, l'architecture et les règles du projet pour guider Claude Code lors du développement. À conserver à la racine du projet et à mettre à jour au fil de l'avancement.

## Objectif du projet

Développer un agent IA expert en comptabilité SYSCOHOADA (système comptable OHADA), hébergé en local dans un premier temps, capable de :
- Répondre à des questions sur les normes et le plan de comptes OHADA
- Assister la saisie et la validation d'écritures comptables
- Générer des états financiers conformes (bilan, compte de résultat, tableau des flux de trésorerie)

## Architecture du projet

```
syscohoada-agent/
├── data/
│   ├── raw/                    # PDF original du SYSCOHOADA
│   ├── extracted/              # Texte brut extrait du PDF
│   └── structured/             # Plan de comptes en JSON/CSV, normes découpées
│
├── ingestion/
│   ├── extract_pdf.py          # Extraction texte + tables du PDF
│   ├── chunk_text.py           # Découpage en chunks logiques (par norme, par classe)
│   └── build_index.py          # Génération embeddings + indexation (Chroma/FAISS)
│
├── index/
│   └── chroma_db/               # Base vectorielle locale (générée, non versionnée)
│
├── agent/
│   ├── retriever.py             # Fonction de recherche dans l'index
│   ├── rules_engine.py          # Règles déterministes (équilibre débit/crédit, imputation)
│   └── main.py                  # Point d'entrée : orchestration RAG + appel Claude
│
├── tests/
│   └── test_retrieval.py        # Vérifier que les requêtes types retournent les bons chunks
│
├── .env                          # Clé API (jamais versionnée)
├── requirements.txt
└── README.md
```

## Flux de traitement (RAG)

1. `extract_pdf.py` → extrait le texte brut du PDF SYSCOHOADA, isole les tableaux (plan de comptes) séparément du texte narratif
2. `chunk_text.py` → découpe le contenu en unités cohérentes (une norme = un chunk, une classe de comptes = un chunk)
3. `build_index.py` → génère les embeddings et peuple la base vectorielle locale
4. `retriever.py` → au moment de la question utilisateur, récupère les chunks pertinents par recherche sémantique
5. `main.py` → assemble le contexte récupéré + la question utilisateur, appelle l'API Claude, applique les règles de validation si nécessaire

## Principes directeurs

- **Séparation données structurées / narratives** : le plan de comptes (numéros + intitulés) est stocké en format tabulaire (JSON/CSV) dans `data/structured/`, car il se prête à une recherche exacte par numéro de compte. Les normes et textes explicatifs restent en texte pour la recherche sémantique.
- **Calculs déterministes, pas de calculs par le LLM** : tous les calculs financiers (équilibre débit/crédit, totaux, imputations) doivent être effectués par du code vérifiable dans `rules_engine.py`, jamais délégués aux réponses du modèle. Le LLM sert à l'interprétation, l'explication des règles, et l'assistance à la saisie — pas à être la source de vérité des montants.
- **RAG léger, pas d'infrastructure lourde** : le corpus SYSCOHOADA est de taille raisonnable (quelques centaines de pages). Une base vectorielle locale (Chroma ou FAISS) et des embeddings via API suffisent ; pas besoin de GPU ni de serveur dédié pour cette phase locale.
- **Qualité de l'extraction PDF** : vérifier si le PDF source est natif (texte) ou scanné (image) avant de choisir la bibliothèque d'extraction — un PDF scanné nécessite une étape d'OCR.
- **Hébergement local d'abord** : l'objectif actuel est de faire fonctionner l'agent en local avant d'envisager un déploiement à plus grande échelle.

## Stack technique envisagée

- Extraction PDF : `pypdf` ou `pdfplumber` (à confirmer selon le type de PDF)
- Base vectorielle : Chroma ou FAISS (locale)
- Embeddings : API d'embedding externe (pas d'hébergement de modèle local)
- Orchestration / appel LLM : API Claude

## À faire / décisions en attente

- [ ] Confirmer si le PDF SYSCOHOADA source est un PDF texte natif ou scanné
- [ ] Définir la structure exacte du JSON/CSV du plan de comptes
- [ ] Détailler les règles de `rules_engine.py` (validations spécifiques OHADA)
- [ ] Choisir entre Chroma et FAISS selon les tests de performance
