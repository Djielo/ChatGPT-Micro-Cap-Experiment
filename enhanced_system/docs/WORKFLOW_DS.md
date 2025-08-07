### DS MicroCaps — Spécification du Workflow (v1)

#### Objectifs

- Identifier, prioriser et valider des microcaps US à fort potentiel via un pipeline modulaire et traçable.
- Exploiter DeepSeek pour l’enrichissement web ciblé et produire des datasets intermédiaires utiles à HRM et au Streamlit.

#### Vue d’ensemble du pipeline

```
micro_caps_extended.csv (univers 50–300M MC)
        ↓
extended_to_potential.py
        ↓  extended_to_potential.csv
        ↓
DS_potential_to_pepite.py
        ↓  potential_to_pepite.csv
        ↓
DS_pepite_to_sharpratio.py
        ↓  final_pepites.csv (consommé par Streamlit)
```

#### Emplacements des fichiers (par défaut)

- `enhanced_system/data/micro_caps_extended.csv` + `enhanced_system/data/evolution/caps_evolution_YYYY-MM-DD.json`
- `enhanced_system/data/extended_to_potential.csv` + `enhanced_system/data/evolution/extended_to_potential_YYYY-MM-DD.json`
- `enhanced_system/data/potential_to_pepite.csv` + `enhanced_system/data/evolution/potential_to_pepite_YYYY-MM-DD.json`
- `enhanced_system/data/final_pepites.csv` + `enhanced_system/data/evolution/final_pepites_YYYY-MM-DD.json`

---

### Étape 0 — Univers quotidien (rappel)

- Source: collecte multi-quotidienne des microcaps US 50–300M MC (script existant `fetch_all_microcaps_fmp.py`).
- Sortie courante: `micro_caps_extended.csv`.
- Archive: `caps_evolution_YYYY-MM-DD.json` (cumule les runs de la journée avec horodatage).

---

### Étape 1 — `extended_to_potential.py` (sans IA)

**But**: filtrage déterministe pour constituer le vivier à investiguer.

- Entrée: `micro_caps_extended.csv`
- Sortie: `extended_to_potential.csv`
- Archive: `extended_to_potential_YYYY-MM-DD.json`

Critères de sélection (paramétrables):

- **Market Cap**: 50M ≤ MC ≤ 200M (option 150M en plafond alternatif).
- **Prix**: Price ≥ 5$ (préférence forte pour 5–10$).
- **Volume (soft)**: ≥ 10K (non prépondérant; pondération adaptée à la MC).
- **Exchange prioritaire**: Nasdaq.
- **Secteurs porteurs**: Tech, Healthcare, etc.

Scoring déterministe proposé (0–100, pondérations par défaut):

- MC: 50–150M → +30; 150–200M → +20
- Exchange Nasdaq → +15
- Secteur prioritaire (Tech/Healthcare) → +15
- Prix 5–10$ → +20; sinon ≥5$ → +10
- Volume « adéquat » à la MC → +10 (seuils progressifs par tranche MC)
- Qualité des données (non-OTC, champs clés présents) → +10
- Seuil de passage recommandé: Score ≥ 60

ReasonsTags et commentaires (règles simples, sans IA):

- Tags possibles: `Nasdaq`, `SectorTech`, `SectorHealthcare`, `PriceBand5-10`, `MC_50-150`, `MC_150-200`, `VolAdequate`, `DataComplete`, `NotOTC`.
- `Comments` peut résumer: « Nasdaq + Tech + PriceBand 5–10 + MC 80M ».

Suivi de progression par rapport à `caps_evolution_YYYY-MM-DD.json`:

- Statuts: `New`, `Maintained`, `Dropped`.
- `ChangeNotes` (ex: « Price +12% vs veille; Volume x1.8 »).

Colonnes minimales `extended_to_potential.csv`:

- `Ticker`, `MarketCap`, `Price`, `Volume`, `Exchange`, `Sector`
- `ScorePotential`, `ReasonsTags`, `Comments`
- `Status`, `ChangeNotes`, `Date`

Structure d’archive JSON (exemple minimal):

```json
{
  "metadata": {
    "pipeline_step": "extended_to_potential",
    "source_csv": "micro_caps_extended.csv",
    "run_date": "2025-08-07",
    "run_time": "14:30:03",
    "schedule_slot": "14:30",
    "parameters": {
      "mc_min": 50000000,
      "mc_max": 200000000,
      "price_min": 5,
      "volume_soft": 10000
    },
    "weights": {
      "mc": 30,
      "exchange": 15,
      "sector": 15,
      "price_band": 20,
      "volume": 10,
      "data_quality": 10
    },
    "version": "1.0"
  },
  "counters": { "total_input": 2311, "filtered": 412 },
  "items": [
    {
      "Ticker": "INMB",
      "ScorePotential": 78,
      "ReasonsTags": ["Nasdaq", "SectorTech", "PriceBand5-10", "MC_50-150"],
      "Status": "Maintained"
    }
  ]
}
```

