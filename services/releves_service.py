"""Gestion des relevés de mesure (température, pression, débit...) pris sur
site pendant l'audit. Voir `domain/models.py::ReleveMesure` pour le modèle
et `domain/releves_catalog.py` pour les modèles usuels proposés dans le
formulaire d'ajout."""

from __future__ import annotations

from domain.models import Audit, ReleveMesure, TypeMesure


def add_releve(
    audit: Audit,
    *,
    libelle: str,
    valeur: float,
    unite: str = "",
    type_mesure: TypeMesure | str = TypeMesure.autre,
    controle_id: str | None = None,
    section: str | None = None,
    commentaire: str | None = None,
) -> ReleveMesure:
    releve = ReleveMesure(
        type_mesure=TypeMesure(type_mesure) if isinstance(type_mesure, str) else type_mesure,
        libelle=libelle,
        valeur=valeur,
        unite=unite,
        controle_id=controle_id or None,
        section=section or None,
        commentaire=commentaire or None,
    )
    audit.releves.append(releve)
    return releve


def remove_releve(audit: Audit, releve_id: str) -> bool:
    before = len(audit.releves)
    audit.releves = [r for r in audit.releves if r.releve_id != releve_id]
    return len(audit.releves) < before


def list_releves_sorted(audit: Audit) -> list[ReleveMesure]:
    return sorted(audit.releves, key=lambda r: r.date_mesure, reverse=True)
