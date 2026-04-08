from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from domain.control_catalog import CONTROL_CATALOG
from domain.models import Audit, ConstatControle, ControleCatalogueItem, Installation


def is_applicable(control: ControleCatalogueItem, installation: Installation) -> bool:
    classification = getattr(installation, "classification", None)
    if classification is None:
        return True

    cond = control.condition_applicabilite or {}

    systeme = classification.systeme_capteurs
    echangeur = classification.type_echangeur
    comptages = set(classification.type_comptage or [])

    if "systeme_capteurs_in" in cond and systeme not in cond["systeme_capteurs_in"]:
        return False

    if "systeme_capteurs_not_in" in cond and systeme in cond["systeme_capteurs_not_in"]:
        return False

    if "type_echangeur_in" in cond and echangeur not in cond["type_echangeur_in"]:
        return False

    if "type_echangeur_not_in" in cond and echangeur in cond["type_echangeur_not_in"]:
        return False

    if "type_comptage_any_in" in cond and not comptages.intersection(set(cond["type_comptage_any_in"])):
        return False

    return True


def get_applicable_controls(audit: Audit) -> List[ControleCatalogueItem]:
    return [control for control in CONTROL_CATALOG if is_applicable(control, audit.installation)]


def group_controls_by_section(audit: Audit) -> Dict[str, List[ControleCatalogueItem]]:
    grouped = defaultdict(list)

    for item in get_applicable_controls(audit):
        grouped[item.section].append(item)

    return dict(grouped)


def index_constats(audit: Audit) -> Dict[str, ConstatControle]:
    return {constat.controle_id: constat for constat in audit.constats}


def get_constat(audit: Audit, controle_id: str) -> ConstatControle | None:
    return index_constats(audit).get(controle_id)


def get_or_create_constat(audit: Audit, item: ControleCatalogueItem) -> ConstatControle:
    existing = get_constat(audit, item.controle_id)
    if existing is not None:
        return existing

    constat = ConstatControle(
        controle_id=item.controle_id,
        section=item.section,
        libelle=item.libelle,
        criticite=item.criticite_par_defaut,
        recommandation=item.recommandation_type,
    )
    audit.constats.append(constat)
    return constat


def remove_non_applicable_constats(audit: Audit) -> None:
    applicable_ids = {item.controle_id for item in get_applicable_controls(audit)}
    audit.constats = [constat for constat in audit.constats if constat.controle_id in applicable_ids]