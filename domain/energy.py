"""OPT'HELIOS — Calculs énergétiques solaire thermique / ECS.

Module métier autonome fournissant :

- les modèles d'entrée (`EnergyInputs`) et de sortie (`EnergyResults`) ;
- des fonctions de calcul pures et testables (énergie ECS annuelle, productivité
  solaire, taux de couverture, ratio stockage L/m², proposition qualitative de
  redimensionnement) ;
- un point d'entrée unique `compute_energy(inputs)` qui regroupe l'ensemble.

Les calculs reposent sur des ordres de grandeur standards de l'audit solaire
thermique collectif. Ils ont vocation à servir d'**aide à la décision** dans
l'interface et dans le rapport — non à se substituer à une étude thermique
détaillée. Les conventions principales :

* énergie ECS annuelle :
    E_ECS [kWh/an] = rho * cp * V_jour * delta_T * jours_an / 3600
    avec rho = 1 kg/L, cp = 4,186 kJ/(kg·K).

* productivité solaire :
    productivite [kWh/m².an] = E_solaire_utile [kWh/an] / surface [m²]

* taux de couverture solaire :
    f_solaire = E_solaire_utile / E_ECS

* ratio stockage solaire :
    ratio [L/m²] = volume_stockage_litres / surface_capteurs_m²

Les valeurs par défaut sont volontairement conservatrices ; elles peuvent être
ajustées via `EnergyInputs` sans modifier l'API publique.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# Densité de l'eau (kg/L) et capacité thermique massique (kJ/kg/K) — valeurs standards.
RHO_EAU_KG_L: float = 1.0
CP_EAU_KJ_KG_K: float = 4.186
SECONDES_PAR_HEURE: int = 3600
JOURS_PAR_AN: int = 365

# Productible solaire indicatif (kWh/m².an) selon zone climatique.
# Ordres de grandeur OPT'HELIOS pour ECS collectif en France métropolitaine.
PRODUCTIBLE_INDICATIF_ZONES: dict[str, float] = {
    "H1": 350.0,
    "H2": 450.0,
    "H3": 550.0,
}
PRODUCTIBLE_INDICATIF_DEFAUT: float = 450.0

# Bornes qualitatives utilisées pour le ratio stockage L/m² (recommandation
# usuelle ADEME / SOCOL pour ECS solaire collectif : 50 à 100 L/m²).
RATIO_STOCKAGE_MIN_LM2: float = 50.0
RATIO_STOCKAGE_MAX_LM2: float = 100.0

# Bornes qualitatives pour le taux de couverture solaire ECS collectif
# (cibles 30 à 60 % usuelles ; au-delà, risque de surchauffe estivale).
COUVERTURE_MIN: float = 0.30
COUVERTURE_MAX: float = 0.60


class EnergyInputs(BaseModel):
    """Données d'entrée du calcul énergétique.

    Tous les champs sont optionnels — les fonctions renvoient ``None`` pour les
    grandeurs qu'elles ne peuvent pas calculer faute de donnée. Cela permet
    d'intégrer le module dans une UI où l'utilisateur saisit progressivement.
    Les bornes Pydantic restent volontairement larges pour ne pas rejeter une
    saisie en cours, tout en interceptant les valeurs aberrantes (négatives,
    rendement > 1, deltaT > 100 K, jours hors plage annuelle).
    """

    volume_ecs_jour_litres: Optional[float] = Field(
        default=None,
        ge=0,
        description="Volume d'eau chaude sanitaire consommé en moyenne par jour (L/jour).",
    )
    delta_t_kelvin: Optional[float] = Field(
        default=40.0,
        ge=0,
        le=100,
        description="Écart de température eau froide → eau chaude (K, 0..100).",
    )
    jours_fonctionnement: int = Field(
        default=JOURS_PAR_AN,
        ge=0,
        le=366,
        description="Nombre de jours de fonctionnement effectif sur l'année (0..366).",
    )

    surface_capteurs_m2: Optional[float] = Field(
        default=None,
        ge=0,
        description="Surface utile du champ capteurs (m²).",
    )
    volume_stockage_solaire_litres: Optional[float] = Field(
        default=None,
        ge=0,
        description="Volume total du stockage solaire (L).",
    )

    productible_indicatif_kwh_m2_an: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Productible solaire indicatif retenu (kWh/m².an). Si absent, "
            "il est dérivé de la zone climatique ou de la valeur par défaut."
        ),
    )
    zone_climatique: Optional[str] = Field(
        default=None,
        description="Zone climatique RT/RE (H1, H2, H3) si connue.",
    )

    rendement_utile: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description=(
            "Rendement utile global appliqué au productible théorique pour "
            "passer en énergie effectivement valorisée côté ECS (pertes "
            "primaires, échangeur, distribution). Doit être compris entre 0 et 1."
        ),
    )

    model_config = {"extra": "ignore"}


class EnergyResults(BaseModel):
    """Résultats agrégés des calculs énergétiques."""

    energie_ecs_kwh_an: Optional[float] = None
    productible_retenu_kwh_m2_an: Optional[float] = None
    energie_solaire_utile_kwh_an: Optional[float] = None
    productivite_kwh_m2_an: Optional[float] = None
    taux_couverture: Optional[float] = None
    ratio_stockage_l_m2: Optional[float] = None
    proposition_redimensionnement: str = ""
    messages: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# Fonctions de calcul unitaires
# ---------------------------------------------------------------------------


def energie_ecs_annuelle_kwh(
    volume_jour_litres: Optional[float],
    delta_t_kelvin: Optional[float],
    jours: int = JOURS_PAR_AN,
) -> Optional[float]:
    """Énergie thermique nécessaire pour produire l'ECS sur l'année.

    Formule : E = rho * cp * V_jour * delta_T * jours / 3600 (en kWh).
    """

    if volume_jour_litres is None or delta_t_kelvin is None:
        return None
    if volume_jour_litres <= 0 or delta_t_kelvin <= 0 or jours <= 0:
        return 0.0

    kj = RHO_EAU_KG_L * CP_EAU_KJ_KG_K * volume_jour_litres * delta_t_kelvin * jours
    return round(kj / SECONDES_PAR_HEURE, 1)


def productible_retenu_kwh_m2_an(
    productible_indicatif: Optional[float],
    zone_climatique: Optional[str],
) -> float:
    """Productible solaire indicatif à utiliser (kWh/m².an)."""

    if productible_indicatif is not None and productible_indicatif > 0:
        return float(productible_indicatif)
    if zone_climatique:
        return PRODUCTIBLE_INDICATIF_ZONES.get(
            zone_climatique.strip().upper(),
            PRODUCTIBLE_INDICATIF_DEFAUT,
        )
    return PRODUCTIBLE_INDICATIF_DEFAUT


def productivite_kwh_m2_an(
    energie_solaire_utile: Optional[float],
    surface_m2: Optional[float],
) -> Optional[float]:
    """Productivité spécifique (kWh utiles / m² de capteurs / an)."""

    if energie_solaire_utile is None or surface_m2 is None or surface_m2 <= 0:
        return None
    return round(energie_solaire_utile / surface_m2, 1)


def taux_couverture(
    energie_solaire_utile: Optional[float],
    energie_ecs: Optional[float],
) -> Optional[float]:
    """Fraction de l'énergie ECS couverte par le solaire (0 à 1)."""

    if energie_solaire_utile is None or energie_ecs is None or energie_ecs <= 0:
        return None
    return round(energie_solaire_utile / energie_ecs, 3)


