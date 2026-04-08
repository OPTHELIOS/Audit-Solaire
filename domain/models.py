from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class TypePreuve(str, Enum):
    photo = "photo"
    document = "document"
    mesure = "mesure"
    schema = "schema"
    autre = "autre"


class AuditMeta(BaseModel):
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
    preuve_id: str = Field(default_factory=lambda: f"PRV-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}")
    type_preuve: TypePreuve = TypePreuve.photo
    nom_fichier: Optional[str] = None
    chemin_fichier: Optional[str] = None
    section: Optional[str] = None
    controle_id: Optional[str] = None
    legende: Optional[str] = None
    commentaire: Optional[str] = None
    date_ajout: datetime = Field(default_factory=datetime.now)


class ConstatControle(BaseModel):
    controle_id: str
    section: str
    libelle: str
    verdict: VerdictControle = VerdictControle.non_verifiable
    criticite: Criticite = Criticite.mineure
    observation: Optional[str] = None
    preuve_ids: list[str] = Field(default_factory=list)
    recommandation: Optional[str] = None


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
    synthese: SyntheseAudit = Field(default_factory=SyntheseAudit)
# Alias de compatibilité avec l'ancien code
Constat = ConstatControle
AuditInfo = AuditMeta
InstallationGenerale = Installation