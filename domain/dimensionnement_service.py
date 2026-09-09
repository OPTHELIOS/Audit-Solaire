"""Contrôles de cohérence de dimensionnement solaire thermique, basés sur les
ratios officiels de la "Fiche technique SOCOL 2021 — Ratios des besoins en
eau chaude sanitaire pour le dimensionnement des installations en solaire
thermique collectif" (ADEME, Alliance Soleil, EnButinantl'Energie, GRDF,
INES, Tecsol — www.solaire-collectif.fr).

Ces ratios sont documentés comme des valeurs de PRÉDIMENSIONNEMENT ("valeurs
indicatives par défaut, à affiner"), pas des seuils réglementaires stricts :
les fonctions ci-dessous renvoient donc un statut informatif (conforme à la
fourchette / hors fourchette), jamais un verdict de non-conformité au sens
des contrôles du catalogue d'audit (`domain/control_catalog.py`). Utile
notamment en audit d'existant, quand la note de dimensionnement d'origine
(étude SOLO2018 ou équivalent) n'a pas été retrouvée : on peut alors vérifier
que l'installation observée reste dans des ordres de grandeur plausibles.

Voir `domain/models.py::DimensionnementSolaire` pour les champs de saisie et
`domain/performance_service.py` pour les indicateurs de performance mesurée
(FSAV/Prod/Taux) et la comparaison réel/théorique.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ratio Vmin_mensuel / S_estimée (L/m²) par zone géographique — fiche SOCOL
# 2021, §4, tableau "Situation géographique". Le partage nord/centre/sud
# n'est pas un découpage administratif strict : c'est le partage utilisé tel
# quel par SOCOL (approximativement 1/3 nord, 1/3 centre, 1/3 sud de la
# France métropolitaine).
RATIOS_BESOINS_ZONE_L_PAR_M2: dict[str, tuple[float, float]] = {
    "nord": (40.0, 45.0),
    "centre": (50.0, 75.0),
    "sud": (70.0, 100.0),
}

ZONE_LABELS: dict[str, str] = {
    "nord": "1/3 nord de la France",
    "centre": "1/3 centre de la France",
    "sud": "1/3 sud de la France",
}

# Ratio de volume de stockage (L/m² de capteurs), fiche SOCOL 2021 §2 :
# "75 à 100 l/m²" en stockage sanitaire classique ; §REF3 (eau technique) :
# 50 l/m² minimum. Voir domain/socol_reference.py pour le lien avec le
# schéma de référence.
RATIO_STOCKAGE_SANITAIRE_L_PAR_M2: tuple[float, float] = (75.0, 100.0)
RATIO_STOCKAGE_EAU_TECHNIQUE_MIN_L_PAR_M2: float = 50.0

# Taux de couverture solaire utile optimal sur le(s) mois critique(s)
# (généralement l'été) — fiche SOCOL 2021 §4 : "un taux de couverture solaire
# utile est optimisé lorsqu'il atteint 85 à 90 % pour le ou les mois
# critiques".
TAUX_COUVERTURE_OPTIMAL_PCT: tuple[float, float] = (85.0, 90.0)


@dataclass(frozen=True)
class RatioCheckResult:
    label: str
    valeur: float | None
    plage_recommandee: tuple[float, float] | None
    dans_la_plage: bool | None
    commentaire: str


def check_volume_stockage(
    volume_stockage_litres: float | None,
    surface_capteurs_m2: float | None,
    type_stockage: str | None,
) -> RatioCheckResult:
    """Compare le volume de stockage réellement installé (relevé en page
    "Installation") à la fourchette recommandée par la fiche SOCOL 2021, en
    fonction de la surface de capteurs et du type de stockage (sanitaire ou
    eau technique, voir `domain/models.py::ClassificationInstallation`)."""
    if not volume_stockage_litres or not surface_capteurs_m2:
        return RatioCheckResult(
            label="Volume de stockage / surface de capteurs",
            valeur=None,
            plage_recommandee=None,
            dans_la_plage=None,
            commentaire="Volume de stockage ou surface de capteurs non renseigné(e).",
        )

    ratio = round(volume_stockage_litres / surface_capteurs_m2, 1)

    if type_stockage == "eau_technique":
        borne_min = RATIO_STOCKAGE_EAU_TECHNIQUE_MIN_L_PAR_M2
        dans_la_plage = ratio >= borne_min
        commentaire = (
            f"Ratio observé {ratio} l/m² (stockage eau technique, minimum SOCOL "
            f"recommandé {borne_min:.0f} l/m²)."
        )
        return RatioCheckResult(
            label="Volume de stockage / surface de capteurs",
            valeur=ratio,
            plage_recommandee=(borne_min, borne_min),
            dans_la_plage=dans_la_plage,
            commentaire=commentaire,
        )

    borne_min, borne_max = RATIO_STOCKAGE_SANITAIRE_L_PAR_M2
    dans_la_plage = borne_min <= ratio <= borne_max
    commentaire = (
        f"Ratio observé {ratio} l/m² (fourchette SOCOL recommandée "
        f"{borne_min:.0f}-{borne_max:.0f} l/m² en stockage sanitaire classique)."
    )
    return RatioCheckResult(
        label="Volume de stockage / surface de capteurs",
        valeur=ratio,
        plage_recommandee=(borne_min, borne_max),
        dans_la_plage=dans_la_plage,
        commentaire=commentaire,
    )


def check_surface_vs_besoins(
    surface_capteurs_m2: float | None,
    besoins_ecs_l_jour: float | None,
    zone_climatique: str | None,
) -> RatioCheckResult:
    """Compare la surface de capteurs installée aux besoins ECS journaliers
    déclarés, via le ratio Vmin_mensuel/S_estimée de la fiche SOCOL 2021 —
    un pré-dimensionnement de contrôle, PAS un remplacement d'une étude
    SOLO2018 complète (qui seule tient compte de l'ensoleillement réel du
    site, de l'inclinaison, de l'orientation...)."""
    zone = (zone_climatique or "").strip().lower()
    plage = RATIOS_BESOINS_ZONE_L_PAR_M2.get(zone)

    if not surface_capteurs_m2 or not besoins_ecs_l_jour or plage is None:
        return RatioCheckResult(
            label="Surface de capteurs / besoins ECS (ratio SOCOL)",
            valeur=None,
            plage_recommandee=plage,
            dans_la_plage=None,
            commentaire=(
                "Surface de capteurs, besoins ECS journaliers ou zone climatique "
                "non renseignés — pré-dimensionnement de contrôle non calculable."
            ),
        )

    ratio = round(besoins_ecs_l_jour / surface_capteurs_m2, 1)
    borne_min, borne_max = plage
    dans_la_plage = borne_min <= ratio <= borne_max
    zone_label = ZONE_LABELS.get(zone, zone)
    commentaire = (
        f"Ratio besoins/surface observé {ratio} l/m² (fourchette SOCOL {zone_label} : "
        f"{borne_min:.0f}-{borne_max:.0f} l/m²). Pré-dimensionnement de contrôle uniquement — "
        f"ne remplace pas une étude SOLO2018 tenant compte de l'ensoleillement réel du site."
    )
    return RatioCheckResult(
        label="Surface de capteurs / besoins ECS (ratio SOCOL)",
        valeur=ratio,
        plage_recommandee=plage,
        dans_la_plage=dans_la_plage,
        commentaire=commentaire,
    )
