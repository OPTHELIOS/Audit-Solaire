"""Catalogue des documents administratifs/techniques generalement attendus
pour un dossier d'audit solaire thermique complet (DOE, schemas, garanties,
contrats...).

Volontairement une simple liste de dicts (meme esprit que
`domain/checklists.py`) : facile a etendre sans toucher au modele Pydantic.
"""

DOCUMENTS_CATALOG: list[dict[str, str]] = [
    {
        "code": "DOE",
        "libelle": "Dossier des Ouvrages Exécutés (DOE)",
        "description": "Plans et documents tels que construits, remis en fin de chantier.",
    },
    {
        "code": "SCHEMA_HYDRAULIQUE",
        "libelle": "Schéma hydraulique",
        "description": "Schéma de principe de l'installation solaire (circuits primaire/secondaire, appoint).",
    },
    {
        "code": "SCHEMA_ELECTRIQUE",
        "libelle": "Schéma électrique",
        "description": "Schéma de câblage et de raccordement électrique de l'installation.",
    },
    {
        "code": "ANALYSE_FONCTIONNELLE",
        "libelle": "Analyse fonctionnelle",
        "description": "Description du fonctionnement attendu de la régulation et des équipements.",
    },
    {
        "code": "NOTICE_EXPLOITATION",
        "libelle": "Notice d'exploitation / maintenance",
        "description": "Consignes d'exploitation courante et de maintenance préventive.",
    },
    {
        "code": "GARANTIES",
        "libelle": "Attestations de garantie fabricant",
        "description": "Garanties capteurs, ballons, régulation et autres équipements clés.",
    },
    {
        "code": "CONTRAT_MAINTENANCE",
        "libelle": "Contrat de maintenance",
        "description": "Contrat en cours avec un prestataire de maintenance solaire.",
    },
    {
        "code": "PV_RECEPTION",
        "libelle": "PV de réception des travaux",
        "description": "Procès-verbal de réception signé à la mise en service.",
    },
    {
        "code": "FICHES_PRODUITS",
        "libelle": "Fiches techniques / produits installés",
        "description": "Fiches techniques des capteurs, ballons, régulateur, échangeur...",
    },
    {
        "code": "CARNET_ENTRETIEN",
        "libelle": "Carnet d'entretien / suivi",
        "description": "Historique des interventions et relevés d'entretien.",
    },
]

DOCUMENTS_BY_CODE: dict[str, dict[str, str]] = {d["code"]: d for d in DOCUMENTS_CATALOG}
