from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from domain.audit_studio import AuditStudioBlock, ModeRapport
from domain.enums import TypePreuve


class StatutAudit(str, Enum):
    brouillon = "brouillon"
    en_cours = "en_cours"
    termine = "termine"
    archive = "archive"


class VerdictControle(str, Enum):
    conforme = "conforme"
    non_conforme = "non_conforme"
    non_verifiable = "non_verifiable"
    non_present = "non_present"
    sans_objet = "sans_objet"


class Criticite(str, Enum):
    mineure = "mineure"
    majeure = "majeure"
    critique = "critique"


class TypeMesure(str, Enum):
    temperature = "temperature"
    pression = "pression"
    debit = "debit"
    concentration_antigel = "concentration_antigel"
    energie = "energie"
    autre = "autre"


class AuditMeta(BaseModel):
    # CORRECTIF : `audit_id` etait utilise (audit.meta.audit_id) par
    # services/evidence_service.py et ui/pages/_03_preuves.py pour nommer le
    # dossier local des preuves, mais n'existait pas sur ce modele -> chaque
    # ajout de preuve levait une AttributeError des la premiere ligne. Cet
    # identifiant est stable (genere une seule fois a la creation de
    # l'audit, y compris avant toute sauvegarde) et independant de
    # `numero_audit`, qui lui peut etre modifie en cours de saisie. Il sert
    # aussi de nom de dossier cote SharePoint
    # (voir repositories/sharepoint_repository.py).
    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    # CORRECTIF (lisibilite SharePoint) : le dossier cree cote SharePoint
    # portait jusque-la le nom brut de `audit_id` (un UUID illisible dans la
    # navigation SharePoint). Ce champ memorise le nom de dossier lisible
    # (slug du nom d'operation/commune + suffixe d'unicite) une fois calcule
    # au premier envoi cloud, pour que tous les envois suivants (JSON,
    # preuves) utilisent systematiquement le meme dossier. Voir
    # `repositories/sharepoint_repository.get_cloud_folder_name`.
    dossier_cloud: Optional[str] = None
    numero_audit: str = Field(default_factory=lambda: f"AUD-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    statut: StatutAudit = StatutAudit.brouillon
    date_audit: date = Field(default_factory=date.today)
    auditeur: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version_modele: str = "1.0"


class Adresse(BaseModel):
    ligne_1: Optional[str] = None
    ligne_2: Optional[str] = None
    code_postal: Optional[str] = None
    commune: Optional[str] = None
    departement: Optional[str] = None
    pays: str = "France"


class Contact(BaseModel):
    nom: Optional[str] = None
    fonction: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    organisme: Optional[str] = None


class Projet(BaseModel):
    operation: Optional[str] = None
    maitre_ouvrage: Optional[str] = None
    exploitant: Optional[str] = None
    mainteneur: Optional[str] = None
    adresse: Adresse = Field(default_factory=Adresse)
    contact_site: Contact = Field(default_factory=Contact)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    commentaires_generaux: Optional[str] = None
    # Photo affichee en page de garde du rapport DOCX (distincte des preuves
    # de "Preuves et annexes", qui documentent des constats precis). Choisie
    # explicitement par l'auditeur sur la page Dossier.
    photo_couverture_path: Optional[str] = None


class ChampCapteurs(BaseModel):
    marque_modele: Optional[str] = None
    nombre_capteurs: int = 0
    nombre_rangees: int = 0
    surface_unitaire_m2: Optional[float] = None
    surface_totale_m2: Optional[float] = None
    azimut_deg: Optional[float] = None
    inclinaison_deg: Optional[float] = None
    type_capteur: Optional[str] = None


class StockageSolaire(BaseModel):
    nombre_ballons: int = 0
    volume_total_litres: Optional[float] = None
    details_ballons: list[str] = Field(default_factory=list)


class EquipementsTechniques(BaseModel):
    circulateur_solaire: Optional[str] = None
    regulateur: Optional[str] = None
    echangeur: Optional[str] = None
    vase_expansion: Optional[str] = None
    debitmetre: Optional[str] = None
    compteur_energie: Optional[str] = None


class ClassificationInstallation(BaseModel):
    systeme_capteurs: Optional[str] = None
    type_echangeur: Optional[str] = None
    type_stockage: Optional[str] = None
    type_comptage: list[str] = Field(default_factory=list)


class Installation(BaseModel):
    type_installation: Optional[str] = None
    usage_principal: Optional[str] = None
    annee_mise_en_service: Optional[int] = None
    description_generale: Optional[str] = None

    schema_hydraulique_disponible: bool = False
    schema_electrique_disponible: bool = False
    analyse_fonctionnelle_disponible: bool = False
    telegestion_presente: bool = False

    classification: ClassificationInstallation = Field(default_factory=ClassificationInstallation)

    champ_capteurs: ChampCapteurs = Field(default_factory=ChampCapteurs)
    stockage_solaire: StockageSolaire = Field(default_factory=StockageSolaire)
    equipements: EquipementsTechniques = Field(default_factory=EquipementsTechniques)


class ControleCatalogueItem(BaseModel):
    controle_id: str
    section: str
    sous_section: Optional[str] = None
    lot: Optional[str] = None
    libelle: str
    description_controle: Optional[str] = None
    methode_verification: Optional[str] = None
    criticite_par_defaut: Criticite = Criticite.mineure
    impact_defaut: Optional[str] = None
    recommandation_type: Optional[str] = None
    preuve_attendue: Optional[str] = None
    condition_applicabilite: dict = Field(default_factory=dict)


class Preuve(BaseModel):
    """Piece justificative (photo, document, mesure...) rattachee a un audit.

    NOTE (correctif) : ce modele a ete aligne sur les champs reellement
    utilises par `services/evidence_service.py` et `ui/pages/_03_preuves.py`
    (fichier_path, nom_original, date_capture, auteur). Auparavant, les noms
    de champs divergeaient et Pydantic ignorait silencieusement les donnees
    envoyees, ce qui faisait perdre le chemin du fichier enregistre.
    """

    preuve_id: str = Field(default_factory=lambda: f"PRV-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}")
    type_preuve: TypePreuve = TypePreuve.PHOTO
    fichier_path: Optional[str] = None
    nom_original: Optional[str] = None
    section: Optional[str] = None
    controle_id: Optional[str] = None
    legende: Optional[str] = None
    commentaire: Optional[str] = None
    auteur: Optional[str] = None
    date_capture: datetime = Field(default_factory=datetime.now)
    # URL SharePoint du fichier une fois envoye dans le cloud (voir
    # services/evidence_service.py::_try_cloud_backup). Reste a None si
    # l'envoi cloud a echoue ou n'est pas configure : le fichier local
    # (fichier_path) demeure la reference dans ce cas.
    cloud_url: Optional[str] = None


class ConstatControle(BaseModel):
    controle_id: str
    section: str
    libelle: str
    verdict: VerdictControle | None = None
    criticite: Criticite = Criticite.mineure
    criticite_finale: Criticite = Criticite.mineure
    observation: Optional[str] = None
    preuve_ids: list[str] = Field(default_factory=list)
    preuve_documentaire: Optional[str] = None
    photos: list[str] = Field(default_factory=list)
    recommandation: Optional[str] = None
    recommandation_personnalisee: Optional[str] = None
    non_verifiable_raison: Optional[str] = None


class DocumentFourni(BaseModel):
    """Document administratif/technique attendu pour le dossier (DOE, plans,
    garanties...), voir `domain/documents_catalog.py`. Distinct des preuves
    de "Preuves et annexes" (qui documentent des CONSTATS terrain) : ici on
    trace la complétude documentaire globale du dossier."""

    code: str
    libelle: str
    fourni: bool = False
    fichier_path: Optional[str] = None
    commentaire: Optional[str] = None


class ReleveMesure(BaseModel):
    """Relevé de mesure horodaté pris sur site (température, pression,
    débit, concentration antigel...), voir `domain/releves_catalog.py` pour
    les modèles usuels. Rattachable à un point de contrôle mais pas
    obligatoire (certains relevés sont généraux, pas liés à un point précis).
    """

    releve_id: str = Field(default_factory=lambda: str(uuid4()))
    type_mesure: TypeMesure = TypeMesure.temperature
    libelle: str
    valeur: float = 0.0
    unite: str = ""
    controle_id: Optional[str] = None
    section: Optional[str] = None
    date_mesure: datetime = Field(default_factory=datetime.now)
    commentaire: Optional[str] = None


class SyntheseAudit(BaseModel):
    note_globale_sur_10: Optional[float] = None
    conclusion_generale: Optional[str] = None
    points_forts: list[str] = Field(default_factory=list)
    points_sensibles: list[str] = Field(default_factory=list)
    priorites_p1: list[str] = Field(default_factory=list)
    priorites_p2: list[str] = Field(default_factory=list)
    priorites_p3: list[str] = Field(default_factory=list)


class Audit(BaseModel):
    meta: AuditMeta = Field(default_factory=AuditMeta)
    projet: Projet = Field(default_factory=Projet)
    installation: Installation = Field(default_factory=Installation)
    constats: list[ConstatControle] = Field(default_factory=list)
    preuves: list[Preuve] = Field(default_factory=list)
    documents_fournis: list[DocumentFourni] = Field(default_factory=list)
    releves: list[ReleveMesure] = Field(default_factory=list)
    synthese: SyntheseAudit = Field(default_factory=SyntheseAudit)
    mode_rapport: ModeRapport = ModeRapport.audit_complet
    studio: AuditStudioBlock = Field(default_factory=AuditStudioBlock)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _merge_legacy_mode_rapport(cls, data: Any) -> Any:
        # Legacy JSON may carry mode_rapport only at the root. Fold it into the
        # studio block so studio.mode_rapport is the canonical source going forward.
        if not isinstance(data, dict):
            return data
        root_mode = data.get("mode_rapport")
        studio = data.get("studio")
        if root_mode is not None and isinstance(studio, dict) and "mode_rapport" not in studio:
            studio["mode_rapport"] = root_mode
        elif root_mode is not None and studio is None:
            data["studio"] = {"mode_rapport": root_mode}
        return data

    @model_validator(mode="after")
    def _sync_mode_rapport(self) -> "Audit":
        # Single source of truth: studio.mode_rapport. The root field mirrors it
        # for backward-compatible reads and JSON exports.
        if self.mode_rapport != self.studio.mode_rapport:
            self.mode_rapport = self.studio.mode_rapport
        return self

    def set_mode_rapport(self, mode: ModeRapport) -> None:
        # Always update via this helper so the root mirror stays in sync with the
        # studio block between validation cycles.
        self.studio.mode_rapport = mode
        self.mode_rapport = mode
# Alias de compatibilite avec l'ancien code
Constat = ConstatControle
AuditInfo = AuditMeta
InstallationGenerale = Installation