---

### Étape 2 — `DS_potential_to_pepite.py` (DeepSeek requis)

**But**: enquête web pour identifier/valider des pépites.

- Entrée: `extended_to_potential.csv`
- Sortie: `potential_to_pepite.csv`
- Archive: `potential_to_pepite_YYYY-MM-DD.json`

Sources web recommandées (gratuits/freemium):

- PR Newswire (`https://www.prnewswire.com`) — communiqués/partenariats.
- Morningstar (`https://www.morningstar.com`) — fondamentaux.
- SeekingAlpha (`https://seekingalpha.com`) — earnings calls, analyses.
- InvestorPlace / MarketBeat / Benzinga — news marché.
- Yahoo Finance (`https://finance.yahoo.com`) — résumés + liens SEC.
- SEC EDGAR (`https://www.sec.gov/edgar.shtml`) — 8-K, 10-K, 10-Q.
- Site officiel — pages News/Investors/Partners.
- Reddit, Twitter/X — buzz et sentiment (prudence).

Modèles de recherches (exemples):

- `site:prnewswire.com "Nom Société" partnership OR collaboration OR agreement`
- `site:seekingalpha.com "Nom Société" partnership`
- `site:sec.gov 8-K "Nom Société" agreement OR customer`
- `site:<site-entreprise> partnership OR client OR collaboration`

Super-prompt DS — exigences clés:

- Confiance attendue 0.65–0.80 selon MC (échelle glissante). 80% n’est pas un plafond; flexibilité ±5% (min absolu 0.60).
- Restrictions: MC ∈ [50M;300M], Prix ≥ 5$, éviter penny/OTC.
- Sortie JSON stricte: `decision`, `confidence`, `target_price_15j`, `catalyseurs`, `thesis`, `risk_factors`, `conviction_level`, `reasoning_steps`.
- Ajouter `NewsSummary`, `FilingsSummary`, `TechnicalSummary`, `Insights`.

Validation qualité post-DS:

- `confidence_required_base` via échelle glissante; `confidence_required_flexible` = base − 5pp (min 0.60).
- `confidence_valid` si `confidence ≥ flexible`.
- `meets_criteria` = MC in-range AND confidence_valid AND Price ≥ 5$ AND cohérence des signaux.

Colonnes minimales `potential_to_pepite.csv`:

- Base: `Ticker`, `MarketCap`, `Price`, `Volume`, `Exchange`, `Sector`, `ScorePotential`, `ReasonsTags`
- Enrichissements DS: `Partenariats`, `LeveesFonds`, `InstHoldersCount`, `TwitterSentiment`, `TwitterBuzzScore`, `ShortRatio`, `FloatShortPct`, `Employees`, `Revenus`, `Benefices`, `Croissance`, `Keywords`
- Synthèses: `NewsSummary`, `FilingsSummary`, `TechnicalSummary`, `Insights`
- Décision: `DS_Decision`, `DS_Confidence`, `DS_TargetPrice15d`, `DS_Conviction`, `DS_Risks`, `DS_ReasoningSteps`, `MeetsCriteria`
- Garde-fous: `DS_ConfidenceRequired_Base`, `DS_ConfidenceRequired_Flexible`, `DS_ConfidenceMargin`
- Stats: `DS_Tokens`, `DS_Timestamp`

---

### Étape 3 — `DS_pepite_to_sharpratio.py`

**But**: scoring final « Sharpe-like » pour prioriser les entrées et nourrir Streamlit.

- Entrée: `potential_to_pepite.csv`
- Sortie: `final_pepites.csv`
- Archive: `final_pepites_YYYY-MM-DD.json`

Calculs recommandés:

- `ExpectedReturn15d = (TargetPrice15d − Price) / Price`
- `Volatility30d` = écart-type des rendements quotidiens 30j (ou ATR(14) normalisé par le prix si plus robuste).
- `ShortSqueezeFactor` = f(`ShortRatio`, `FloatShortPct`) normalisée [0;1] (plafonner pour outliers).
- `DS_SharpRatio = (ExpectedReturn15d × DS_Confidence × (1 + 0.3 × ShortSqueezeFactor)) / max(Volatility30d, ε)`
- Option: bandes d’objectifs et clôtures partielles via quantiles historiques (comparables sectoriels).

