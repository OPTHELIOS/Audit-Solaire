from enum import Enum


class AuditStatus(str, Enum):
    BROUILLON = "brouillon"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    VALIDE = "valide"
    ARCHIVE = "archive"


class Verdict(str, Enum):
    CONFORME = "conforme"
    DEFAUT = "defaut"
    NON_CONTROLABLE = "non_controlable"
    SANS_OBJET = "sans_objet"
    NON_RENSEIGNE = "non_renseigne"


class Criticite(str, Enum):
    INFO = "info"
    MINEURE = "mineure"
    MAJEURE = "majeure"
    CRITIQUE = "critique"


class PrioriteAction(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TypePreuve(str, Enum):
    PHOTO = "photo"
    DOCUMENT = "document"
    MESURE = "mesure"
    CAPTURE = "capture"
    PLAQUE_SIGNALETIQUE = "plaque_signaletique"


class LotTechnique(str, Enum):
    DOCUMENTATION = "documentation"
    ELECTRICITE = "electricite"
    CAPTEURS = "capteurs"
    TOITURE = "toiture"
    EQUILIBRAGE = "equilibrage"
    HYDRAULIQUE = "hydraulique"
    EXPANSION = "expansion"
    ECHANGEUR_STOCKAGE = "echangeur_stockage"
    ECS_BOUCLAGE = "ecs_bouclage"
    METROLOGIE = "metrologie"
    REGULATION = "regulation"
    COMPTEURS = "compteurs"
    SECURITE = "securite"