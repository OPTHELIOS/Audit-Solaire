import streamlit as st
import folium

from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from services.audit_service import touch_audit
from ui.state import get_audit, save_audit

GEOCODER = Nominatim(user_agent="opthelios-audit-app")


def _safe_str(value, default="") -> str:
    return value if value not in (None, "") else default


def _build_search_query(ligne_1: str, code_postal: str, commune: str, pays: str) -> str:
    parts = [ligne_1.strip(), code_postal.strip(), commune.strip(), pays.strip()]
    return ", ".join([p for p in parts if p])


def _extract_department(postcode: str, county: str) -> str:
    if county:
        return county
    if postcode and len(postcode) >= 2:
        return postcode[:2]
    return ""


def _geocode_address(query: str):
    if not query.strip():
        return None
    try:
        return GEOCODER.geocode(query, addressdetails=True, country_codes="fr", exactly_one=True)
    except Exception:
        return None


def _reverse_geocode(lat: float, lon: float):
    try:
        return GEOCODER.reverse((lat, lon), addressdetails=True, exactly_one=True)
    except Exception:
        return None


def _build_map(latitude: float | None, longitude: float | None, label: str) -> folium.Map:
    lat = latitude if latitude is not None else 46.603354
    lon = longitude if longitude is not None else 1.888334
    zoom = 18 if latitude is not None and longitude is not None else 6

    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None)

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Plan",
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite",
        control=True,
    ).add_to(m)

    if latitude is not None and longitude is not None:
        folium.Marker(
            [latitude, longitude],
            tooltip=label or "Site audité",
            popup=label or "Site audité",
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def _init_dossier_state(audit) -> None:
    projet = audit.projet
    adresse = projet.adresse
    contact_site = projet.contact_site

    defaults = {
        "dossier_operation": _safe_str(projet.operation),
        "dossier_maitre_ouvrage": _safe_str(projet.maitre_ouvrage),
        "dossier_exploitant": _safe_str(projet.exploitant),
        "dossier_mainteneur": _safe_str(projet.mainteneur),
        "dossier_ligne_1": _safe_str(adresse.ligne_1),
        "dossier_ligne_2": _safe_str(adresse.ligne_2),
        "dossier_code_postal": _safe_str(adresse.code_postal),
        "dossier_commune": _safe_str(adresse.commune),
        "dossier_departement": _safe_str(adresse.departement),
        "dossier_pays": _safe_str(adresse.pays, "France") or "France",
        "dossier_latitude": float(projet.latitude) if projet.latitude is not None else 0.0,
        "dossier_longitude": float(projet.longitude) if projet.longitude is not None else 0.0,
        "dossier_nom_contact": _safe_str(contact_site.nom),
        "dossier_fonction_contact": _safe_str(contact_site.fonction),
        "dossier_organisme_contact": _safe_str(contact_site.organisme),
        "dossier_telephone_contact": _safe_str(contact_site.telephone),
        "dossier_email_contact": _safe_str(contact_site.email),
        "dossier_commentaires_generaux": _safe_str(projet.commentaires_generaux),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _apply_pending_updates() -> None:
    pending_pairs = [
        ("dossier_pending_latitude", "dossier_latitude"),
        ("dossier_pending_longitude", "dossier_longitude"),
        ("dossier_pending_commune", "dossier_commune"),
        ("dossier_pending_code_postal", "dossier_code_postal"),
        ("dossier_pending_departement", "dossier_departement"),
        ("dossier_pending_pays", "dossier_pays"),
    ]

    for pending_key, target_key in pending_pairs:
        if pending_key in st.session_state:
            st.session_state[target_key] = st.session_state[pending_key]
            del st.session_state[pending_key]


def _apply_session_to_audit(audit) -> None:
    projet = audit.projet
    adresse = projet.adresse
    contact_site = projet.contact_site

    projet.operation = st.session_state["dossier_operation"] or None
    projet.maitre_ouvrage = st.session_state["dossier_maitre_ouvrage"] or None
    projet.exploitant = st.session_state["dossier_exploitant"] or None
    projet.mainteneur = st.session_state["dossier_mainteneur"] or None

    adresse.ligne_1 = st.session_state["dossier_ligne_1"] or None
    adresse.ligne_2 = st.session_state["dossier_ligne_2"] or None
    adresse.code_postal = st.session_state["dossier_code_postal"] or None
    adresse.commune = st.session_state["dossier_commune"] or None
    adresse.departement = st.session_state["dossier_departement"] or None
    adresse.pays = st.session_state["dossier_pays"] or "France"

    latitude = st.session_state["dossier_latitude"]
    longitude = st.session_state["dossier_longitude"]
    projet.latitude = latitude if latitude != 0.0 else None
    projet.longitude = longitude if longitude != 0.0 else None

    contact_site.nom = st.session_state["dossier_nom_contact"] or None
    contact_site.fonction = st.session_state["dossier_fonction_contact"] or None
    contact_site.organisme = st.session_state["dossier_organisme_contact"] or None
    contact_site.telephone = st.session_state["dossier_telephone_contact"] or None
    contact_site.email = st.session_state["dossier_email_contact"] or None

    projet.commentaires_generaux = st.session_state["dossier_commentaires_generaux"] or None


def _save_dossier(audit) -> None:
    _apply_session_to_audit(audit)

    audit = touch_audit(audit)
    save_audit(audit)

    commune = st.session_state["dossier_commune"]
    code_postal = st.session_state["dossier_code_postal"]
    departement = st.session_state["dossier_departement"]
    operation = st.session_state["dossier_operation"]
    maitre_ouvrage = st.session_state["dossier_maitre_ouvrage"]
    exploitant = st.session_state["dossier_exploitant"]
    mainteneur = st.session_state["dossier_mainteneur"]

    site_label_parts = [operation or "", commune or ""]
    site_label = " - ".join([part for part in site_label_parts if part]).strip() or "Site non renseigné"

    reference_parts = [
        "AUDIT",
        (commune or "").replace(" ", "_").upper(),
        str(audit.updated_at.year) if getattr(audit, "updated_at", None) else "",
    ]
    reference = "-".join([part for part in reference_parts if part]) or "AUDIT-SOLAIRE"

    st.session_state["audit_meta"] = {
        "site_name": site_label,
        "reference": reference,
        "audit_date": "",
        "nom_site": site_label,
        "site": site_label,
        "commune": commune or "",
        "code_postal": code_postal or "",
        "departement": departement or "",
        "maitre_ouvrage": maitre_ouvrage or "",
        "exploitant": exploitant or "",
        "mainteneur": mainteneur or "",
        "latitude": audit.projet.latitude or "",
        "longitude": audit.projet.longitude or "",
    }


def _geocode_from_address() -> bool:
    query = _build_search_query(
        st.session_state["dossier_ligne_1"],
        st.session_state["dossier_code_postal"],
        st.session_state["dossier_commune"],
        st.session_state["dossier_pays"],
    )

    result = _geocode_address(query)

    if result is None:
        st.warning("Aucune localisation trouvée à partir des informations saisies.")
        return False

    raw = result.raw.get("address", {})

    st.session_state["dossier_pending_latitude"] = float(result.latitude)
    st.session_state["dossier_pending_longitude"] = float(result.longitude)

    if not st.session_state["dossier_commune"]:
        st.session_state["dossier_pending_commune"] = (
            raw.get("city") or raw.get("town") or raw.get("village") or ""
        )

    if not st.session_state["dossier_code_postal"]:
        st.session_state["dossier_pending_code_postal"] = raw.get("postcode") or ""

    if not st.session_state["dossier_departement"]:
        st.session_state["dossier_pending_departement"] = _extract_department(
            raw.get("postcode", ""),
            raw.get("county", ""),
        )

    st.session_state["dossier_pending_pays"] = raw.get(
        "country",
        st.session_state["dossier_pays"] or "France",
    )

    return True


def _reverse_from_coordinates() -> bool:
    latitude = st.session_state["dossier_latitude"]
    longitude = st.session_state["dossier_longitude"]

    if latitude == 0.0 and longitude == 0.0:
        st.warning("Renseigne d'abord des coordonnées GPS valides.")
        return False

    result = _reverse_geocode(latitude, longitude)

    if result is None:
        st.warning("Aucune adresse trouvée à partir de ces coordonnées.")
        return False

    raw = result.raw.get("address", {})

    st.session_state["dossier_pending_commune"] = (
        raw.get("city") or raw.get("town") or raw.get("village") or st.session_state["dossier_commune"]
    )
    st.session_state["dossier_pending_code_postal"] = (
        raw.get("postcode") or st.session_state["dossier_code_postal"]
    )
    st.session_state["dossier_pending_departement"] = (
        _extract_department(raw.get("postcode", ""), raw.get("county", ""))
        or st.session_state["dossier_departement"]
    )
    st.session_state["dossier_pending_pays"] = (
        raw.get("country") or st.session_state["dossier_pays"] or "France"
    )

    return True


def render() -> None:
    audit = get_audit()
    _init_dossier_state(audit)
    _apply_pending_updates()

    st.header("01 - Dossier")
    st.caption("Identification du projet, localisation, acteurs et informations générales du site.")

    st.subheader("Identification du projet")

    st.text_input(
        "Nom de l'opération",
        key="dossier_operation",
        placeholder="Ex. Résidence Les Chênes - Audit installation solaire thermique",
    )

    st.text_input(
        "Maître d'ouvrage",
        key="dossier_maitre_ouvrage",
        placeholder="Nom du maître d'ouvrage",
    )

    st.text_input(
        "Exploitant",
        key="dossier_exploitant",
        placeholder="Nom de l'exploitant",
    )

    st.text_input(
        "Mainteneur",
        key="dossier_mainteneur",
        placeholder="Nom de l'entreprise de maintenance",
    )

    st.subheader("Adresse du site")

    st.text_input(
        "Adresse - ligne 1",
        key="dossier_ligne_1",
        placeholder="Ex. 12 rue de la Gare",
    )

    st.text_input(
        "Adresse - ligne 2",
        key="dossier_ligne_2",
        placeholder="Complément d'adresse",
    )

    col_cp, col_commune, col_dept = st.columns(3)

    with col_cp:
        st.text_input(
            "Code postal",
            key="dossier_code_postal",
            placeholder="56390",
        )

    with col_commune:
        st.text_input(
            "Commune",
            key="dossier_commune",
            placeholder="Grand-Champ",
        )

    with col_dept:
        st.text_input(
            "Département",
            key="dossier_departement",
            placeholder="Morbihan",
        )

    st.text_input(
        "Pays",
        key="dossier_pays",
    )

    map_label = st.session_state["dossier_operation"] or st.session_state["dossier_commune"] or "Site audité"
    map_lat = st.session_state["dossier_latitude"] if st.session_state["dossier_latitude"] != 0.0 else None
    map_lon = st.session_state["dossier_longitude"] if st.session_state["dossier_longitude"] != 0.0 else None

    dossier_map = _build_map(map_lat, map_lon, map_label)
    st_folium(dossier_map, width="100%", height=420)

    st.subheader("Géolocalisation")

    col_lat, col_lon = st.columns(2)

    with col_lat:
        st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            step=0.000001,
            format="%.6f",
            key="dossier_latitude",
        )

    with col_lon:
        st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            step=0.000001,
            format="%.6f",
            key="dossier_longitude",
        )

    col_geo1, col_geo2 = st.columns(2)

    with col_geo1:
        if st.button("Localiser à partir de l'adresse", use_container_width=True):
            if _geocode_from_address():
                st.rerun()

    with col_geo2:
        if st.button("Compléter depuis les coordonnées GPS", use_container_width=True):
            if _reverse_from_coordinates():
                st.rerun()

    st.subheader("Contact sur site")

    st.text_input(
        "Nom du contact",
        key="dossier_nom_contact",
        placeholder="Nom et prénom",
    )

    st.text_input(
        "Fonction",
        key="dossier_fonction_contact",
        placeholder="Ex. Responsable technique",
    )

    st.text_input(
        "Organisme",
        key="dossier_organisme_contact",
        placeholder="Ex. Syndic / Exploitant / Client",
    )

    col_tel, col_email = st.columns(2)

    with col_tel:
        st.text_input(
            "Téléphone",
            key="dossier_telephone_contact",
            placeholder="Ex. 06 00 00 00 00",
        )

    with col_email:
        st.text_input(
            "Email",
            key="dossier_email_contact",
            placeholder="Ex. contact@exemple.fr",
        )

    st.subheader("Commentaires généraux")

    st.text_area(
        "Commentaires",
        key="dossier_commentaires_generaux",
        placeholder="Contexte du dossier, remarques d'accès, informations générales utiles à l'audit...",
        height=120,
    )

    if st.button("Enregistrer le dossier", type="primary"):
        _save_dossier(audit)
        st.success("Dossier enregistré.")