Colonnes ajoutées:

- `ExpectedReturn15d`, `Volatility30d`, `ShortSqueezeFactor`, `DS_SharpRatio`, `Rank`, `FinalLabel`, `Notes`

---

### Scheduling — créneaux et orchestration

Principes:

- À chaque exécution, **CSV et JSON sont produits simultanément** pour l’étape concernée.
- Le CSV est **toujours écrasé** (vue courante). Le JSON est un **journal quotidien** cumulant les runs.
- Zone horaire: `Europe/Paris` (gérer DST).

Créneaux recommandés:

- Étapes 0–1 (univers + filtrage): **5×/jour** — 09:00, 14:30, 18:00, 22:00, 01:30
- Étapes 2–3 (DS + scoring): **3×/jour** — 14:30, 18:00, 22:00

Offsets intra-slot (éviter simultanéité):

- `t+00:00` → Étape 0 (`micro_caps_extended.*`)
- `t+00:02` → Étape 1 (`extended_to_potential.*`)
- `t+00:04` → Étape 2 (`potential_to_pepite.*`)
- `t+00:06` → Étape 3 (`final_pepites.*`)

Remarque: 22:00 peut devenir 23:00 selon DST. Aligner dynamiquement sur la clôture US. Idem pour les autres horiares !

---

### Archivage JSON — conventions

- Nom de fichier: `{etape}_YYYY-MM-DD.json`
- Contenu minimal:
  - `metadata`: `pipeline_step`, `source_csv`, `run_date`, `run_time`, `schedule_slot`, `parameters`, `version`
  - `counters`: métriques de production (par étape)
  - `items` (ou `runs[]`): objets/échantillons de l’exécution
  - Option: `run_id` (UUID) pour chaque entrée intra-journalière

Bonnes pratiques d’E/S:

- Écriture atomique: écrire vers un fichier temporaire puis `rename()`.
- Verrou léger par étape/slot pour éviter les chevauchements.
- Si l’étape N échoue, ne pas lancer N+1 dans le même slot.

Rétention:

- JSON conservés 365 jours (recommandé); compresser >90 jours (`.json.gz`).
- CSV: uniquement la vue courante par étape.
- Index optionnel: `runs_index.csv` (liste `run_id`, étape, date/heure, statut, chemins sorties).

---

### Configuration & sécurité

- `enhanced_system/deepseek_integration/config.py` joue le rôle de **façade** de configuration et lit les **variables d’environnement**.
  - `DEEPSEEK_API_KEY` doit venir de l’environnement; si absent → erreur explicite.
  - Timeouts, retries, slots, offsets, seuils/pondérations: valeurs par défaut + surcharge via env.
- Éviter toute clé en clair commitée.

---

### Confiance & critères DS (rappel)

- Échelle glissante: **65–80%** visée (selon MC, 50M → 0.80 … 300M → 0.65).
- Flexibilité: ±5% autour du minimum requis (min absolu 0.60).
- Validation stricte: MC in-range, confiance valide, prix ≥ 5$, cohérence des signaux.

---

### Datasets HRM — Source de vérité

- HRM doit apprendre à partir des **JSON d’archive** (`enhanced_system/data/evolution/*.json`) qui conservent l’historique intra-journalier, les paramètres et les horodatages, plutôt que des CSV qui sont écrasés à chaque mise à jour.
- Clé logique recommandée pour déduplication et versionnage: `(ticker, pipeline_step, run_datetime, run_id)`.
- Pipeline suggéré:
  - Construire un dataset consolidé via un script (ex: `hrm_ai/build_hrm_dataset.py`) qui lit/normalise les JSON des 3 étapes, aplatit les structures, déduplique et écrit un `parquet` partitionné par `pipeline_step` et `run_date`.
  - Split temporel: `train` (ancien), `val` (récent), `test` (très récent) pour éviter la fuite temporelle.
  - Cibles initiales: `DS_Decision` et/ou régression via `ExpectedReturn15d`; pondération possible par `DS_Confidence` (échelle glissante 65–80% avec flex ±5%).

### Notes d’implémentation

- Étape 1 reste simple, performante et traçable; Étape 2 concentre le coût IA sur un sous-ensemble pertinent; Étape 3 transforme l’info en décision opérationnelle.
- Les **JSON d’archive** constituent la base d’apprentissage HRM; les CSV servent de vue courante pour l’app et le monitoring.
