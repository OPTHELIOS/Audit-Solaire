from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class ControlCatalogError(ValueError):
    """Erreur métier liée à la construction ou validation du catalogue."""


class Criticite(str, Enum):
    critique = "critique"
    majeure = "majeure"
    mineure = "mineure"
    information = "information"


class VerdictControle(str, Enum):
    conforme = "conforme"
    non_conforme = "non_conforme"
    non_verifiable = "non_verifiable"
    non_present = "non_present"
    sans_objet = "sans_objet"


class SystemeCapteurs(str, Enum):
    autovidangeable = "autovidangeable"
    sous_pression = "sous_pression"
    thermosiphon = "thermosiphon"


class TypeEchangeur(str, Enum):
    echangeur_externe = "echangeur_externe"
    echangeur_immerge = "echangeur_immerge"


class TypeStockageSolaire(str, Enum):
    eau_sanitaire = "eau_sanitaire"
    eau_technique = "eau_technique"


class TypeComptage(str, Enum):
    autre_comptage = "autre_comptage"
    comptage_appoint = "comptage_appoint"
    comptage_bouclage_solaire = "comptage_bouclage_solaire"
    solaire_primaire = "solaire_primaire"
    solaire_utile_direct = "solaire_utile_direct"
    solaire_utile_indirect = "solaire_utile_indirect"


ALLOWED_CONDITION_KEYS: frozenset[str] = frozenset(
    {
        "systeme_capteurs_in",
        "systeme_capteurs_not_in",
        "type_echangeur_in",
        "type_echangeur_not_in",
        "type_stockage_solaire_in",
        "type_stockage_solaire_not_in",
        "type_comptage_any_in",
        "type_comptage_all_in",
        "type_comptage_not_in",
        "requires_monitoring",
        "requires_telecontrole",
    }
)

ENUM_VALUE_MAP: dict[str, set[str]] = {
    "systeme_capteurs_in": {e.value for e in SystemeCapteurs},
    "systeme_capteurs_not_in": {e.value for e in SystemeCapteurs},
    "type_echangeur_in": {e.value for e in TypeEchangeur},
    "type_echangeur_not_in": {e.value for e in TypeEchangeur},
    "type_stockage_solaire_in": {e.value for e in TypeStockageSolaire},
    "type_stockage_solaire_not_in": {e.value for e in TypeStockageSolaire},
    "type_comptage_any_in": {e.value for e in TypeComptage},
    "type_comptage_all_in": {e.value for e in TypeComptage},
    "type_comptage_not_in": {e.value for e in TypeComptage},
}


def _clean_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ControlCatalogError(f"Le champ '{field_name}' doit être une chaîne.")
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ControlCatalogError(f"Le champ '{field_name}' ne peut pas être vide.")
    return cleaned


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ControlCatalogError(f"Le champ '{field_name}' doit être une liste de chaînes.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ControlCatalogError(f"Le champ '{field_name}' contient une valeur non textuelle.")
        normalized.append(item.strip())
    if not normalized:
        raise ControlCatalogError(f"Le champ '{field_name}' ne peut pas être vide.")
    return normalized


def _as_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ControlCatalogError(f"Le champ '{field_name}' doit être booléen.")
    return value


@dataclass(frozen=True, slots=True)
class ControleCatalogueItem:
    controle_id: str
    section: str
    libelle: str
    methode_verification: str
    criticite_par_defaut: Criticite
    impact_defaut: str
    recommandation_type: str
    preuve_attendue: str
    sous_section: str | None = None
    lot: str | None = None
    description_controle: str | None = None
    condition_applicabilite: Mapping[str, Any] | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    ordre: int = 0
    actif: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "controle_id", _clean_text(self.controle_id, "controle_id"))
        object.__setattr__(self, "section", _clean_text(self.section, "section"))
        object.__setattr__(self, "libelle", _clean_text(self.libelle, "libelle"))
        object.__setattr__(self, "methode_verification", _clean_text(self.methode_verification, "methode_verification"))
        object.__setattr__(self, "impact_defaut", _clean_text(self.impact_defaut, "impact_defaut"))
        object.__setattr__(self, "recommandation_type", _clean_text(self.recommandation_type, "recommandation_type"))
        object.__setattr__(self, "preuve_attendue", _clean_text(self.preuve_attendue, "preuve_attendue"))

        if self.sous_section is not None:
            object.__setattr__(self, "sous_section", _clean_text(self.sous_section, "sous_section"))
        if self.lot is not None:
            object.__setattr__(self, "lot", _clean_text(self.lot, "lot"))
        if self.description_controle is not None:
            object.__setattr__(self, "description_controle", _clean_text(self.description_controle, "description_controle"))

        if not isinstance(self.criticite_par_defaut, Criticite):
            raise ControlCatalogError(
                f"Le champ 'criticite_par_defaut' doit être un membre de Criticite pour {self.controle_id}."
            )

        if not isinstance(self.ordre, int) or self.ordre < 0:
            raise ControlCatalogError(f"Le champ 'ordre' doit être un entier >= 0 pour {self.controle_id}.")

        object.__setattr__(self, "actif", _as_bool(self.actif, "actif"))

        normalized_tags = tuple(sorted({_clean_text(t, "tags") for t in self.tags})) if self.tags else tuple()
        normalized_sources = tuple(sorted({_clean_text(s, "source_refs") for s in self.source_refs})) if self.source_refs else tuple()
        object.__setattr__(self, "tags", normalized_tags)
        object.__setattr__(self, "source_refs", normalized_sources)

        if self.condition_applicabilite is not None:
            validated = validate_condition_applicabilite(self.condition_applicabilite, self.controle_id)
            object.__setattr__(self, "condition_applicabilite", validated)

    def is_applicable(self, contexte: Mapping[str, Any] | None = None) -> bool:
        return is_condition_applicable(self.condition_applicabilite, contexte)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controle_id": self.controle_id,
            "section": self.section,
            "sous_section": self.sous_section,
            "lot": self.lot,
            "libelle": self.libelle,
            "description_controle": self.description_controle,
            "methode_verification": self.methode_verification,
            "criticite_par_defaut": self.criticite_par_defaut.value,
            "impact_defaut": self.impact_defaut,
            "recommandation_type": self.recommandation_type,
            "preuve_attendue": self.preuve_attendue,
            "condition_applicabilite": dict(self.condition_applicabilite) if self.condition_applicabilite else None,
            "tags": list(self.tags),
            "source_refs": list(self.source_refs),
            "ordre": self.ordre,
            "actif": self.actif,
        }


def validate_condition_applicabilite(
    condition: Mapping[str, Any],
    controle_id: str = "<inconnu>",
) -> dict[str, Any]:
    if not isinstance(condition, Mapping):
        raise ControlCatalogError(f"condition_applicabilite doit être un mapping pour {controle_id}.")

    validated: dict[str, Any] = {}
    for key, value in condition.items():
        if key not in ALLOWED_CONDITION_KEYS:
            raise ControlCatalogError(
                f"Clé de condition_applicabilite non autorisée '{key}' pour {controle_id}."
            )

        if key in ENUM_VALUE_MAP:
            values = _normalize_string_list(value, f"{controle_id}.{key}")
            invalid = sorted(set(values) - ENUM_VALUE_MAP[key])
            if invalid:
                raise ControlCatalogError(
                    f"Valeurs invalides pour {controle_id}.{key}: {invalid}. "
                    f"Valeurs autorisées: {sorted(ENUM_VALUE_MAP[key])}"
                )
            validated[key] = list(dict.fromkeys(values))
        else:
            validated[key] = _as_bool(value, f"{controle_id}.{key}")

    return validated


