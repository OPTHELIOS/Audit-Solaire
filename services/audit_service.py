from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from domain.models import Audit, AuditMeta, StatutAudit, SyntheseAudit


def create_empty_audit() -> Audit:
    audit = Audit()
    audit.meta.updated_at = datetime.now()
    return audit


def touch_audit(audit: Audit) -> Audit:
    audit.meta.updated_at = datetime.now()
    return audit


def duplicate_audit(source: Audit) -> Audit:
    """Cree un nouvel audit a partir d'un audit existant, pour gagner du
    temps sur un site similaire (meme type d'installation).

    Ce qui est REPRIS : la description technique de l'installation
    (`installation`), ainsi que le maitre d'ouvrage/exploitant/mainteneur
    (souvent identiques sur un parc de batiments comparables).

    Ce qui est REMIS A ZERO (specifique a CE site-la, pas au "modele") :
    l'identite du dossier (nouvel `audit_id`, nouveau `numero_audit`,
    `dossier_cloud` non calcule — sera recalcule a partir du nouveau nom
    d'operation au premier envoi cloud), le statut (brouillon), l'adresse et
    le contact sur site, les constats de controle (l'etat physique constate
    est propre a chaque site, on ne duplique pas de faux verdicts), les
    preuves (photos specifiques au site source) et la synthese/etude Studio.
    """
    new_audit = Audit()

    new_audit.meta = AuditMeta(
        audit_id=str(uuid4()),
        numero_audit=f"AUD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        statut=StatutAudit.brouillon,
        date_audit=date.today(),
        auditeur=source.meta.auditeur,
        dossier_cloud=None,
    )

    new_audit.projet.maitre_ouvrage = source.projet.maitre_ouvrage
    new_audit.projet.exploitant = source.projet.exploitant
    new_audit.projet.mainteneur = source.projet.mainteneur
    # Nom d'operation repris comme point de depart (a renommer par
    # l'auditeur pour le nouveau site) ; adresse et contact volontairement
    # NON repris car specifiques au site source.
    if source.projet.operation:
        new_audit.projet.operation = f"{source.projet.operation} (copie)"

    new_audit.installation = source.installation.model_copy(deep=True)

    new_audit.constats = []
    new_audit.preuves = []
    new_audit.synthese = SyntheseAudit()

    return new_audit


def reset_audit() -> Audit:
    return create_empty_audit()


def audit_to_dict(audit: Audit) -> dict:
    return audit.model_dump()


def load_audit_from_dict(data: dict) -> Audit:
    return Audit(**data)
