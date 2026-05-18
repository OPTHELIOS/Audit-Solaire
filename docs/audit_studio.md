# OPT'HELIOS Audit Studio — V1

Cette V1 incrémentale ajoute deux briques métier au dépôt `Audit-Solaire`, inspirées
du prototype *Audit Solaire Builder V2*, sans casser la structure existante.

## 1. Mode de rapport

Le modèle `Audit` (Pydantic) porte désormais un champ `mode_rapport` à deux valeurs :

- `audit_complet` — rapport long format (constats détaillés + plan d'actions + annexes).
- `diagnostic_court` — note de synthèse resserrée (appréciation globale + scénarios + recommandations prioritaires).

Les anciens audits JSON sans ce champ se chargent automatiquement avec la valeur
par défaut `audit_complet` (compatibilité ascendante).

## 2. Catalogue de scénarios

Module `domain.audit_studio.SCENARIOS_CATALOG` :

| Code | Libellé | Horizon |
| --- | --- | --- |
| `conserver_optimiser` | Conserver et optimiser | Court terme |
| `rehabiliter_court_terme` | Réhabiliter à court terme | 6 à 18 mois |
| `rehabiliter_lourdement` | Réhabiliter lourdement | 12 à 36 mois |
| `redimensionner` | Redimensionner l'installation | 12 à 24 mois |
| `remplacer` | Remplacer l'installation | 12 à 36 mois |
| `abandonner` | Abandonner l'installation | Court terme |
| `portefeuille_multi_batiments` | Stratégie portefeuille multi-bâtiments | 24 à 60 mois |

Chaque scénario propose une description, des conditions de pertinence, des actions
types et des points de vigilance. L'auditeur peut retenir un ou plusieurs scénarios
et adjoindre un commentaire libre.

## 3. Bibliothèque de formulations OPT'HELIOS

Module `domain.audit_studio.FORMULATIONS_CATALOG`. Dix formulations capitalisées
sur les rapports OPT'HELIOS sont disponibles :

- `schema_hydraulique_incoherent`
- `surdimensionnement`
- `metrologie_insuffisante`
- `maintenance_insuffisante`
- `capteurs_integres_fabricant_disparu`
- `autovidangeable_recuperable`
- `sportive_peu_utilisee_ete`
- `diagnostic_multi_batiments`
- `corrosion_liaison_equipotentielle`
- `traceur_electrique`

Chaque formulation porte un constat type, un impact type et une recommandation
type. Lors de son application à un audit, ces textes peuvent être surchargés
ponctuellement (`constat_personnalise`, `impact_personnalise`,
`recommandation_personnalisee`).

## 4. Intégration UI

- **Page 5 — Synthèse** : nouvel onglet *Studio OPT'HELIOS* permettant de choisir
  le mode de rapport, retenir les scénarios pertinents, appliquer des formulations
  et rédiger la note stratégique.
- **Page 6 — Export** : un expander *Studio OPT'HELIOS — synthèse rapide* récapitule
  en lecture seule les choix faits dans la page 5, avant la génération du livrable.

## 5. Intégration export

- `domain.docx_service.build_docx_report` ajoute une section *6. Studio OPT'HELIOS —
  orientations stratégiques* (scénarios retenus, formulations appliquées, note
  stratégique), suivie de la section 7 *Métadonnées*.
- `domain.report_service.build_report_markdown` rend une section *Studio OPT'HELIOS*
  équivalente dans l'export Markdown / JSON.

## 6. Compatibilité JSON

Le nouveau bloc `studio` est ajouté au modèle `Audit` avec une valeur par défaut.
Les audits JSON existants se rechargent sans erreur (`model_config = {"extra":
"ignore"}` + valeurs par défaut sur tous les champs nouveaux).

## 7. Tests

```bash
python3 -m unittest tests.test_audit_studio -v
```

14 tests couvrent :

- intégrité des catalogues (scénarios et formulations) ;
- recherche dans la bibliothèque de formulations ;
- API `AuditStudioBlock` (`upsert_scenario`, `selected_scenarios`,
  `add_formulation`, `remove_formulation`) ;
- intégration au modèle `Audit` (valeurs par défaut, sérialisation, compatibilité
  avec un JSON ancien sans champ `studio`).
