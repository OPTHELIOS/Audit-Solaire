import streamlit as st

from services.audit_service import touch_audit
from ui.state import get_audit, save_audit


def _safe_str(value, default="") -> str:
    return value if value not in (None, "") else default


def _init_installation_state(audit) -> None:
    installation = audit.installation

    defaults = {
        "inst_type_installation": _safe_str(installation.type_installation),
        "inst_usage_principal": _safe_str(installation.usage_principal),
        "inst_annee_mise_en_service": installation.annee_mise_en_service or 2020,
        "inst_description_generale": _safe_str(installation.description_generale),
        "inst_schema_hydraulique_disponible": installation.schema_hydraulique_disponible,
        "inst_schema_electrique_disponible": installation.schema_electrique_disponible,
        "inst_analyse_fonctionnelle_disponible": installation.analyse_fonctionnelle_disponible,
        "inst_telegestion_presente": installation.telegestion_presente,
        "inst_marque_modele": _safe_str(installation.champ_capteurs.marque_modele),
        "inst_nombre_capteurs": installation.champ_capteurs.nombre_capteurs,
        "inst_nombre_rangees": installation.champ_capteurs.nombre_rangees,
        "inst_surface_unitaire_m2": float(installation.champ_capteurs.surface_unitaire_m2 or 0.0),
        "inst_azimut_deg": float(installation.champ_capteurs.azimut_deg or 0.0),
        "inst_inclinaison_deg": float(installation.champ_capteurs.inclinaison_deg or 0.0),
        "inst_type_capteur": _safe_str(installation.champ_capteurs.type_capteur),
        "inst_nombre_ballons": installation.stockage_solaire.nombre_ballons,
        "inst_volume_total_litres": float(installation.stockage_solaire.volume_total_litres or 0.0),
        "inst_details_ballons_raw": "\n".join(installation.stockage_solaire.details_ballons),
        "inst_circulateur_solaire": _safe_str(installation.equipements.circulateur_solaire),
        "inst_regulateur": _safe_str(installation.equipements.regulateur),
        "inst_echangeur": _safe_str(installation.equipements.echangeur),
        "inst_vase_expansion": _safe_str(installation.equipements.vase_expansion),
        "inst_debitmetre": _safe_str(installation.equipements.debitmetre),
        "inst_compteur_energie": _safe_str(installation.equipements.compteur_energie),
        "inst_systeme_capteurs": installation.classification.systeme_capteurs or "",
        "inst_type_echangeur": installation.classification.type_echangeur or "",
        "inst_type_stockage": installation.classification.type_stockage or "",
        "inst_type_comptage": installation.classification.type_comptage or [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _apply_session_to_installation(audit) -> None:
    installation = audit.installation

    installation.type_installation = st.session_state["inst_type_installation"] or None
    installation.usage_principal = st.session_state["inst_usage_principal"] or None
    installation.annee_mise_en_service = int(st.session_state["inst_annee_mise_en_service"])
    installation.description_generale = st.session_state["inst_description_generale"] or None

    installation.schema_hydraulique_disponible = st.session_state["inst_schema_hydraulique_disponible"]
    installation.schema_electrique_disponible = st.session_state["inst_schema_electrique_disponible"]
    installation.analyse_fonctionnelle_disponible = st.session_state["inst_analyse_fonctionnelle_disponible"]
    installation.telegestion_presente = st.session_state["inst_telegestion_presente"]

    installation.champ_capteurs.marque_modele = st.session_state["inst_marque_modele"] or None
    installation.champ_capteurs.nombre_capteurs = int(st.session_state["inst_nombre_capteurs"])
    installation.champ_capteurs.nombre_rangees = int(st.session_state["inst_nombre_rangees"])

    surface_unitaire_m2 = float(st.session_state["inst_surface_unitaire_m2"])
    installation.champ_capteurs.surface_unitaire_m2 = surface_unitaire_m2 if surface_unitaire_m2 > 0 else None

    nombre_capteurs = int(st.session_state["inst_nombre_capteurs"])
    installation.champ_capteurs.surface_totale_m2 = (
        round(nombre_capteurs * surface_unitaire_m2, 2)
        if nombre_capteurs > 0 and surface_unitaire_m2 > 0
        else None
    )

    installation.champ_capteurs.azimut_deg = float(st.session_state["inst_azimut_deg"])
    installation.champ_capteurs.inclinaison_deg = float(st.session_state["inst_inclinaison_deg"])
    installation.champ_capteurs.type_capteur = st.session_state["inst_type_capteur"] or None

    installation.stockage_solaire.nombre_ballons = int(st.session_state["inst_nombre_ballons"])
    volume_total_litres = float(st.session_state["inst_volume_total_litres"])
    installation.stockage_solaire.volume_total_litres = volume_total_litres if volume_total_litres > 0 else None
    installation.stockage_solaire.details_ballons = [
        line.strip()
        for line in st.session_state["inst_details_ballons_raw"].splitlines()
        if line.strip()
    ]

    installation.equipements.circulateur_solaire = st.session_state["inst_circulateur_solaire"] or None
    installation.equipements.regulateur = st.session_state["inst_regulateur"] or None
    installation.equipements.echangeur = st.session_state["inst_echangeur"] or None
    installation.equipements.vase_expansion = st.session_state["inst_vase_expansion"] or None
    installation.equipements.debitmetre = st.session_state["inst_debitmetre"] or None
    installation.equipements.compteur_energie = st.session_state["inst_compteur_energie"] or None

    installation.classification.systeme_capteurs = st.session_state["inst_systeme_capteurs"] or None
    installation.classification.type_echangeur = st.session_state["inst_type_echangeur"] or None
    installation.classification.type_stockage = st.session_state["inst_type_stockage"] or None
    installation.classification.type_comptage = st.session_state["inst_type_comptage"]


def _save_installation(audit) -> None:
    _apply_session_to_installation(audit)

    audit = touch_audit(audit)
    save_audit(audit)

    installation = audit.installation

    st.session_state["installation_context"] = {
        "systeme_capteurs": installation.classification.systeme_capteurs,
        "type_echangeur": installation.classification.type_echangeur,
        "type_stockage_solaire": installation.classification.type_stockage,
        "type_comptage": installation.classification.type_comptage or [],
        "requires_monitoring": bool(
            installation.telegestion_presente or installation.equipements.compteur_energie
        ),
        "requires_telecontrole": bool(installation.telegestion_presente),
    }

    audit_meta = st.session_state.get("audit_meta", {})
    if not isinstance(audit_meta, dict):
        audit_meta = {}

    if not audit_meta.get("site_name"):
        audit_meta["site_name"] = "Site non renseigné"

    if not audit_meta.get("reference"):
        audit_meta["reference"] = "AUDIT-SOLAIRE"

    audit_meta["installation_type"] = installation.type_installation or ""
    audit_meta["usage_principal"] = installation.usage_principal or ""
    audit_meta["annee_mise_en_service"] = installation.annee_mise_en_service or ""
    audit_meta["systeme_capteurs"] = installation.classification.systeme_capteurs or ""
    audit_meta["type_echangeur"] = installation.classification.type_echangeur or ""
    audit_meta["type_stockage_solaire"] = installation.classification.type_stockage or ""
    audit_meta["type_comptage"] = installation.classification.type_comptage or []
    audit_meta["audit_date"] = audit_meta.get("audit_date") or ""

    st.session_state["audit_meta"] = audit_meta


def render():
    audit = get_audit()
    _init_installation_state(audit)

    st.header("04 - Installation")
    st.caption("Description technique générale de l'installation solaire thermique.")

    with st.form("installation_form", clear_on_submit=False):
        st.subheader("Caractéristiques générales")

        st.text_input(
            "Type d'installation",
            key="inst_type_installation",
            placeholder="Ex. Solaire thermique collectif ECS",
        )

        st.text_input(
            "Usage principal",
            key="inst_usage_principal",
            placeholder="Ex. ECS collective",
        )

        st.number_input(
            "Année de mise en service",
            min_value=1980,
            max_value=2100,
            step=1,
            key="inst_annee_mise_en_service",
        )

        st.text_area(
            "Description générale",
            key="inst_description_generale",
            placeholder=(
                "Description synthétique de l'installation, de son usage "
                "et de son principe de fonctionnement..."
            ),
            height=120,
        )

        st.subheader("Documents et supervision")

        st.checkbox(
            "Schéma hydraulique disponible",
            key="inst_schema_hydraulique_disponible",
        )

        st.checkbox(
            "Schéma électrique disponible",
            key="inst_schema_electrique_disponible",
        )

        st.checkbox(
            "Analyse fonctionnelle disponible",
            key="inst_analyse_fonctionnelle_disponible",
        )

        st.checkbox(
            "Télégestion présente",
            key="inst_telegestion_presente",
        )

        st.subheader("Champ capteurs")

        st.text_input(
            "Marque / modèle capteurs",
            key="inst_marque_modele",
        )

        col_cap1, col_cap2 = st.columns(2)
        with col_cap1:
            st.number_input(
                "Nombre de capteurs",
                min_value=0,
                step=1,
                key="inst_nombre_capteurs",
            )
        with col_cap2:
            st.number_input(
                "Nombre de rangées / champs",
                min_value=0,
                step=1,
                key="inst_nombre_rangees",
            )

        col_cap3, col_cap4, col_cap5 = st.columns(3)
        with col_cap3:
            st.number_input(
                "Surface unitaire capteur (m²)",
                min_value=0.0,
                step=0.1,
                key="inst_surface_unitaire_m2",
            )
        with col_cap4:
            st.number_input(
                "Azimut (°)",
                min_value=-180.0,
                max_value=180.0,
                step=1.0,
                key="inst_azimut_deg",
            )
        with col_cap5:
            st.number_input(
                "Inclinaison (°)",
                min_value=0.0,
                max_value=90.0,
                step=1.0,
                key="inst_inclinaison_deg",
            )

        st.text_input(
            "Type de capteur",
            key="inst_type_capteur",
            placeholder="Ex. plan vitré, tubes sous vide...",
        )

        surface_totale_calculee = (
            float(st.session_state["inst_nombre_capteurs"]) * float(st.session_state["inst_surface_unitaire_m2"])
        )
        st.info(f"Surface totale calculée : {surface_totale_calculee:.2f} m²")

        st.subheader("Stockage solaire")

        col_sto1, col_sto2 = st.columns(2)
        with col_sto1:
            st.number_input(
                "Nombre de ballons",
                min_value=0,
                step=1,
                key="inst_nombre_ballons",
            )
        with col_sto2:
            st.number_input(
                "Volume total de stockage (L)",
                min_value=0.0,
                step=10.0,
                key="inst_volume_total_litres",
            )

        st.text_area(
            "Détails ballons (une ligne par ballon)",
            key="inst_details_ballons_raw",
            placeholder="Ex. Ballon 1 - 1500 L - acier émaillé\nBallon 2 - 1500 L - acier émaillé",
            height=100,
        )

        st.subheader("Équipements techniques")

        st.text_input("Circulateur solaire", key="inst_circulateur_solaire")
        st.text_input("Régulateur / télégestion", key="inst_regulateur")
        st.text_input("Échangeur", key="inst_echangeur")
        st.text_input("Vase d'expansion", key="inst_vase_expansion")
        st.text_input("Débitmètre", key="inst_debitmetre")
        st.text_input("Compteur d'énergie", key="inst_compteur_energie")

        st.subheader("Classification installation")

        systeme_capteurs_options = ["", "autovidangeable", "sous_pression", "thermosiphon"]
        type_echangeur_options = ["", "echangeur_externe", "echangeur_immerge"]
        type_stockage_options = ["", "eau_sanitaire", "eau_technique"]

        current_systeme = st.session_state["inst_systeme_capteurs"]
        if current_systeme not in systeme_capteurs_options:
            current_systeme = ""

        current_type_echangeur = st.session_state["inst_type_echangeur"]
        if current_type_echangeur not in type_echangeur_options:
            current_type_echangeur = ""

        current_type_stockage = st.session_state["inst_type_stockage"]
        if current_type_stockage not in type_stockage_options:
            current_type_stockage = ""

        st.selectbox(
            "Système capteurs",
            systeme_capteurs_options,
            index=systeme_capteurs_options.index(current_systeme),
            key="inst_systeme_capteurs",
        )

        st.selectbox(
            "Type échangeur circuit primaire",
            type_echangeur_options,
            index=type_echangeur_options.index(current_type_echangeur),
            key="inst_type_echangeur",
        )

        st.selectbox(
            "Type stockage solaire",
            type_stockage_options,
            index=type_stockage_options.index(current_type_stockage),
            key="inst_type_stockage",
        )

        st.multiselect(
            "Type(s) de comptage",
            [
                "autre_comptage",
                "appoint",
                "bouclage_solaire",
                "solaire_primaire",
                "solaire_utile_direct",
                "solaire_utile_indirect",
            ],
            key="inst_type_comptage",
        )

        submitted = st.form_submit_button("Enregistrer l'installation", type="primary")

    if submitted:
        _save_installation(audit)
        st.success("Installation enregistrée.")