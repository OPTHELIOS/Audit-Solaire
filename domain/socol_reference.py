"""Rattachement de l'installation auditée à la nomenclature des schémas de
référence SOCOL (charte qualité solaire thermique collectif, portée par
Enerplan/ADEME/INES/Tecsol — livret technique "Les Systèmes Solaires
Combinés pour les bâtiments collectifs", éd. 2023, www.solaire-collectif.fr)
et bibliothèque de schémas de principe génériques associés.

PROPRIÉTÉ INTELLECTUELLE — point important : les schémas hydrauliques publiés
par SOCOL (livret technique, fiches PDF) sont la propriété de leurs auteurs
et ne sont PAS reproduits ici. Les images de `assets/schemas_socol/` sont
redessinées intégralement par nos soins (voir
`scripts/generate_schemas_socol.py`), avec des symboles hydrauliques
génériques et la palette de couleurs OPT'HELIOS — seuls le PRINCIPE de
fonctionnement (schéma de principe, non protégeable en tant que tel) et la
NOMENCLATURE SOCOL (simple identifiant "REF1-SSC1" etc., qui sert de
référentiel professionnel reconnu par la filière) sont repris.

Seules les trois combinaisons directement déductibles des données saisies
dans l'appli (type d'échangeur × type de stockage) sont couvertes : la base
"REFx" complète du référentiel SOCOL (REF1 à REF5) dépend aussi du type de
distribution de chauffage et de la présence d'un bouclage sanitaire, des
informations que l'appli ne collecte pas aujourd'hui — la suggestion
automatique ci-dessous est donc un point de départ à confirmer par
l'auditeur, jamais une certification.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SocolSchemaRef:
    code: str
    libelle: str
    principe: str
    points_vigilance: tuple[str, ...]
    image_filename: str


SOCOL_SCHEMA_LIBRARY: dict[str, SocolSchemaRef] = {
    "REF1-SSC1": SocolSchemaRef(
        code="REF1-SSC1",
        libelle="REF1-SSC1 — Préchauffage solaire à échangeur externe, appoint en série",
        principe=(
            "Montage le plus répandu en solaire thermique collectif ECS : le "
            "circuit primaire solaire cède sa chaleur à l'eau sanitaire via un "
            "échangeur à plaques externe au ballon de stockage solaire, qui "
            "préchauffe l'eau avant son passage dans l'appoint (chaudière ou "
            "réseau de chaleur), monté en série en aval."
        ),
        points_vigilance=(
            "Le préchauffage solaire doit rester en amont de l'appoint : toute "
            "élévation de consigne de l'appoint pénalise directement le taux de "
            "couverture solaire.",
            "L'échangeur externe nécessite un circulateur secondaire dédié et un "
            "réglage de pincement (écart de température primaire/secondaire) "
            "cohérent — un écart trop grand traduit un échangeur sous-dimensionné "
            "ou entartré.",
        ),
        image_filename="ref1_ssc1_echangeur_externe.png",
    ),
    "REF1-SSC2": SocolSchemaRef(
        code="REF1-SSC2",
        libelle="REF1-SSC2 — Préchauffage solaire à échangeur immergé, appoint en série",
        principe=(
            "Variante du montage précédent où l'échange se fait par un serpentin "
            "immergé directement dans le ballon de stockage solaire, sans "
            "circulateur secondaire ni échangeur à plaques séparé — solution plus "
            "compacte, répandue sur les installations de taille modeste."
        ),
        points_vigilance=(
            "La surface d'échange du serpentin immergé est fixe : contrairement à "
            "l'échangeur externe, elle ne peut pas être ajustée après coup si le "
            "besoin évolue.",
            "L'entartrage du serpentin (eau dure) dégrade progressivement "
            "l'échange sans signe visible de l'extérieur — un écart de "
            "température primaire/ballon anormalement élevé doit alerter.",
        ),
        image_filename="ref1_ssc2_echangeur_immerge.png",
    ),
    "REF3-SSC1": SocolSchemaRef(
        code="REF3-SSC1",
        libelle="REF3-SSC1 — Production ECS instantanée sur stockage en eau technique",
        principe=(
            "Le solaire préchauffe un ballon d'eau technique (boucle fermée, non "
            "sanitaire), qui alimente à son tour un échangeur à plaques à "
            "production instantanée d'ECS — montage utilisé notamment en "
            "établissements de santé pour limiter le volume d'eau chaude "
            "sanitaire stagnante (risque légionelle)."
        ),
        points_vigilance=(
            "La production étant instantanée, la puissance de l'échangeur ECS "
            "final doit être dimensionnée sur la pointe de soutirage, pas sur la "
            "moyenne journalière.",
            "Le volume de stockage en eau technique peut être réduit par rapport "
            "à un stockage sanitaire classique (ratio SOCOL : 50 l/m² minimum "
            "contre 75-100 l/m² en stockage sanitaire), à vérifier spécifiquement.",
        ),
        image_filename="ref3_ssc1_eau_technique.png",
    ),
}


def suggest_schema_reference(
    systeme_capteurs: str | None,
    type_echangeur: str | None,
    type_stockage: str | None,
) -> str | None:
    """Best-effort : suggère un code de la bibliothèque ci-dessus à partir des
    3 champs de classification déjà saisis sur la page "Installation". Ne
    retourne jamais une valeur "certaine" — c'est une aide au remplissage,
    toujours modifiable manuellement par l'auditeur (voir le docstring du
    module pour la limite : la base REFx complète n'est pas déductible)."""
    if type_stockage == "eau_technique":
        return "REF3-SSC1"
    if type_echangeur == "echangeur_immerge":
        return "REF1-SSC2"
    if type_echangeur == "echangeur_externe":
        return "REF1-SSC1"
    return None


def get_schema_ref(code: str | None) -> SocolSchemaRef | None:
    if not code:
        return None
    return SOCOL_SCHEMA_LIBRARY.get(code)