def ratio_stockage_l_m2(
    volume_stockage_litres: Optional[float],
    surface_m2: Optional[float],
) -> Optional[float]:
    """Ratio volume de stockage solaire / surface capteurs (L/m²)."""

    if volume_stockage_litres is None or surface_m2 is None or surface_m2 <= 0:
        return None
    return round(volume_stockage_litres / surface_m2, 1)


def evaluer_redimensionnement(
    couverture: Optional[float],
    ratio_stockage: Optional[float],
) -> tuple[str, list[str]]:
    """Émet une proposition qualitative de redimensionnement.

    Retourne un libellé court (« surdimensionné », « équilibré », ...) et la
    liste des messages détaillés justifiant la proposition.
    """

    messages: list[str] = []
    label = "indeterminé"

    if couverture is None:
        messages.append(
            "Taux de couverture solaire non calculable faute de données ECS suffisantes."
        )
    else:
        if couverture > 1.0:
            label = "incoherent"
            messages.append(
                f"Taux de couverture estimé à {couverture * 100:.0f} % "
                "(> 100 %) — vérifier la saisie (volume ECS / ΔT / surface) ou "
                "le dimensionnement : l'énergie solaire utile ne peut pas "
                "dépasser le besoin ECS annuel."
            )
        elif couverture > COUVERTURE_MAX:
            label = "surdimensionné"
            messages.append(
                f"Taux de couverture estimé à {couverture * 100:.0f} % "
                f"(> {COUVERTURE_MAX * 100:.0f} %) : risque de surchauffe estivale, "
                "envisager une réduction du champ ou un bridage de rangées."
            )
        elif couverture < COUVERTURE_MIN:
            label = "sous-dimensionné"
            messages.append(
                f"Taux de couverture estimé à {couverture * 100:.0f} % "
                f"(< {COUVERTURE_MIN * 100:.0f} %) : marge d'extension possible "
                "si le besoin ECS est confirmé."
            )
        else:
            label = "équilibré"
            messages.append(
                f"Taux de couverture estimé à {couverture * 100:.0f} % : "
                "dimensionnement cohérent avec les cibles usuelles ECS collectif."
            )

    if ratio_stockage is None:
        messages.append(
            "Ratio stockage solaire / surface capteurs non calculable "
            "(volume ou surface manquant)."
        )
    else:
        if ratio_stockage < RATIO_STOCKAGE_MIN_LM2:
            messages.append(
                f"Ratio stockage de {ratio_stockage:.0f} L/m² "
                f"(< {RATIO_STOCKAGE_MIN_LM2:.0f}) : stockage probablement trop faible, "
                "risque de surchauffe et de perte de productible."
            )
            if label == "équilibré":
                label = "stockage à augmenter"
        elif ratio_stockage > RATIO_STOCKAGE_MAX_LM2:
            messages.append(
                f"Ratio stockage de {ratio_stockage:.0f} L/m² "
                f"(> {RATIO_STOCKAGE_MAX_LM2:.0f}) : stockage probablement surdimensionné, "
                "pertes statiques potentiellement élevées."
            )
            if label == "équilibré":
                label = "stockage à réduire"
        else:
            messages.append(
                f"Ratio stockage de {ratio_stockage:.0f} L/m² : "
                f"conforme aux bornes usuelles ({RATIO_STOCKAGE_MIN_LM2:.0f}-"
                f"{RATIO_STOCKAGE_MAX_LM2:.0f} L/m²)."
            )

    return label, messages


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def compute_energy(inputs: EnergyInputs) -> EnergyResults:
    """Calcule l'ensemble des indicateurs énergétiques à partir des entrées."""

    energie_ecs = energie_ecs_annuelle_kwh(
        inputs.volume_ecs_jour_litres,
        inputs.delta_t_kelvin,
        inputs.jours_fonctionnement,
    )

    productible = productible_retenu_kwh_m2_an(
        inputs.productible_indicatif_kwh_m2_an,
        inputs.zone_climatique,
    )

    energie_solaire_utile: Optional[float] = None
    if inputs.surface_capteurs_m2 is not None and inputs.surface_capteurs_m2 > 0:
        brute = productible * inputs.surface_capteurs_m2
        energie_solaire_utile = round(brute * inputs.rendement_utile, 1)

    productivite = productivite_kwh_m2_an(
        energie_solaire_utile,
        inputs.surface_capteurs_m2,
    )

    couverture = taux_couverture(energie_solaire_utile, energie_ecs)

    ratio = ratio_stockage_l_m2(
        inputs.volume_stockage_solaire_litres,
        inputs.surface_capteurs_m2,
    )

    proposition, messages = evaluer_redimensionnement(couverture, ratio)

    return EnergyResults(
        energie_ecs_kwh_an=energie_ecs,
        productible_retenu_kwh_m2_an=round(productible, 1),
        energie_solaire_utile_kwh_an=energie_solaire_utile,
        productivite_kwh_m2_an=productivite,
        taux_couverture=couverture,
        ratio_stockage_l_m2=ratio,
        proposition_redimensionnement=proposition,
        messages=messages,
    )


