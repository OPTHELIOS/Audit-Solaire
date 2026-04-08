import streamlit as st

from services.audit_service import touch_audit
from ui.state import get_audit, save_audit


def render():
    audit = get_audit()
    installation = audit.installation

    st.header("04 - Installation")
    st.caption("Description technique générale de l'installation solaire thermique.")

    # --- Caractéristiques générales ---
    st.subheader("Caractéristiques générales")

    type_installation = st.text_input(
        "Type d'installation",
        value=installation.type_installation or "",
        placeholder="Ex. Solaire thermique collectif ECS",
    )

    usage_principal = st.text_input(
        "Usage principal",
        value=installation.usage_principal or "",
        placeholder="Ex. ECS collective",
    )

    annee_mise_en_service = st.number_input(
        "Année de mise en service",
        min_value=1980,
        max_value=2100,
        value=installation.annee_mise_en_service or 2020,
        step=1,
    )

    description_generale = st.text_area(
        "Description générale",
        value=installation.description_generale or "",
        placeholder=(
            "Description synthétique de l'installation, de son usage "
            "et de son principe de fonctionnement..."
        ),
        height=120,
    )

    # --- Documents et supervision ---
    st.subheader("Documents et supervision")

    schema_hydraulique_disponible = st.checkbox(
        "Schéma hydraulique disponible",
        value=installation.schema_hydraulique_disponible,
    )

    schema_electrique_disponible = st.checkbox(
        "Schéma électrique disponible",
        value=installation.schema_electrique_disponible,
    )

    analyse_fonctionnelle_disponible = st.checkbox(
        "Analyse fonctionnelle disponible",
        value=installation.analyse_fonctionnelle_disponible,
    )

    telegestion_presente = st.checkbox(
        "Télégestion présente",
        value=installation.telegestion_presente,
    )

    # --- Champ capteurs ---
    st.subheader("Champ capteurs")

    marque_modele = st.text_input(
        "Marque / modèle capteurs",
        value=installation.champ_capteurs.marque_modele or "",
    )

    nombre_capteurs = st.number_input(
        "Nombre de capteurs",
        min_value=0,
        value=installation.champ_capteurs.nombre_capteurs,
        step=1,
    )

    nombre_rangees = st.number_input(
        "Nombre de rangées / champs",
        min_value=0,
        value=installation.champ_capteurs.nombre_rangees,
        step=1,
    )

    surface_unitaire_m2 = st.number_input(
        "Surface unitaire capteur (m²)",
        min_value=0.0,
        value=float(installation.champ_capteurs.surface_unitaire_m2 or 0.0),
        step=0.1,
    )

    azimut_deg = st.number_input(
        "Azimut (°)",
        min_value=-180.0,
        max_value=180.0,
        value=float(installation.champ_capteurs.azimut_deg or 0.0),
        step=1.0,
    )

    inclinaison_deg = st.number_input(
        "Inclinaison (°)",
        min_value=0.0,
        max_value=90.0,
        value=float(installation.champ_capteurs.inclinaison_deg or 0.0),
        step=1.0,
    )

    type_capteur = st.text_input(
        "Type de capteur",
        value=installation.champ_capteurs.type_capteur or "",
        placeholder="Ex. plan vitré, tubes sous vide...",
    )

    # --- Stockage solaire ---
    st.subheader("Stockage solaire")

    nombre_ballons = st.number_input(
        "Nombre de ballons",
        min_value=0,
        value=installation.stockage_solaire.nombre_ballons,
        step=1,
    )

    volume_total_litres = st.number_input(
        "Volume total de stockage (L)",
        min_value=0.0,
        value=float(installation.stockage_solaire.volume_total_litres or 0.0),
        step=10.0,
    )

    details_ballons_raw = st.text_area(
        "Détails ballons (une ligne par ballon)",
        value="\n".join(installation.stockage_solaire.details_ballons),
        placeholder=(
            "Ex. Ballon 1 - 1500 L - acier émaillé\n"
            "Ballon 2 - 1500 L - acier émaillé"
        ),
        height=100,
    )

    # --- Équipements techniques ---
    st.subheader("Équipements techniques")

    circulateur_solaire = st.text_input(
        "Circulateur solaire",
        value=installation.equipements.circulateur_solaire or "",
    )

    regulateur = st.text_input(
        "Régulateur / télégestion",
        value=installation.equipements.regulateur or "",
    )

    echangeur = st.text_input(
        "Échangeur",
        value=installation.equipements.echangeur or "",
    )

    vase_expansion = st.text_input(
        "Vase d'expansion",
        value=installation.equipements.vase_expansion or "",
    )

    debitmetre = st.text_input(
        "Débitmètre",
        value=installation.equipements.debitmetre or "",
    )

    compteur_energie = st.text_input(
        "Compteur d'énergie",
        value=installation.equipements.compteur_energie or "",
    )

    # --- Classification installation ---
    st.subheader("Classification installation")

    systeme_capteurs = st.selectbox(
        "Système capteurs",
        ["", "autovidangeable", "sous_pression", "thermosiphon"],
        index=["", "autovidangeable", "sous_pression", "thermosiphon"].index(
            installation.classification.systeme_capteurs or ""
        ),
    )

    type_echangeur = st.selectbox(
        "Type échangeur circuit primaire",
        ["", "echangeur_externe", "echangeur_immerge"],
        index=["", "echangeur_externe", "echangeur_immerge"].index(
            installation.classification.type_echangeur or ""
        ),
    )

    type_stockage = st.selectbox(
        "Type stockage solaire",
        ["", "eau_sanitaire", "eau_technique"],
        index=["", "eau_sanitaire", "eau_technique"].index(
            installation.classification.type_stockage or ""
        ),
    )

    type_comptage = st.multiselect(
        "Type(s) de comptage",
        [
            "autre_comptage",
            "appoint",
            "bouclage_solaire",
            "solaire_primaire",
            "solaire_utile_direct",
            "solaire_utile_indirect",
        ],
        default=installation.classification.type_comptage,
    )

        # --- Enregistrement ---
    if st.button("Enregistrer l'installation", type="primary"):
        installation.type_installation = type_installation or None
        installation.usage_principal = usage_principal or None
        installation.annee_mise_en_service = int(annee_mise_en_service)
        installation.description_generale = description_generale or None

        installation.schema_hydraulique_disponible = schema_hydraulique_disponible
        installation.schema_electrique_disponible = schema_electrique_disponible
        installation.analyse_fonctionnelle_disponible = analyse_fonctionnelle_disponible
        installation.telegestion_presente = telegestion_presente

        installation.champ_capteurs.marque_modele = marque_modele or None
        installation.champ_capteurs.nombre_capteurs = int(nombre_capteurs)
        installation.champ_capteurs.nombre_rangees = int(nombre_rangees)
        installation.champ_capteurs.surface_unitaire_m2 = (
            surface_unitaire_m2 if surface_unitaire_m2 > 0 else None
        )
        installation.champ_capteurs.surface_totale_m2 = (
            round(nombre_capteurs * surface_unitaire_m2, 2)
            if nombre_capteurs > 0 and surface_unitaire_m2 > 0
            else None
        )
        installation.champ_capteurs.azimut_deg = azimut_deg
        installation.champ_capteurs.inclinaison_deg = inclinaison_deg
        installation.champ_capteurs.type_capteur = type_capteur or None

        installation.stockage_solaire.nombre_ballons = int(nombre_ballons)
        installation.stockage_solaire.volume_total_litres = (
            volume_total_litres if volume_total_litres > 0 else None
        )
        installation.stockage_solaire.details_ballons = [
            line.strip()
            for line in details_ballons_raw.splitlines()
            if line.strip()
        ]

        installation.equipements.circulateur_solaire = circulateur_solaire or None
        installation.equipements.regulateur = regulateur or None
        installation.equipements.echangeur = echangeur or None
        installation.equipements.vase_expansion = vase_expansion or None
        installation.equipements.debitmetre = debitmetre or None
        installation.equipements.compteur_energie = compteur_energie or None

        installation.classification.systeme_capteurs = systeme_capteurs or None
        installation.classification.type_echangeur = type_echangeur or None
        installation.classification.type_stockage = type_stockage or None
        installation.classification.type_comptage = type_comptage

        audit = touch_audit(audit)
        save_audit(audit)

        st.session_state["installation_context"] = {
            "systeme_capteurs": installation.classification.systeme_capteurs,
            "type_echangeur": installation.classification.type_echangeur,
            "type_stockage_solaire": installation.classification.type_stockage,
            "type_comptage": installation.classification.type_comptage or [],
            "requires_monitoring": bool(
                installation.telegestion_presente
                or installation.equipements.compteur_energie
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

        st.success("Installation enregistrée.")