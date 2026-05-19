"""Panneau Streamlit de saisie des calculs énergétiques ECS / productivité.

Module isolé pour pouvoir être intégré dans la page Installation (ou Synthèse)
sans dupliquer la logique de calcul. Toutes les saisies écrivent dans le bloc
`audit.energy` du modèle Pydantic, puis `compute_energy` recalcule les
résultats. Les bornes Pydantic d'`EnergyInputs` garantissent que les saisies
restent physiquement plausibles.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from domain.energy import (
    PRODUCTIBLE_INDICATIF_DEFAUT,
    EnergyInputs,
    compute_energy,
)
from domain.models import EnergyBlock
from services.audit_service import touch_audit
from ui.state import get_audit, save_audit

_ZONES = ["", "H1", "H2", "H3"]


def _get_energy_block() -> EnergyBlock:
    audit = get_audit()
    if not hasattr(audit, "energy") or audit.energy is None:
        audit.energy = EnergyBlock()
        save_audit(audit)
    return audit.energy


def _none_if_zero(value: float) -> Optional[float]:
    return value if value > 0 else None


def _init_state(block: EnergyBlock) -> None:
    inputs = block.inputs
    defaults = {
        "energy_volume_ecs_jour": float(inputs.volume_ecs_jour_litres or 0.0),
        "energy_delta_t": float(inputs.delta_t_kelvin or 40.0),
        "energy_jours": int(inputs.jours_fonctionnement or 365),
        "energy_surface_capteurs": float(inputs.surface_capteurs_m2 or 0.0),
        "energy_volume_stockage": float(inputs.volume_stockage_solaire_litres or 0.0),
        "energy_productible_indicatif": float(inputs.productible_indicatif_kwh_m2_an or 0.0),
        "energy_zone": (inputs.zone_climatique or "") if (inputs.zone_climatique or "") in _ZONES else "",
        "energy_rendement_utile": float(inputs.rendement_utile if inputs.rendement_utile is not None else 0.9),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _build_inputs_from_state() -> EnergyInputs:
    return EnergyInputs(
        volume_ecs_jour_litres=_none_if_zero(float(st.session_state["energy_volume_ecs_jour"])),
        delta_t_kelvin=float(st.session_state["energy_delta_t"]),
        jours_fonctionnement=int(st.session_state["energy_jours"]),
        surface_capteurs_m2=_none_if_zero(float(st.session_state["energy_surface_capteurs"])),
        volume_stockage_solaire_litres=_none_if_zero(float(st.session_state["energy_volume_stockage"])),
        productible_indicatif_kwh_m2_an=_none_if_zero(float(st.session_state["energy_productible_indicatif"])),
        zone_climatique=st.session_state["energy_zone"] or None,
        rendement_utile=float(st.session_state["energy_rendement_utile"]),
    )


def _render_results(block: EnergyBlock) -> None:
    results = block.results
    if results is None:
        st.info("Saisis les entrées puis valide pour calculer les indicateurs.")
        return

    cols = st.columns(3)
    cols[0].metric(
        "Énergie ECS",
        f"{results.energie_ecs_kwh_an:,.0f} kWh/an".replace(",", " ") if results.energie_ecs_kwh_an is not None else "—",
    )
    cols[1].metric(
        "Productible retenu",
        f"{results.productible_retenu_kwh_m2_an:.0f} kWh/m²·an"
        if results.productible_retenu_kwh_m2_an is not None
        else "—",
    )
    cols[2].metric(
        "Énergie solaire utile",
        f"{results.energie_solaire_utile_kwh_an:,.0f} kWh/an".replace(",", " ")
        if results.energie_solaire_utile_kwh_an is not None
        else "—",
    )

    cols2 = st.columns(3)
    cols2[0].metric(
        "Productivité",
        f"{results.productivite_kwh_m2_an:.0f} kWh/m²·an"
        if results.productivite_kwh_m2_an is not None
        else "—",
    )

    if results.taux_couverture is None:
        cols2[1].metric("Taux de couverture", "—")
    elif results.taux_couverture > 1.0:
        cols2[1].metric(
            "Taux de couverture",
            f"{results.taux_couverture * 100:.0f} %",
            delta="> 100 % à vérifier",
            delta_color="inverse",
        )
    else:
        cols2[1].metric("Taux de couverture", f"{results.taux_couverture * 100:.0f} %")

    cols2[2].metric(
        "Ratio stockage",
        f"{results.ratio_stockage_l_m2:.0f} L/m²" if results.ratio_stockage_l_m2 is not None else "—",
    )

    st.markdown(
        f"**Proposition de redimensionnement :** {results.proposition_redimensionnement or 'indeterminé'}"
    )

    if results.taux_couverture is not None and results.taux_couverture > 1.0:
        st.warning(
            f"Taux de couverture estimé à {results.taux_couverture * 100:.0f} % "
            "— supérieur à 100 %. Vérifier la saisie (volume ECS, ΔT, surface, "
            "productible) ou le dimensionnement avant publication."
        )

    for msg in results.messages:
        st.caption(f"• {msg}")


def render() -> None:
    """Rend le panneau de saisie + résultats dans le contexte courant."""
    block = _get_energy_block()
    _init_state(block)

    st.subheader("Calculs énergétiques (ECS / productivité)")
    st.caption(
        "Saisie d'aide à la décision : énergie ECS annuelle, énergie solaire "
        "utile, productivité, taux de couverture et ratio stockage. Les bornes "
        "ADEME / SOCOL pilotent la proposition de redimensionnement."
    )

    with st.form("energy_inputs_form", clear_on_submit=False):
        st.markdown("**Besoins ECS**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.number_input(
                "Volume ECS journalier (L/j)",
                min_value=0.0,
                step=50.0,
                key="energy_volume_ecs_jour",
                help="Volume d'eau chaude consommé en moyenne par jour.",
            )
        with col_b:
            st.number_input(
                "ΔT eau froide → ECS (K)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="energy_delta_t",
                help="Écart de température, plafonné à 100 K.",
            )
        with col_c:
            st.number_input(
                "Jours de fonctionnement (0-366)",
                min_value=0,
                max_value=366,
                step=1,
                key="energy_jours",
            )

        st.markdown("**Champ capteurs et stockage**")
        col_d, col_e = st.columns(2)
        with col_d:
            st.number_input(
                "Surface capteurs (m²)",
                min_value=0.0,
                step=1.0,
                key="energy_surface_capteurs",
                help="Surface utile retenue pour le calcul productivité.",
            )
        with col_e:
            st.number_input(
                "Volume stockage solaire (L)",
                min_value=0.0,
                step=50.0,
                key="energy_volume_stockage",
            )

        st.markdown("**Productible et rendement**")
        col_f, col_g, col_h = st.columns(3)
        with col_f:
            st.number_input(
                f"Productible indicatif (kWh/m²·an, 0 = défaut {PRODUCTIBLE_INDICATIF_DEFAUT:.0f})",
                min_value=0.0,
                step=10.0,
                key="energy_productible_indicatif",
            )
        with col_g:
            st.selectbox(
                "Zone climatique",
                _ZONES,
                key="energy_zone",
                help="Si pas de productible explicite, la zone fixe la valeur indicative.",
            )
        with col_h:
            st.number_input(
                "Rendement utile (0-1)",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="energy_rendement_utile",
            )

        submitted = st.form_submit_button("Calculer et enregistrer", type="primary")

    if submitted:
        try:
            inputs = _build_inputs_from_state()
        except Exception as exc:
            st.error(f"Saisie invalide : {exc}")
            return

        results = compute_energy(inputs)

        audit = get_audit()
        audit.energy.inputs = inputs
        audit.energy.results = results
        audit = touch_audit(audit)
        save_audit(audit)
        st.success("Calculs énergétiques mis à jour.")
        block = audit.energy

    st.markdown("---")
    _render_results(block)
