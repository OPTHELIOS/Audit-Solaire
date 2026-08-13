"""Modèles de relevés de mesure usuels pour un audit solaire thermique
(température, pression, débit...). Sert juste à préremplir rapidement le
formulaire d'ajout dans `ui/pages/_08_mesures.py` ; l'auditeur peut toujours
saisir un relevé entièrement personnalisé.
"""

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
]

RELEVES_BY_CODE: dict[str, dict[str, str]] = {r["code"]: r for r in RELEVES_CATALOG}
