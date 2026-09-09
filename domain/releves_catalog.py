"""Modèles de relevés de mesure usuels pour un audit solaire thermique
(température, pression, débit...). Sert juste à préremplir rapidement le
formulaire d'ajout dans `ui/pages/_08_mesures.py` ; l'auditeur peut toujours
saisir un relevé entièrement personnalisé.

Les trois libellés ci-dessous (LIBELLE_*) sont ceux utilisés par
`domain/performance_service.py` pour calculer les indicateurs FSAV/Prod/Taux
(nomenclature SOCOL) : contrairement aux autres relevés (température,
pression, débit instantané), il s'agit de totaux ÉNERGÉTIQUES SUR UNE
PÉRIODE de suivi (ex. une saison de chauffe, une année), pas d'une valeur
ponctuelle — à récupérer depuis la supervision/télégestion si disponible.
"""

LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE = "Production solaire utile sur la période (QSTU)"
LIBELLE_ENERGIE_APPOINT_PERIODE = "Énergie d'appoint sur la période (QApp)"
LIBELLE_CONSO_ELEC_AUX_PERIODE = "Consommation électrique auxiliaires sur la période"

RELEVES_CATALOG: list[dict[str, str]] = [
    {
        "code": "temp_depart_capteurs",
        "libelle": "Température départ capteurs",
        "type_mesure": "temperature",
        "unite": "°C",
    },
    {
        "code": "temp_retour_capteurs",
        "libelle": "Température retour capteurs",
        "type_mesure": "temperature",
        "unite": "°C",
    },
    {
        "code": "temp_ballon_haut",
        "libelle": "Température ballon (haut)",
        "type_mesure": "temperature",
        "unite": "°C",
    },
    {
        "code": "temp_ballon_bas",
        "libelle": "Température ballon (bas)",
        "type_mesure": "temperature",
        "unite": "°C",
    },
    {
        "code": "temp_ecs_distribuee",
        "libelle": "Température ECS distribuée",
        "type_mesure": "temperature",
        "unite": "°C",
    },
    {
        "code": "pression_primaire",
        "libelle": "Pression circuit primaire",
        "type_mesure": "pression",
        "unite": "bar",
    },
    {
        "code": "debit_primaire",
        "libelle": "Débit primaire",
        "type_mesure": "debit",
        "unite": "L/min",
    },
    {
        "code": "concentration_antigel",
        "libelle": "Concentration antigel",
        "type_mesure": "concentration_antigel",
        "unite": "%",
    },
    {
        "code": "energie_solaire_compteur",
        "libelle": "Énergie solaire (compteur ESU, cumul)",
        "type_mesure": "energie",
        "unite": "kWh",
    },
    {
        "code": "energie_solaire_utile_periode",
        "libelle": LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
        "type_mesure": "energie",
        "unite": "kWh",
    },
    {
        "code": "energie_appoint_periode",
        "libelle": LIBELLE_ENERGIE_APPOINT_PERIODE,
        "type_mesure": "energie",
        "unite": "kWh",
    },
    {
        "code": "conso_electrique_aux_periode",
        "libelle": LIBELLE_CONSO_ELEC_AUX_PERIODE,
        "type_mesure": "energie",
        "unite": "kWh",
    },
]

RELEVES_BY_CODE: dict[str, dict[str, str]] = {r["code"]: r for r in RELEVES_CATALOG}