def inputs_have_payload(inputs: Optional[EnergyInputs]) -> bool:
    """True si au moins une grandeur saisissable est renseignée non triviale.

    Utilisé par les exports DOCX / Markdown pour décider s'il faut auto-calculer
    `results` quand l'utilisateur a saisi des entrées mais n'a pas explicitement
    déclenché le calcul depuis l'UI.
    """
    if inputs is None:
        return False
    return any(
        v is not None and v > 0
        for v in (
            inputs.volume_ecs_jour_litres,
            inputs.surface_capteurs_m2,
            inputs.volume_stockage_solaire_litres,
            inputs.productible_indicatif_kwh_m2_an,
        )
    )


def format_results_markdown(results: EnergyResults) -> list[str]:
    """Sérialise les résultats en lignes Markdown pour les exports."""

    def _fmt(value: Optional[float], unit: str = "") -> str:
        if value is None:
            return "non calculé"
        return f"{value:,.1f}{(' ' + unit) if unit else ''}".replace(",", " ")

    lines = [
        "",
        "## Calculs énergétiques",
        f"- Énergie ECS annuelle : {_fmt(results.energie_ecs_kwh_an, 'kWh/an')}",
        f"- Productible solaire retenu : {_fmt(results.productible_retenu_kwh_m2_an, 'kWh/m².an')}",
        f"- Énergie solaire utile estimée : {_fmt(results.energie_solaire_utile_kwh_an, 'kWh/an')}",
        f"- Productivité spécifique : {_fmt(results.productivite_kwh_m2_an, 'kWh/m².an')}",
    ]
    if results.taux_couverture is not None:
        if results.taux_couverture > 1.0:
            lines.append(
                f"- Taux de couverture solaire : {results.taux_couverture * 100:.0f} % "
                "— **> 100 %, vérifier la saisie ou le dimensionnement**"
            )
        else:
            lines.append(f"- Taux de couverture solaire : {results.taux_couverture * 100:.0f} %")
    else:
        lines.append("- Taux de couverture solaire : non calculé")
    if results.ratio_stockage_l_m2 is not None:
        lines.append(f"- Ratio stockage : {results.ratio_stockage_l_m2:.0f} L/m²")
    else:
        lines.append("- Ratio stockage : non calculé")
    lines.append(
        f"- Proposition de redimensionnement : **{results.proposition_redimensionnement}**"
    )
    if results.messages:
        lines.append("")
        lines.append("### Commentaires")
        for msg in results.messages:
            lines.append(f"- {msg}")
    return lines