def _normalize_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(v) for v in value if v is not None}
    return {str(value)}


def is_condition_applicable(
    condition: Mapping[str, Any] | None,
    contexte: Mapping[str, Any] | None = None,
) -> bool:
    if not condition:
        return True

    ctx = dict(contexte or {})
    systeme_capteurs = ctx.get("systeme_capteurs")
    type_echangeur = ctx.get("type_echangeur")
    type_stockage = ctx.get("type_stockage_solaire")
    type_comptage = _normalize_set(ctx.get("type_comptage"))
    requires_monitoring = bool(ctx.get("requires_monitoring", False))
    requires_telecontrole = bool(ctx.get("requires_telecontrole", False))

    for key, expected in condition.items():
        if key == "systeme_capteurs_in" and systeme_capteurs not in expected:
            return False
        if key == "systeme_capteurs_not_in" and systeme_capteurs in expected:
            return False
        if key == "type_echangeur_in" and type_echangeur not in expected:
            return False
        if key == "type_echangeur_not_in" and type_echangeur in expected:
            return False
        if key == "type_stockage_solaire_in" and type_stockage not in expected:
            return False
        if key == "type_stockage_solaire_not_in" and type_stockage in expected:
            return False
        if key == "type_comptage_any_in" and not (type_comptage & set(expected)):
            return False
        if key == "type_comptage_all_in" and not set(expected).issubset(type_comptage):
            return False
        if key == "type_comptage_not_in" and (type_comptage & set(expected)):
            return False
        if key == "requires_monitoring" and requires_monitoring is not expected:
            return False
        if key == "requires_telecontrole" and requires_telecontrole is not expected:
            return False

    return True


def _item(
    *,
    controle_id: str,
    section: str,
    libelle: str,
    methode_verification: str,
    criticite: Criticite,
    impact: str,
    recommandation: str,
    preuve: str,
    sous_section: str | None = None,
    lot: str | None = None,
    description: str | None = None,
    condition: Mapping[str, Any] | None = None,
    tags: Iterable[str] = (),
    sources: Iterable[str] = (),
    ordre: int = 0,
    actif: bool = True,
) -> ControleCatalogueItem:
    return ControleCatalogueItem(
        controle_id=controle_id,
        section=section,
        sous_section=sous_section,
        lot=lot,
        libelle=libelle,
        description_controle=description,
        methode_verification=methode_verification,
        criticite_par_defaut=criticite,
        impact_defaut=impact,
        recommandation_type=recommandation,
        preuve_attendue=preuve,
        condition_applicabilite=dict(condition) if condition else None,
        tags=tuple(tags),
        source_refs=tuple(sources),
        ordre=ordre,
        actif=actif,
    )


