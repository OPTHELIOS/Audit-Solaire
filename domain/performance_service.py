"""Indicateurs de performance solaire normalisés SOCOL (FSAV, Prod, Taux) et
comparaison réel/théorique — pendant, côté audit d'existant, de la fonction
"ratio réel/théorique coloré" qu'un outil comme THMès (INES) affiche pour la
mise en service.

Sources des formules (Livret technique SOCOL — Systèmes Solaires Combinés
pour les bâtiments collectifs, éd. 2023, chapitre "Indicateurs de
performance", et fiche ratios SOCOL 2021) :

- FSAV (taux d'économie d'énergie d'appoint, au sens ISO 9488) :
  FSAV = QSTU / (QApp + QSTU)
- Prod (productivité surfacique, kWh/m².an), utilisée par l'ADEME comme
  critère d'éligibilité Fonds Chaleur (seuils variables selon zone
  climatique, non repris ici).
- Taux (part des auxiliaires électriques dans la production utile) :
  Taux = conso_aux_electriques / QSTU. Le livret SOCOL indique que "pour des
  systèmes efficaces, Taux doit être inférieur à 1,5 %" ; les bornes
  intermédiaires (orange/rouge) ci-dessous sont un choix OPT'HELIOS, pas une
  valeur SOCOL — voir le commentaire de `evaluate_taux_auxiliaires`.

Ces indicateurs nécessitent des totaux ÉNERGÉTIQUES SUR UNE PÉRIODE (pas des
valeurs instantanées) : voir `domain/releves_catalog.py::LIBELLE_*` pour les
libellés de relevé attendus, à renseigner depuis la supervision/télégestion
quand elle existe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.opthelios_style import STATUS_BLUE, STATUS_GRAY, STATUS_GREEN, STATUS_ORANGE, STATUS_RED, STATUS_YELLOW
from domain.releves_catalog import (
    LIBELLE_CONSO_ELEC_AUX_PERIODE,
    LIBELLE_ENERGIE_APPOINT_PERIODE,
    LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
)


@dataclass(frozen=True)
class IndicateurStatut:
    valeur: float | None
    label: str
    couleur: str
    commentaire: str


def _latest_valeur_by_libelle(releves: list[Any], libelle: str) -> float | None:
    """Dernier relevé (le plus récent) correspondant exactement à `libelle`,
    parmi `audit.releves` (liste de `domain.models.ReleveMesure`)."""
    matches = [r for r in releves if getattr(r, "libelle", None) == libelle]
    if not matches:
        return None
    latest = max(matches, key=lambda r: getattr(r, "date_mesure"))
    return float(latest.valeur)


def extract_energy_releves(releves: list[Any]) -> dict[str, float | None]:
    return {
        "qstu_kwh": _latest_valeur_by_libelle(releves, LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE),
        "qapp_kwh": _latest_valeur_by_libelle(releves, LIBELLE_ENERGIE_APPOINT_PERIODE),
        "conso_aux_kwh": _latest_valeur_by_libelle(releves, LIBELLE_CONSO_ELEC_AUX_PERIODE),
    }


def compute_fsav(qstu_kwh: float | None, qapp_kwh: float | None) -> float | None:
    if qstu_kwh is None or qapp_kwh is None:
        return None
    denom = qstu_kwh + qapp_kwh
    if denom <= 0:
        return None
    return round(100 * qstu_kwh / denom, 1)


def compute_productivite(qstu_kwh: float | None, surface_capteurs_m2: float | None) -> float | None:
    if qstu_kwh is None or not surface_capteurs_m2:
        return None
    return round(qstu_kwh / surface_capteurs_m2, 1)


def compute_taux_auxiliaires(conso_aux_kwh: float | None, qstu_kwh: float | None) -> float | None:
    if conso_aux_kwh is None or not qstu_kwh:
        return None
    return round(100 * conso_aux_kwh / qstu_kwh, 2)


def evaluate_taux_auxiliaires(taux_pct: float | None) -> IndicateurStatut:
    """Le livret SOCOL ne donne qu'un seuil unique ("doit être inférieur à
    1,5 % pour un système efficace") : les bornes 1,5-3 %/>3 % ci-dessous
    sont une échelle OPT'HELIOS ajoutée pour graduer l'alerte, pas une valeur
    SOCOL — à mentionner tel quel si le rapport est discuté avec un tiers."""
    if taux_pct is None:
        return IndicateurStatut(None, "Non calculable", STATUS_GRAY, "Relevés insuffisants pour calculer Taux.")
    if taux_pct < 1.5:
        return IndicateurStatut(taux_pct, f"{taux_pct} %", STATUS_GREEN, "Conforme au seuil SOCOL (< 1,5 % pour un système efficace).")
    if taux_pct < 3.0:
        return IndicateurStatut(taux_pct, f"{taux_pct} %", STATUS_ORANGE, "Au-delà du seuil SOCOL de 1,5 % — auxiliaires électriques à examiner.")
    return IndicateurStatut(taux_pct, f"{taux_pct} %", STATUS_RED, "Largement au-delà du seuil SOCOL — surconsommation probable des auxiliaires.")


# Bornes du ratio réel/théorique (production réelle / production attendue,
# ou taux de couverture réel / visé) — échelle OPT'HELIOS inspirée des
# pratiques usuelles de suivi de performance (M&V) solaire, pas une valeur
# SOCOL normée : à formuler comme telle dans le rapport.
def evaluate_ratio_reel_theorique(valeur_reelle: float | None, valeur_theorique: float | None, label: str) -> IndicateurStatut:
    if valeur_reelle is None or not valeur_theorique:
        return IndicateurStatut(None, "Non calculable", STATUS_GRAY, f"{label} : donnée réelle ou théorique manquante.")

    ratio = round(valeur_reelle / valeur_theorique, 2)
    pct = round(ratio * 100)

    if ratio >= 0.9:
        return IndicateurStatut(ratio, f"{pct} %", STATUS_GREEN, f"{label} conforme aux attentes ({pct} % du théorique).")
    if ratio >= 0.75:
        return IndicateurStatut(ratio, f"{pct} %", STATUS_YELLOW, f"{label} légèrement sous-performant ({pct} % du théorique).")
    if ratio >= 0.5:
        return IndicateurStatut(ratio, f"{pct} %", STATUS_ORANGE, f"{label} en sous-performance significative ({pct} % du théorique).")
    return IndicateurStatut(ratio, f"{pct} %", STATUS_RED, f"{label} en sous-performance majeure ({pct} % du théorique).")


def compute_performance_indicators(audit: Any) -> dict[str, Any]:
    """Calcule les 3 indicateurs SOCOL + la comparaison réel/théorique de
    productivité, à partir de `audit.releves` et `audit.installation`
    (surface de capteurs, dimensionnement). Ne lève jamais d'exception :
    retourne des indicateurs "non calculable" si les données manquent."""
    releves = list(getattr(audit, "releves", []) or [])
    energies = extract_energy_releves(releves)

    installation = getattr(audit, "installation", None)
    champ_capteurs = getattr(installation, "champ_capteurs", None) if installation else None
    surface_m2 = getattr(champ_capteurs, "surface_totale_m2", None) if champ_capteurs else None

    dimensionnement = getattr(installation, "dimensionnement", None) if installation else None
    productible_theorique = getattr(dimensionnement, "productible_theorique_kwh_m2_an", None) if dimensionnement else None
    taux_couverture_vise = getattr(dimensionnement, "taux_couverture_vise_pct", None) if dimensionnement else None

    fsav = compute_fsav(energies["qstu_kwh"], energies["qapp_kwh"])
    prod = compute_productivite(energies["qstu_kwh"], surface_m2)
    taux = compute_taux_auxiliaires(energies["conso_aux_kwh"], energies["qstu_kwh"])

    taux_statut = evaluate_taux_auxiliaires(taux)
    prod_statut = evaluate_ratio_reel_theorique(prod, productible_theorique, "Productivité (Prod)")
    fsav_statut = evaluate_ratio_reel_theorique(fsav, taux_couverture_vise, "Taux de couverture (FSAV)")

    return {
        "qstu_kwh": energies["qstu_kwh"],
        "qapp_kwh": energies["qapp_kwh"],
        "conso_aux_kwh": energies["conso_aux_kwh"],
        "surface_capteurs_m2": surface_m2,
        "productible_theorique_kwh_m2_an": productible_theorique,
        "taux_couverture_vise_pct": taux_couverture_vise,
        "fsav_pct": fsav,
        "prod_kwh_m2_an": prod,
        "taux_aux_pct": taux,
        "fsav_statut": fsav_statut,
        "prod_statut": prod_statut,
        "taux_statut": taux_statut,
    }