CONTROL_CATALOG: list[ControleCatalogueItem] = [
    _item(
        controle_id="DOC_001",
        section="Documentation et DOE",
        libelle="Présence du schéma hydraulique d’exécution à jour",
        methode_verification="Vérification documentaire en chaufferie, DOE ou dossier exploitant.",
        criticite=Criticite.majeure,
        impact="Exploitation, maintenance et diagnostic dégradés.",
        recommandation="Fournir ou mettre à jour le schéma hydraulique d’exécution.",
        preuve="Photo du schéma affiché ou extrait DOE.",
        tags=("doe", "schema", "exploitation"),
        sources=("xlsx_mes", "classification_doc"),
        ordre=10,
    ),
    _item(
        controle_id="DOC_002",
        section="Documentation et DOE",
        libelle="Présence du schéma électrique à jour",
        methode_verification="Contrôle documentaire et cohérence avec l’installation observée.",
        criticite=Criticite.majeure,
        impact="Maintenance, dépannage et sécurisation des interventions difficiles.",
        recommandation="Fournir ou mettre à jour le schéma électrique.",
        preuve="Photo armoire et extrait documentaire.",
        tags=("doe", "electrique"),
        sources=("xlsx_mes",),
        ordre=20,
    ),
    _item(
        controle_id="DOC_003",
        section="Documentation et DOE",
        libelle="Présence de l’analyse fonctionnelle",
        methode_verification="Vérification documentaire dans le DOE ou le dossier de mise en service.",
        criticite=Criticite.majeure,
        impact="Stratégie de pilotage et réglages peu maîtrisés.",
        recommandation="Fournir l’analyse fonctionnelle et la logique de régulation.",
        preuve="Document ou extrait DOE.",
        tags=("analyse_fonctionnelle", "regulation"),
        sources=("xlsx_mes", "socol_mes"),
        ordre=30,
    ),
    _item(
        controle_id="DOC_004",
        section="Documentation et DOE",
        libelle="Présence des notices constructeurs et fiches techniques",
        methode_verification="Contrôle du dossier technique disponible sur site ou chez l’exploitant.",
        criticite=Criticite.mineure,
        impact="Maintenance ralentie et risques d’erreur de remplacement.",
        recommandation="Compléter le dossier avec notices et fiches techniques à jour.",
        preuve="Copies ou photos des notices.",
        tags=("documentation", "maintenance"),
        sources=("socol_mes",),
        ordre=40,
    ),
    _item(
        controle_id="DOC_005",
        section="Documentation et DOE",
        libelle="Présence des notes de réglage, d’équilibrage et de mise en service",
        methode_verification="Vérification du carnet de bord, du PV de mise en service et des feuilles de réglage.",
        criticite=Criticite.majeure,
        impact="Impossible de reconstituer la mise au point initiale.",
        recommandation="Formaliser et archiver les réglages initiaux, débits et équilibrages.",
        preuve="Rapport de mise en service ou feuille de réglage.",
        tags=("mise_en_service", "equilibrage", "reglage"),
        sources=("socol_mes", "tecsol_ines"),
        ordre=50,
    ),
    _item(
        controle_id="ELEC_001",
        section="Conformité électrique et sécurité",
        libelle="Raccordements électriques conformes, repérés et protégés",
        methode_verification="Contrôle visuel et comparaison au schéma électrique.",
        criticite=Criticite.critique,
        impact="Risque sécurité, panne et difficulté d’intervention.",
        recommandation="Reprendre les raccordements, protections et repérages.",
        preuve="Photos armoire, borniers et raccordements.",
        tags=("electrique", "securite"),
        sources=("xlsx_mes",),
        ordre=60,
    ),
    _item(
        controle_id="ELEC_002",
        section="Conformité électrique et sécurité",
        libelle="Mise à la terre de l’installation présente et cohérente",
        methode_verification="Contrôle visuel et, si possible, vérification de continuité.",
        criticite=Criticite.critique,
        impact="Risque électrique pour les biens et les personnes.",
        recommandation="Mettre en conformité la liaison équipotentielle et la terre.",
        preuve="Photo des liaisons et borne de terre.",
        tags=("electrique", "terre"),
        sources=("xlsx_mes",),
        ordre=70,
    ),
    _item(
        controle_id="CAP_001",
        section="Champ capteurs",
        libelle="Absence de vannes d’isolement inappropriées sur la tuyauterie capteurs",
        methode_verification="Contrôle visuel du champ et comparaison au principe hydraulique.",
        criticite=Criticite.majeure,
        impact="Risque de mauvaise manœuvre, stagnation locale ou dysfonctionnement du champ.",
        recommandation="Supprimer ou justifier les organes d’isolement inadaptés au droit du champ.",
        preuve="Photos du champ et des tuyauteries.",
        tags=("capteurs", "hydraulique"),
        sources=("xlsx_mes",),
        ordre=80,
    ),
    _item(
        controle_id="CAP_002",
        section="Champ capteurs",
        libelle="Dispositif de traversée de toiture ou de parois adapté",
        methode_verification="Contrôle visuel des traversées et de l’étanchéité bâtiment.",
        criticite=Criticite.critique,
        impact="Risque d’infiltration et de désordre bâtiment.",
        recommandation="Reprendre les traversées et l’étanchéité associée.",
        preuve="Photos détaillées des traversées.",
        tags=("capteurs", "etancheite"),
        sources=("xlsx_mes",),
        ordre=90,
    ),
    _item(
        controle_id="CAP_003",
        section="Champ capteurs",
        libelle="Supports capteurs conformes, intègres et adaptés au support",
        methode_verification="Contrôle visuel de la fixation, supportage et corrosion éventuelle.",
        criticite=Criticite.critique,
        impact="Risque structurel, arrachement ou désordre toiture.",
        recommandation="Contrôler, renforcer ou remettre en conformité les supports.",
        preuve="Photos du supportage et des fixations.",
        tags=("capteurs", "supportage", "structure"),
        sources=("xlsx_mes",),
        ordre=100,
    ),
    _item(
        controle_id="CAP_004",
        section="Champ capteurs",
        libelle="Raccordement correct des capteurs et des nourrices",
        methode_verification="Contrôle visuel et comparaison au schéma d’exécution.",
        criticite=Criticite.majeure,
        impact="Perte de performance ou dysfonctionnement hydraulique.",
        recommandation="Reprendre le raccordement du champ capteurs.",
        preuve="Photos nourrices, retours et collecteurs.",
        tags=("capteurs", "nourrices", "hydraulique"),
        sources=("xlsx_mes",),
        ordre=110,
    ),
    _item(
        controle_id="CAP_005",
        section="Champ capteurs",
        libelle="Accès capteurs sécurisé pour l’exploitation et la maintenance",
        methode_verification="Vérification des accès, protections collectives ou ligne de vie selon le cas.",
        criticite=Criticite.critique,
        impact="Risque pour les intervenants et maintenance compromise.",
        recommandation="Sécuriser les accès et moyens d’intervention.",
        preuve="Photos accès, échelle, trappe, protections.",
        tags=("capteurs", "acces", "maintenance", "securite"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=120,
    ),
    _item(
        controle_id="CAP_006",
        section="Champ capteurs",
        libelle="Absence de masque proche significatif",
        methode_verification="Observation sur site, photos et confrontation avec l’étude solaire si disponible.",
        criticite=Criticite.majeure,
        impact="Sous-performance solaire chronique.",
        recommandation="Analyser l’impact des masques et corriger si possible.",
        preuve="Photos du champ et de l’environnement proche.",
        tags=("capteurs", "masques", "performance"),
        sources=("xlsx_mes",),
        ordre=130,
    ),
    _item(
        controle_id="CAP_007",
        section="Champ capteurs",
        libelle="Orientation et inclinaison cohérentes avec le projet",
        methode_verification="Comparaison relevé terrain, visite site et étude de conception.",
        criticite=Criticite.mineure,
        impact="Rendement énergétique dégradé par rapport au prévu.",
        recommandation="Documenter ou corriger l’écart d’implantation si nécessaire.",
        preuve="Relevé terrain, photos et étude.",
        tags=("capteurs", "orientation", "inclinaison"),
        sources=("file_classification",),
        ordre=140,
    ),
    _item(
        controle_id="EQU_001",
        section="Équilibrage",
        libelle="Dispositif d’équilibrage sur chaque champ capteurs",
        methode_verification="Contrôle visuel sur chaque branche ou champ solaire.",
        criticite=Criticite.majeure,
        impact="Débits déséquilibrés et champs défavorisés.",
        recommandation="Installer ou remettre en service les organes d’équilibrage.",
        preuve="Photos des dispositifs d’équilibrage.",
        tags=("equilibrage", "debit"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=150,
    ),
    _item(
        controle_id="EQU_002",
        section="Équilibrage",
        libelle="Dispositifs d’équilibrage sécurisés, repérés et exploitables",
        methode_verification="Contrôle visuel, lisibilité des repères et possibilité de réglage.",
        criticite=Criticite.majeure,
        impact="Réglage impossible ou instable dans le temps.",
        recommandation="Rendre les organes lisibles, réglables et sécurisés.",
        preuve="Photos et valeurs de réglage si connues.",
        tags=("equilibrage", "maintenance"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=160,
    ),
    _item(
        controle_id="HYD_001",
        section="Réseau primaire solaire",
        libelle="Matériaux de tuyauterie conformes à l’usage solaire thermique",
        methode_verification="Contrôle visuel des matériaux, accessoires et état du calorifuge.",
        criticite=Criticite.critique,
        impact="Vieillissement prématuré, rupture ou incompatibilité thermique.",
        recommandation="Remplacer les matériaux non adaptés au solaire thermique.",
        preuve="Photos du réseau primaire.",
        tags=("hydraulique", "materiaux"),
        sources=("xlsx_mes",),
        ordre=170,
    ),
    _item(
        controle_id="HYD_002",
        section="Réseau primaire solaire",
        libelle="Circulation capteurs et échangeur dans le bon sens",
        methode_verification="Lecture du schéma, repérage des flux et relevés de température en fonctionnement.",
        criticite=Criticite.critique,
        impact="Installation peu productive ou non fonctionnelle.",
        recommandation="Corriger le sens hydraulique et le repérage des circuits.",
        preuve="Photos, schéma annoté et relevés terrain.",
        tags=("hydraulique", "sens_circulation"),
        sources=("xlsx_mes",),
        ordre=180,
    ),
    _item(
        controle_id="HYD_003",
        section="Réseau primaire solaire",
        libelle="Présence d’un jeu de vannes pour pompe de remplissage / rinçage / dégazage",
        methode_verification="Contrôle visuel des organes de maintenance du primaire.",
        criticite=Criticite.majeure,
        impact="Remplissage, rinçage et maintenance fortement compliqués.",
        recommandation="Ajouter un jeu de vannes dédié aux opérations de maintenance.",
        preuve="Photo des organes de raccordement.",
        tags=("hydraulique", "maintenance", "remplissage"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=190,
    ),
    _item(
        controle_id="HYD_004",
        section="Réseau primaire solaire",
        libelle="Présence d’un dégazeur sur l’aller chaud capteurs si architecture concernée",
        methode_verification="Contrôle visuel et comparaison à l’architecture hydraulique.",
        criticite=Criticite.majeure,
        impact="Bulles, pertes de circulation et baisse de performance.",
        recommandation="Ajouter ou remettre en service le dispositif de dégazage.",
        preuve="Photo du dégazeur.",
        condition={"systeme_capteurs_not_in": ["autovidangeable"]},
        tags=("hydraulique", "degazage"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=200,
    ),
    _item(
        controle_id="HYD_005",
        section="Réseau primaire solaire",
        libelle="Soupape de sécurité présente, accessible et conforme",
        methode_verification="Contrôle visuel, lecture plaque signalétique et pression de tarage.",
        criticite=Criticite.critique,
        impact="Risque de surpression et de dégradation du circuit.",
        recommandation="Mettre en conformité la soupape de sécurité.",
        preuve="Photo de la soupape et de sa plaque.",
        tags=("hydraulique", "securite", "pression"),
        sources=("xlsx_mes",),
        ordre=210,
    ),
    _item(
        controle_id="HYD_006",
        section="Réseau primaire solaire",
        libelle="Bidon de récupération avec contrôle de niveau",
        methode_verification="Contrôle visuel du dispositif de récupération.",
        criticite=Criticite.majeure,
        impact="Pertes de fluide non détectées et suivi dégradé.",
        recommandation="Installer un dispositif de récupération visible et contrôlable.",
        preuve="Photo du bidon de récupération.",
        condition={"systeme_capteurs_not_in": ["autovidangeable"]},
        tags=("hydraulique", "fluide", "securite"),
        sources=("xlsx_mes",),
        ordre=220,
    ),
    _item(
        controle_id="HYD_007",
        section="Réseau primaire solaire",
        libelle="Circulateur solaire implanté de façon cohérente avec l’architecture",
        methode_verification="Contrôle visuel et comparaison au schéma hydraulique.",
        criticite=Criticite.majeure,
        impact="Fonctionnement dégradé et maintenance plus difficile.",
        recommandation="Revoir l’implantation du circulateur si nécessaire.",
        preuve="Photo circulateur et environnement.",
        tags=("hydraulique", "circulateur"),
        sources=("xlsx_mes",),
        ordre=230,
    ),
    _item(
        controle_id="HYD_008",
        section="Réseau primaire solaire",
        libelle="Présence d’un clapet anti-retour si requis pour éviter les thermosiphons parasites",
        methode_verification="Contrôle visuel et lecture du schéma.",
        criticite=Criticite.majeure,
        impact="Circulations parasites, pertes et surchauffes localisées.",
        recommandation="Installer ou remplacer le clapet anti-retour nécessaire.",
        preuve="Photo du clapet.",
        tags=("hydraulique", "clapet", "thermosiphon"),
        sources=("xlsx_mes",),
        ordre=240,
    ),
    _item(
        controle_id="HYD_009",
        section="Réseau primaire solaire",
        libelle="Vannes 3 voies fonctionnelles si présentes",
        methode_verification="Contrôle visuel, test fonctionnel et lecture régulation si possible.",
        criticite=Criticite.majeure,
        impact="Stratégie hydraulique incorrecte ou inopérante.",
        recommandation="Réparer ou remplacer la vanne 3 voies défaillante.",
        preuve="Photo de la vanne et observation fonctionnelle.",
        tags=("hydraulique", "vanne_3_voies"),
        sources=("xlsx_mes",),
        ordre=250,
    ),
    _item(
        controle_id="HYD_010",
        section="Réseau primaire solaire",
        libelle="Calorifuge primaire continu, adapté et en bon état",
        methode_verification="Contrôle visuel sur l’ensemble du linéaire accessible.",
        criticite=Criticite.majeure,
        impact="Déperditions importantes et vieillissement accéléré.",
        recommandation="Reprendre ou compléter le calorifuge du primaire.",
        preuve="Photos des tronçons et singularités.",
        tags=("hydraulique", "calorifuge", "performance"),
        sources=("file_classification",),
        ordre=260,
    ),
    _item(
        controle_id="EXP_001",
        section="Expansion et sécurité pression",
        libelle="Présence d’un vase d’expansion adapté",
        methode_verification="Contrôle visuel et lecture plaque signalétique.",
        criticite=Criticite.critique,
        impact="Instabilité de pression et pertes de fluide.",
        recommandation="Remplacer ou redimensionner le vase d’expansion.",
        preuve="Photo du vase et de sa plaque.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("expansion", "pression"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=270,
    ),
    _item(
        controle_id="EXP_002",
        section="Expansion et sécurité pression",
        libelle="Volume du vase d’expansion suffisant",
        methode_verification="Vérification calculatoire ou cohérence avec les caractéristiques de l’installation.",
        criticite=Criticite.critique,
        impact="Ouvertures de soupape, pertes de fluide et instabilité de fonctionnement.",
        recommandation="Vérifier et corriger le dimensionnement du vase.",
        preuve="Plaque signalétique, calcul ou note technique.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("expansion", "dimensionnement"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=280,
    ),
    _item(
        controle_id="EXP_003",
        section="Expansion et sécurité pression",
        libelle="Présence d’un dispositif d’isolement et de mise à l’air pour le vase",
        methode_verification="Contrôle visuel autour du vase d’expansion.",
        criticite=Criticite.majeure,
        impact="Contrôle de précharge et maintenance difficiles.",
        recommandation="Compléter les organes autour du vase pour la maintenance.",
        preuve="Photo des organes d’isolement et purge.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("expansion", "maintenance"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=290,
    ),
    _item(
        controle_id="EXP_004",
        section="Expansion et sécurité pression",
        libelle="Raccordement du vase sur le retour froid capteurs cohérent",
        methode_verification="Contrôle visuel et comparaison au schéma.",
        criticite=Criticite.majeure,
        impact="Comportement pression/température défavorable.",
        recommandation="Reprendre le raccordement du vase si nécessaire.",
        preuve="Photo du raccordement du vase.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("expansion", "raccordement"),
        sources=("xlsx_mes",),
        ordre=300,
    ),
    _item(
        controle_id="EXP_005",
        section="Expansion et sécurité pression",
        libelle="Pression de précharge du vase conforme",
        methode_verification="Mesure ou relevé de maintenance, cohérent avec la pression de service.",
        criticite=Criticite.critique,
        impact="Dysfonctionnements répétés, cavitation ou pertes de fluide.",
        recommandation="Régler la pression de précharge du vase.",
        preuve="Relevé de pression ou CR maintenance.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("expansion", "precharge"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=310,
    ),
    _item(
        controle_id="ECH_001",
        section="Échange thermique",
        libelle="Raccordement de l’échangeur en contre-courant",
        methode_verification="Contrôle du schéma et des températures de fonctionnement.",
        criticite=Criticite.critique,
        impact="Transfert thermique dégradé et sous-performance.",
        recommandation="Reprendre le raccordement de l’échangeur en contre-courant.",
        preuve="Photo échangeur et relevés température.",
        condition={"type_echangeur_in": ["echangeur_externe"]},
        tags=("echangeur", "contre_courant"),
        sources=("xlsx_mes",),
        ordre=320,
    ),
    _item(
        controle_id="ECH_002",
        section="Échange thermique",
        libelle="Vannes d’isolement entrée/sortie échangeur présentes",
        methode_verification="Contrôle visuel des organes autour de l’échangeur.",
        criticite=Criticite.majeure,
        impact="Maintenance et intervention difficiles.",
        recommandation="Ajouter les vannes d’isolement nécessaires.",
        preuve="Photo échangeur et organes.",
        condition={"type_echangeur_in": ["echangeur_externe"]},
        tags=("echangeur", "maintenance"),
        sources=("xlsx_mes",),
        ordre=330,
    ),
    _item(
        controle_id="ECH_003",
        section="Échange thermique",
        libelle="Puissance de l’échangeur suffisante ou absence d’indice de sous-dimensionnement",
        methode_verification="Analyse étude, plaques, températures et comportement observé.",
        criticite=Criticite.majeure,
        impact="Sous-performance chronique du transfert solaire.",
        recommandation="Vérifier dimensionnement, encrassement et conditions de fonctionnement de l’échangeur.",
        preuve="Photo plaque, note et relevés.",
        condition={"type_echangeur_in": ["echangeur_externe"]},
        tags=("echangeur", "performance"),
        sources=("xlsx_mes",),
        ordre=340,
    ),
    _item(
        controle_id="STO_001",
        section="Stockage solaire",
        libelle="Ballons implantés dans un local fermé et hors gel",
        methode_verification="Contrôle visuel du local et des conditions ambiantes.",
        criticite=Criticite.critique,
        impact="Risque de gel, dégradation et exploitation dégradée.",
        recommandation="Sécuriser le local et les conditions ambiantes.",
        preuve="Photo du local technique.",
        tags=("stockage", "local", "hors_gel"),
        sources=("xlsx_mes",),
        ordre=350,
    ),
    _item(
        controle_id="STO_002",
        section="Stockage solaire",
        libelle="Accessibilité du local compatible avec le remplacement futur des ballons",
        methode_verification="Contrôle visuel des accès, portes et cheminements.",
        criticite=Criticite.mineure,
        impact="Maintenance lourde et remplacement futurs difficiles.",
        recommandation="Documenter ou améliorer l’accessibilité du stockage.",
        preuve="Photo des accès et ouvertures.",
        tags=("stockage", "accessibilite"),
        sources=("xlsx_mes",),
        ordre=360,
    ),
    _item(
        controle_id="STO_003",
        section="Stockage solaire",
        libelle="Accès complet aux piquages, brides et organes du ballon",
        methode_verification="Contrôle visuel autour des ballons.",
        criticite=Criticite.majeure,
        impact="Maintenance et inspection difficiles.",
        recommandation="Rendre les piquages et brides accessibles.",
        preuve="Photos des piquages et brides.",
        tags=("stockage", "maintenance"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=370,
    ),
    _item(
        controle_id="STO_004",
        section="Stockage solaire",
        libelle="Raccordement ballon(s) conforme au schéma et à la stratégie de stratification",
        methode_verification="Contrôle visuel et comparaison au schéma hydraulique.",
        criticite=Criticite.majeure,
        impact="Stratification dégradée ou fonctionnement anormal.",
        recommandation="Revoir le raccordement des ballons.",
        preuve="Photos des raccordements ballons.",
        tags=("stockage", "stratification"),
        sources=("xlsx_mes",),
        ordre=380,
    ),
    _item(
        controle_id="STO_005",
        section="Stockage solaire",
        libelle="Absence de clapet anti-retour parasite entre les ballons",
        methode_verification="Contrôle visuel de l’interconnexion des stockages.",
        criticite=Criticite.majeure,
        impact="Mauvais équilibrage et dysfonctionnement du stockage.",
        recommandation="Supprimer le clapet parasite ou revoir l’architecture.",
        preuve="Photo du réseau de stockage.",
        tags=("stockage", "clapet"),
        sources=("xlsx_mes",),
        ordre=390,
    ),
    _item(
        controle_id="STO_006",
        section="Stockage solaire",
        libelle="Vannes de vidange et de chasse présentes en partie basse",
        methode_verification="Contrôle visuel sur chaque ballon concerné.",
        criticite=Criticite.majeure,
        impact="Maintenance et rinçage difficiles.",
        recommandation="Installer des organes de vidange et de chasse adaptés.",
        preuve="Photo partie basse ballon.",
        tags=("stockage", "vidange"),
        sources=("xlsx_mes",),
        ordre=400,
    ),
    _item(
        controle_id="STO_007",
        section="Stockage solaire",
        libelle="Prise ou mesure de température en partie haute présente",
        methode_verification="Contrôle visuel et cohérence avec l’instrumentation disponible.",
        criticite=Criticite.majeure,
        impact="Suivi et régulation du stockage dégradés.",
        recommandation="Créer un point de mesure en partie haute du stockage.",
        preuve="Photo sonde ou piquage.",
        tags=("stockage", "temperature", "regulation"),
        sources=("xlsx_mes",),
        ordre=410,
    ),
    _item(
        controle_id="STO_008",
        section="Stockage solaire",
        libelle="Présence d’une protection cathodique du ballon si nécessaire",
        methode_verification="Contrôle visuel et lecture de la documentation du ballon.",
        criticite=Criticite.majeure,
        impact="Corrosion accélérée du stockage.",
        recommandation="Vérifier, rétablir ou entretenir la protection cathodique.",
        preuve="Photo du dispositif ou notice ballon.",
        tags=("stockage", "corrosion"),
        sources=("xlsx_mes",),
        ordre=420,
    ),
    _item(
        controle_id="STO_009",
        section="Stockage solaire",
        libelle="Calorifuge du stockage satisfaisant",
        methode_verification="Contrôle visuel de l’isolation des ballons et accessoires.",
        criticite=Criticite.majeure,
        impact="Déperditions énergétiques élevées.",
        recommandation="Reprendre ou compléter l’isolation du stockage.",
        preuve="Photos du calorifuge.",
        tags=("stockage", "calorifuge"),
        sources=("xlsx_mes",),
        ordre=430,
    ),
    _item(
        controle_id="STO_010",
        section="Stockage solaire",
        libelle="Coudes vers le bas sur les piquages du ballon si requis",
        methode_verification="Contrôle visuel des piquages.",
        criticite=Criticite.mineure,
        impact="Stratification moins favorable.",
        recommandation="Optimiser les piquages du ballon si nécessaire.",
        preuve="Photo des piquages.",
        tags=("stockage", "stratification"),
        sources=("xlsx_mes",),
        ordre=440,
    ),
    _item(
        controle_id="ECS_001",
        section="ECS et bouclage",
        libelle="Soupape de sécurité du ballon présente",
        methode_verification="Contrôle visuel des organes de sécurité ECS.",
        criticite=Criticite.critique,
        impact="Risque sécurité sur la production d’ECS.",
        recommandation="Mettre en conformité la soupape du ballon.",
        preuve="Photo de la soupape ballon.",
        tags=("ecs", "securite"),
        sources=("xlsx_mes",),
        ordre=450,
    ),
    _item(
        controle_id="ECS_002",
        section="ECS et bouclage",
        libelle="Mitigeur présent si nécessaire à la sécurité d’usage",
        methode_verification="Contrôle visuel, analyse du schéma et conditions de distribution.",
        criticite=Criticite.critique,
        impact="Risque de brûlure aux points de puisage.",
        recommandation="Installer, régler ou remettre en service le mitigeur.",
        preuve="Photo du mitigeur et du schéma.",
        tags=("ecs", "mitigeur", "sanitaire"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=460,
    ),
    _item(
        controle_id="ECS_003",
        section="ECS et bouclage",
        libelle="Température maximale de l’ECS respectée aux points de puisage",
        methode_verification="Mesure de température aux points de puisage représentatifs.",
        criticite=Criticite.critique,
        impact="Risque de brûlure ou non-conformité d’usage.",
        recommandation="Revoir le mitigeage et les consignes ECS.",
        preuve="Relevés de température.",
        tags=("ecs", "temperature", "sanitaire"),
        sources=("xlsx_mes",),
        ordre=470,
    ),
    _item(
        controle_id="ECS_004",
        section="ECS et bouclage",
        libelle="Raccordement correct du bouclage",
        methode_verification="Contrôle visuel et comparaison au schéma hydraulique.",
        criticite=Criticite.majeure,
        impact="Distribution ECS dégradée et pertes accrues.",
        recommandation="Corriger le raccordement du bouclage.",
        preuve="Photos du réseau ECS.",
        tags=("ecs", "bouclage"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=480,
    ),
    _item(
        controle_id="ECS_005",
        section="ECS et bouclage",
        libelle="Présence des clapets anti-retour",
        methode_verification="Contrôle visuel des organes sur le réseau ECS.",
        criticite=Criticite.majeure,
        impact="Circulations parasites et dysfonctionnements.",
        recommandation="Installer ou remplacer les clapets manquants ou défectueux.",
        preuve="Photos des organes.",
        tags=("ecs", "clapet"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=490,
    ),
    _item(
        controle_id="ECS_006",
        section="ECS et bouclage",
        libelle="Bouclage calorifugé",
        methode_verification="Contrôle visuel du réseau de bouclage.",
        criticite=Criticite.majeure,
        impact="Déperditions importantes et baisse du rendement global.",
        recommandation="Reprendre ou compléter l’isolation du bouclage.",
        preuve="Photos des tuyauteries de bouclage.",
        tags=("ecs", "bouclage", "calorifuge"),
        sources=("xlsx_mes",),
        ordre=500,
    ),
    _item(
        controle_id="REG_001",
        section="Régulation et automatismes",
        libelle="Régulateur identifié, accessible et opérationnel",
        methode_verification="Contrôle visuel, lecture interface et vérification de base.",
        criticite=Criticite.majeure,
        impact="Pilotage dégradé de l’installation.",
        recommandation="Réparer, remplacer ou documenter le régulateur.",
        preuve="Photo écran régulation.",
        tags=("regulation", "automatismes"),
        sources=("tecsol_ines", "costic"),
        ordre=510,
    ),
    _item(
        controle_id="REG_002",
        section="Régulation et automatismes",
        libelle="Sondes reconnues et valeurs plausibles",
        methode_verification="Lecture du régulateur et comparaison aux mesures terrain.",
        criticite=Criticite.critique,
        impact="Commande erronée de l’installation solaire.",
        recommandation="Contrôler les sondes, leur câblage et leur implantation.",
        preuve="Capture régulateur et mesures terrain.",
        tags=("regulation", "sondes"),
        sources=("page_cegibat", "tecsol_ines"),
        ordre=520,
    ),
    _item(
        controle_id="REG_003",
        section="Régulation et automatismes",
        libelle="Paramètres de démarrage et d’arrêt solaire cohérents",
        methode_verification="Lecture des paramètres de régulation et comparaison à la logique de fonctionnement attendue.",
        criticite=Criticite.majeure,
        impact="Sous-performance ou marche parasite.",
        recommandation="Reprendre les seuils de démarrage/arrêt et les différentiels.",
        preuve="Capture des paramètres.",
        tags=("regulation", "consignes"),
        sources=("web_costic", "tecsol_ines"),
        ordre=530,
    ),
    _item(
        controle_id="REG_004",
        section="Régulation et automatismes",
        libelle="Stratégie de priorité solaire conforme à l’analyse fonctionnelle",
        methode_verification="Comparaison analyse fonctionnelle, schéma et paramétrage régulation.",
        criticite=Criticite.majeure,
        impact="Mauvaise valorisation de l’énergie solaire.",
        recommandation="Revoir la stratégie de pilotage et les priorités.",
        preuve="Analyse fonctionnelle et captures de paramètres.",
        tags=("regulation", "strategie"),
        sources=("web_costic", "socol_mes"),
        ordre=540,
    ),
    _item(
        controle_id="REG_005",
        section="Régulation et automatismes",
        libelle="Gestion des sécurités haute température et surchauffe opérationnelle",
        methode_verification="Lecture paramètres, entretien exploitant et observation des historiques si disponibles.",
        criticite=Criticite.critique,
        impact="Vieillissement accéléré, arrêts répétés et pertes de disponibilité.",
        recommandation="Mettre en place une stratégie de sécurité thermique adaptée.",
        preuve="Paramètres, historiques et observations terrain.",
        tags=("regulation", "surchauffe", "securite"),
        sources=("tecsol_ines",),
        ordre=550,
    ),
    _item(
        controle_id="MET_001",
        section="Métrologie et instrumentation",
        libelle="Manomètre de contrôle du circuit solaire présent et lisible",
        methode_verification="Contrôle visuel et lisibilité de l’indication.",
        criticite=Criticite.majeure,
        impact="Diagnostic de pression impossible.",
        recommandation="Installer ou remplacer le manomètre.",
        preuve="Photo du manomètre.",
        tags=("metrologie", "pression"),
        sources=("xlsx_mes",),
        ordre=560,
    ),
    _item(
        controle_id="MET_002",
        section="Métrologie et instrumentation",
        libelle="Débitmètre(s) présent(s) et lisibles",
        methode_verification="Contrôle visuel et possibilité de relever le débit.",
        criticite=Criticite.majeure,
        impact="Réglage et diagnostic impossibles.",
        recommandation="Installer ou remettre en état les débitmètres.",
        preuve="Photo des débitmètres.",
        tags=("metrologie", "debit"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=570,
    ),
    _item(
        controle_id="MET_003",
        section="Métrologie et instrumentation",
        libelle="Sonde d’ensoleillement bien placée si présente",
        methode_verification="Contrôle visuel de l’implantation et de l’environnement immédiat.",
        criticite=Criticite.mineure,
        impact="Suivi ou pilotage biaisé.",
        recommandation="Repositionner ou fiabiliser la sonde d’ensoleillement.",
        preuve="Photo de la sonde.",
        tags=("metrologie", "ensoleillement"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=580,
    ),
    _item(
        controle_id="MET_004",
        section="Métrologie et instrumentation",
        libelle="Seuil d’éclairement cohérent si utilisé dans la régulation",
        methode_verification="Lecture du paramétrage et cohérence avec la stratégie de contrôle.",
        criticite=Criticite.majeure,
        impact="Mises en marche inadaptées.",
        recommandation="Corriger le paramétrage du seuil d’éclairement.",
        preuve="Capture du paramètre.",
        tags=("metrologie", "regulation"),
        sources=("xlsx_mes",),
        ordre=590,
    ),
    _item(
        controle_id="MET_005",
        section="Métrologie et instrumentation",
        libelle="Sonde de température capteur bien placée",
        methode_verification="Contrôle visuel de l’emplacement réel de la sonde.",
        criticite=Criticite.majeure,
        impact="Mesures fausses et régulation erronée.",
        recommandation="Repositionner la sonde capteur.",
        preuve="Photo de la sonde capteur.",
        tags=("metrologie", "sonde_capteur"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=600,
    ),
    _item(
        controle_id="MET_006",
        section="Métrologie et instrumentation",
        libelle="Sonde de température bas de ballon solaire bien placée",
        methode_verification="Contrôle visuel et cohérence avec la stratégie de charge solaire.",
        criticite=Criticite.majeure,
        impact="Commande solaire inadaptée.",
        recommandation="Repositionner la sonde bas ballon.",
        preuve="Photo de la sonde ballon.",
        tags=("metrologie", "sonde_ballon"),
        sources=("xlsx_mes",),
        ordre=610,
    ),
    _item(
        controle_id="MET_007",
        section="Métrologie et instrumentation",
        libelle="Dispositif de prélèvement du liquide caloporteur disponible",
        methode_verification="Contrôle visuel du point de prélèvement.",
        criticite=Criticite.majeure,
        impact="Analyse du fluide impossible.",
        recommandation="Installer un point de prélèvement du liquide caloporteur.",
        preuve="Photo du point de prélèvement.",
        tags=("metrologie", "fluide"),
        sources=("xlsx_mes",),
        ordre=620,
    ),
    _item(
        controle_id="MET_008",
        section="Métrologie et instrumentation",
        libelle="Thermomètres ou mesures entrée/sortie échangeur disponibles",
        methode_verification="Contrôle visuel et possibilité de relever les températures.",
        criticite=Criticite.majeure,
        impact="Bilan thermique échangeur impossible.",
        recommandation="Installer des points de mesure sur l’échangeur.",
        preuve="Photos des thermomètres ou points de mesure.",
        condition={"type_echangeur_in": ["echangeur_externe"]},
        tags=("metrologie", "echangeur", "temperature"),
        sources=("xlsx_mes",),
        ordre=630,
    ),
    _item(
        controle_id="MET_009",
        section="Métrologie et instrumentation",
        libelle="Compteur volumétrique eau froide disponible et cohérent avec le suivi",
        methode_verification="Contrôle visuel et comparaison au schéma de comptage.",
        criticite=Criticite.majeure,
        impact="Suivi de productivité incomplet ou non fiable.",
        recommandation="Installer ou fiabiliser le comptage d’eau froide.",
        preuve="Photo du compteur et schéma.",
        tags=("metrologie", "comptage", "eau_froide"),
        sources=("xlsx_mes", "page_cegibat"),
        ordre=640,
    ),
    _item(
        controle_id="MET_010",
        section="Métrologie et instrumentation",
        libelle="Comptage solaire utile disponible et exploitable",
        methode_verification="Contrôle de l’architecture de comptage et des données réellement accessibles.",
        criticite=Criticite.majeure,
        impact="Performance solaire non objectivable.",
        recommandation="Mettre en place un comptage solaire utile pertinent.",
        preuve="Schéma de comptage et photo des capteurs/compteurs.",
        condition={"type_comptage_any_in": ["solaire_utile_direct", "solaire_utile_indirect", "solaire_primaire"]},
        tags=("metrologie", "comptage", "performance"),
        sources=("file_classification", "page_cegibat"),
        ordre=650,
    ),
    _item(
        controle_id="MES_001",
        section="Essais, rinçage et fluide",
        libelle="Tests d’étanchéité conformes et tracés",
        methode_verification="Vérification du PV d’essai ou de l’historique disponible.",
        criticite=Criticite.critique,
        impact="Fiabilité de l’installation non démontrée.",
        recommandation="Retrouver, refaire et archiver les essais d’étanchéité.",
        preuve="PV d’essai ou rapport d’intervention.",
        tags=("essais", "etancheite"),
        sources=("xlsx_mes",),
        ordre=660,
    ),
    _item(
        controle_id="MES_002",
        section="Essais, rinçage et fluide",
        libelle="Pression d’épreuve de référence connue",
        methode_verification="Vérification documentaire ou historique chantier.",
        criticite=Criticite.mineure,
        impact="Référentiel d’essai absent ou imprécis.",
        recommandation="Documenter la pression d’épreuve de référence.",
        preuve="PV ou note technique.",
        tags=("essais", "pression_epreuve"),
        sources=("xlsx_mes",),
        ordre=670,
    ),
    _item(
        controle_id="MES_003",
        section="Essais, rinçage et fluide",
        libelle="Pression d’épreuve réellement appliquée conforme",
        methode_verification="Vérification PV d’essai.",
        criticite=Criticite.majeure,
        impact="Qualification du réseau incomplète.",
        recommandation="Revoir la procédure d’épreuve si nécessaire.",
        preuve="PV d’essai.",
        tags=("essais", "pression_epreuve"),
        sources=("xlsx_mes",),
        ordre=680,
    ),
    _item(
        controle_id="MES_004",
        section="Essais, rinçage et fluide",
        libelle="Pression mesurée à la fin de l’essai renseignée",
        methode_verification="Vérification PV d’essai.",
        criticite=Criticite.majeure,
        impact="Étanchéité non démontrée de façon probante.",
        recommandation="Tracer systématiquement la mesure finale d’essai.",
        preuve="PV d’essai.",
        tags=("essais", "tracabilite"),
        sources=("xlsx_mes",),
        ordre=690,
    ),
    _item(
        controle_id="MES_005",
        section="Essais, rinçage et fluide",
        libelle="Réseau rincé avant mise en service",
        methode_verification="Vérification PV, historique ou éléments concordants d’exploitation.",
        criticite=Criticite.majeure,
        impact="Encrassement, dysfonctionnements et dérives.",
        recommandation="Procéder à un rinçage conforme et traçable.",
        preuve="PV ou note maintenance.",
        tags=("essais", "rincage"),
        sources=("xlsx_mes", "tecsol_ines"),
        ordre=700,
    ),
    _item(
        controle_id="MES_006",
        section="Essais, rinçage et fluide",
        libelle="Liquide caloporteur en état satisfaisant",
        methode_verification="Prélèvement, analyse, historique ou inspection visuelle.",
        criticite=Criticite.majeure,
        impact="Corrosion, baisse de performance et vieillissement accéléré.",
        recommandation="Analyser puis remplacer ou corriger le fluide si nécessaire.",
        preuve="Photo, fiche analyse ou CR maintenance.",
        condition={"systeme_capteurs_in": ["sous_pression"]},
        tags=("fluide", "maintenance"),
        sources=("xlsx_mes",),
        ordre=710,
    ),
    _item(
        controle_id="SUP_001",
        section="Supervision et télégestion",
        libelle="Télécontrôleur conforme et identifié",
        methode_verification="Contrôle visuel et identification de l’équipement de supervision.",
        criticite=Criticite.majeure,
        impact="Suivi de fonctionnement dégradé.",
        recommandation="Mettre à niveau ou documenter le télécontrôleur.",
        preuve="Photo de l’équipement.",
        tags=("supervision", "telecontrole"),
        sources=("xlsx_mes", "page_cegibat"),
        ordre=720,
    ),
    _item(
        controle_id="SUP_002",
        section="Supervision et télégestion",
        libelle="Connexion à distance fonctionnelle",
        methode_verification="Test de connexion ou preuve récente de téléaccès.",
        criticite=Criticite.majeure,
        impact="Diagnostic et assistance à distance impossibles.",
        recommandation="Rétablir la connexion à distance et les accès exploitant.",
        preuve="Capture de connexion ou preuve d’accès.",
        tags=("supervision", "telecontrole", "connectivite"),
        sources=("xlsx_mes", "page_cegibat"),
        ordre=730,
    ),
    _item(
        controle_id="SUP_003",
        section="Supervision et télégestion",
        libelle="Historique des données disponible et exploitable",
        methode_verification="Contrôle des courbes, exports et archives disponibles.",
        criticite=Criticite.majeure,
        impact="Dérives de fonctionnement non détectées.",
        recommandation="Mettre en place un historique exploitable avec export ou consultation.",
        preuve="Capture des courbes ou export.",
        tags=("supervision", "historique", "monitoring"),
        sources=("page_cegibat", "tecsol_ines"),
        ordre=740,
    ),
    _item(
        controle_id="EXPLOIT_001",
        section="Exploitation et maintenance",
        libelle="Contrat de maintenance identifié",
        methode_verification="Vérification documentaire et échanges avec le responsable de site.",
        criticite=Criticite.majeure,
        impact="Cadre d’entretien insuffisant ou non formalisé.",
        recommandation="Formaliser un contrat de maintenance adapté au système solaire.",
        preuve="Contrat ou extrait de contrat.",
        tags=("maintenance", "contrat"),
        sources=("page_cegibat", "tecsol_ines"),
        ordre=750,
    ),
    _item(
        controle_id="EXPLOIT_002",
        section="Exploitation et maintenance",
        libelle="Visite annuelle réalisée et tracée",
        methode_verification="Lecture de l’historique maintenance ou carnet d’entretien.",
        criticite=Criticite.majeure,
        impact="Dérives non détectées et pérennité réduite.",
        recommandation="Planifier un entretien annuel documenté, idéalement au printemps.",
        preuve="Compte rendu de maintenance.",
        tags=("maintenance", "visite_annuelle"),
        sources=("page_cegibat", "tecsol_ines"),
        ordre=760,
    ),
    _item(
        controle_id="EXPLOIT_003",
        section="Exploitation et maintenance",
        libelle="Carnet de bord de l’installation disponible",
        methode_verification="Vérification documentaire sur site ou chez l’exploitant.",
        criticite=Criticite.majeure,
        impact="Historique d’exploitation et d’alarmes perdu.",
        recommandation="Mettre en place un carnet de bord ou dossier d’exploitation structuré.",
        preuve="Carnet, fichier ou dossier exploitant.",
        tags=("maintenance", "carnet_de_bord"),
        sources=("socol_mes", "page_cegibat"),
        ordre=770,
    ),
    _item(
        controle_id="PERF_001",
        section="Performance observée",
        libelle="Débits mesurés cohérents avec les attentes d’exploitation",
        methode_verification="Relevés terrain, équilibrage, étude et observation du comportement.",
        criticite=Criticite.majeure,
        impact="Mauvais transfert énergétique et performance dégradée.",
        recommandation="Régler les débits et vérifier les pertes de charge.",
        preuve="Relevés de débit ou observation exploitant.",
        tags=("performance", "debit"),
        sources=("web_costic", "tecsol_ines"),
        ordre=780,
    ),
    _item(
        controle_id="PERF_002",
        section="Performance observée",
        libelle="Écart de température primaire cohérent en fonctionnement",
        methode_verification="Mesure dynamique sur une séquence de fonctionnement solaire.",
        criticite=Criticite.majeure,
        impact="Performance douteuse, instable ou sous-optimale.",
        recommandation="Réaliser une analyse dynamique et corriger hydraulique ou régulation.",
        preuve="Relevés de température.",
        tags=("performance", "delta_t"),
        sources=("web_costic", "page_cegibat"),
        ordre=790,
    ),
    _item(
        controle_id="PERF_003",
        section="Performance observée",
        libelle="Production solaire utile suivie et interprétable",
        methode_verification="Analyse supervision, comptage et cohérence des données disponibles.",
        criticite=Criticite.majeure,
        impact="Performance réelle non objectivable.",
        recommandation="Mettre en place un suivi énergétique pertinent et comparatif.",
        preuve="Courbes, exports ou tableau de bord.",
        tags=("performance", "productivite", "monitoring"),
        sources=("page_cegibat", "tecsol_ines"),
        ordre=800,
    ),
]


def validate_catalog(catalog: Iterable[ControleCatalogueItem]) -> None:
    items = list(catalog)
    if not items:
        raise ControlCatalogError("Le catalogue de contrôles est vide.")

    ids: set[str] = set()
    section_by_id: dict[str, str] = {}
    valid_prefixes = {
        "DOC", "ELEC", "CAP", "EQU", "HYD", "EXP", "ECH", "STO",
        "ECS", "REG", "MET", "MES", "SUP", "EXPLOIT", "PERF",
    }

    for item in items:
        if not isinstance(item, ControleCatalogueItem):
            raise ControlCatalogError("Le catalogue contient un élément invalide.")

        if item.controle_id in ids:
            raise ControlCatalogError(f"Identifiant de contrôle dupliqué : {item.controle_id}")
        ids.add(item.controle_id)

        if "_" not in item.controle_id:
            raise ControlCatalogError(f"Format d’identifiant invalide : {item.controle_id}")

        prefix = item.controle_id.split("_", 1)[0]
        if prefix not in valid_prefixes:
            raise ControlCatalogError(
                f"Préfixe d’identifiant non autorisé pour {item.controle_id} : {prefix}"
            )

        section_by_id[item.controle_id] = item.section

    if len({i.section for i in items}) < 5:
        raise ControlCatalogError("Le catalogue semble trop pauvre : nombre de sections insuffisant.")

    # contrôle simple de cohérence globale de classement
    for item in items:
        if item.section == "Échange thermique" and not item.controle_id.startswith("ECH_"):
            raise ControlCatalogError(f"Incohérence section/ID détectée pour {item.controle_id}.")
        if item.section == "Stockage solaire" and not item.controle_id.startswith("STO_"):
            raise ControlCatalogError(f"Incohérence section/ID détectée pour {item.controle_id}.")
        if item.section == "Régulation et automatismes" and not item.controle_id.startswith("REG_"):
            raise ControlCatalogError(f"Incohérence section/ID détectée pour {item.controle_id}.")

    # détection douce des ordres dupliqués dans une même section
    by_section: dict[str, set[int]] = {}
    for item in items:
        used = by_section.setdefault(item.section, set())
        if item.ordre in used:
            raise ControlCatalogError(
                f"Ordre dupliqué dans la section '{item.section}' pour {item.controle_id}."
            )
        used.add(item.ordre)


def get_all_controls() -> list[ControleCatalogueItem]:
    return list(CONTROL_CATALOG)


def get_sections() -> list[str]:
    return sorted({item.section for item in CONTROL_CATALOG})


def get_controls_by_section(section: str) -> list[ControleCatalogueItem]:
    section_clean = _clean_text(section, "section")
    return sorted(
        [item for item in CONTROL_CATALOG if item.section == section_clean and item.actif],
        key=lambda x: (x.ordre, x.controle_id),
    )


def get_control_by_id(controle_id: str) -> ControleCatalogueItem:
    cid = _clean_text(controle_id, "controle_id")
    for item in CONTROL_CATALOG:
        if item.controle_id == cid:
            return item
    raise KeyError(f"Contrôle introuvable : {cid}")


def filter_controls(
    *,
    section: str | None = None,
    contexte: Mapping[str, Any] | None = None,
    criticites: Iterable[Criticite | str] | None = None,
    actif_only: bool = True,
) -> list[ControleCatalogueItem]:
    normalized_criticites: set[str] | None = None
    if criticites is not None:
        normalized_criticites = {
            c.value if isinstance(c, Criticite) else str(c).strip()
            for c in criticites
        }

    result: list[ControleCatalogueItem] = []
    for item in CONTROL_CATALOG:
        if actif_only and not item.actif:
            continue
        if section and item.section != section:
            continue
        if normalized_criticites and item.criticite_par_defaut.value not in normalized_criticites:
            continue
        if not item.is_applicable(contexte):
            continue
        result.append(item)

    return sorted(result, key=lambda x: (x.section, x.ordre, x.controle_id))


def export_catalog_as_dicts() -> list[dict[str, Any]]:
    return [item.to_dict() for item in CONTROL_CATALOG]


def build_validation_report() -> dict[str, Any]:
    validate_catalog(CONTROL_CATALOG)
    sections = get_sections()
    return {
        "status": "ok",
        "total_controles": len(CONTROL_CATALOG),
        "total_sections": len(sections),
        "sections": sections,
        "criticites": {
            level.value: sum(1 for item in CONTROL_CATALOG if item.criticite_par_defaut == level)
            for level in Criticite
        },
        "controls_without_conditions": sum(
            1 for item in CONTROL_CATALOG if not item.condition_applicabilite
        ),
        "controls_with_conditions": sum(
            1 for item in CONTROL_CATALOG if item.condition_applicabilite
        ),
    }


validate_catalog(CONTROL_CATALOG)
VALIDATION_REPORT = build_validation_report()


if __name__ == "__main__":
    from pprint import pprint

    pprint(VALIDATION_REPORT)