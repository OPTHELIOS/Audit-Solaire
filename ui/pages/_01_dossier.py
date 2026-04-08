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


def render() -> None:
    audit = get_audit()
    projet = audit.projet
    adresse = projet.adresse
    contact_site = projet.contact_site

    st.header("01 - Dossier")
    st.caption("Identification du projet, localisation, acteurs et informations générales du site.")

    st.subheader("Identification du projet")

    operation = st.text_input(
        "Nom de l'opération",
        value=_safe_str(projet.operation),
        placeholder="Ex. Résidence Les Chênes - Audit installation solaire thermique",
    )

    maitre_ouvrage = st.text_input(
        "Maître d'ouvrage",
        value=_safe_str(projet.maitre_ouvrage),
        placeholder="Nom du maître d'ouvrage",
    )

    exploitant = st.text_input(
        "Exploitant",
        value=_safe_str(projet.exploitant),
        placeholder="Nom de l'exploitant",
    )

    mainteneur = st.text_input(
        "Mainteneur",
        value=_safe_str(projet.mainteneur),
        placeholder="Nom de l'entreprise de maintenance",
    )

    st.subheader("Adresse du site")

    ligne_1 = st.text_input(
        "Adresse - ligne 1",
        value=_safe_str(adresse.ligne_1),
        placeholder="Ex. 12 rue de la Gare",
    )

    ligne_2 = st.text_input(
        "Adresse - ligne 2",
        value=_safe_str(adresse.ligne_2),
        placeholder="Complément d'adresse",
    )

    col_cp, col_commune, col_dept = st.columns(3)

    with col_cp:
        code_postal = st.text_input(
            "Code postal",
            value=_safe_str(adresse.code_postal),
            placeholder="56390",
        )

    with col_commune:
        commune = st.text_input(
            "Commune",
            value=_safe_str(adresse.commune),
            placeholder="Grand-Champ",
        )

    with col_dept:
        departement = st.text_input(
            "Département",
            value=_safe_str(adresse.departement),
            placeholder="Morbihan",
        )

    pays = st.text_input(
        "Pays",
        value=_safe_str(adresse.pays, "France") or "France",
    )

    st.subheader("Géolocalisation")

    col_lat, col_lon = st.columns(2)

    with col_lat:
        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=float(projet.latitude or 0.0),
            step=0.000001,
            format="%.6f",
        )

    with col_lon:
        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=float(projet.longitude or 0.0),
            step=0.000001,
            format="%.6f",
        )

    col_geo1, col_geo2 = st.columns(2)

    with col_geo1:
        if st.button("Localiser à partir de l'adresse", use_container_width=True):
            query = _build_search_query(ligne_1, code_postal, commune, pays)
            result = _geocode_address(query)

            if result is None:
                st.warning("Aucune localisation trouvée à partir des informations saisies.")
            else:
                raw = result.raw.get("address", {})
                projet.latitude = float(result.latitude)
                projet.longitude = float(result.longitude)

                if not commune:
                    adresse.commune = raw.get("city") or raw.get("town") or raw.get("village") or ""
                else:
                    adresse.commune = commune

                if not code_postal:
                    adresse.code_postal = raw.get("postcode") or ""
                else:
                    adresse.code_postal = code_postal

                if not departement:
                    adresse.departement = _extract_department(
                        raw.get("postcode", ""),
                        raw.get("county", ""),
                    )
                else:
                    adresse.departement = departement

                adresse.pays = raw.get("country", pays or "France")
                save_audit(touch_audit(audit))
                st.success("Localisation trouvée et coordonnées mises à jour.")
                st.rerun()

    with col_geo2:
        if st.button("Compléter depuis les coordonnées GPS", use_container_width=True):
            if latitude == 0.0 and longitude == 0.0:
                st.warning("Renseigne d'abord des coordonnées GPS valides.")
            else:
                result = _reverse_geocode(latitude, longitude)
                if result is None:
                    st.warning("Aucune adresse trouvée à partir de ces coordonnées.")
                else:
                    raw = result.raw.get("address", {})
                    projet.latitude = latitude
                    projet.longitude = longitude
                    adresse.commune = raw.get("city") or raw.get("town") or raw.get("village") or commune
                    adresse.code_postal = raw.get("postcode") or code_postal
                    adresse.departement = _extract_department(
                        raw.get("postcode", ""),
                        raw.get("county", ""),
                    ) or departement
                    adresse.pays = raw.get("country") or pays or "France"

                    save_audit(touch_audit(audit))
                    st.success("Adresse mise à jour depuis les coordonnées GPS.")
                    st.rerun()

    map_label = operation or commune or "Site audité"
    map_lat = projet.latitude if projet.latitude is not None else (latitude if latitude != 0.0 else None)
    map_lon = projet.longitude if projet.longitude is not None else (longitude if longitude != 0.0 else None)

    dossier_map = _build_map(map_lat, map_lon, map_label)
    st_folium(dossier_map, width="100%", height=420)

    st.subheader("Contact sur site")

    nom_contact = st.text_input(
        "Nom du contact",
        value=_safe_str(contact_site.nom),
        placeholder="Nom et prénom",
    )

    fonction_contact = st.text_input(
        "Fonction",
        value=_safe_str(contact_site.fonction),
        placeholder="Ex. Responsable technique",
    )

    organisme_contact = st.text_input(
        "Organisme",
        value=_safe_str(contact_site.organisme),
        placeholder="Ex. Syndic / Exploitant / Client",
    )

    col_tel, col_email = st.columns(2)

    with col_tel:
        telephone_contact = st.text_input(
            "Téléphone",
            value=_safe_str(contact_site.telephone),
            placeholder="Ex. 06 00 00 00 00",
        )

    with col_email:
        email_contact = st.text_input(
            "Email",
            value=_safe_str(contact_site.email),
            placeholder="Ex. contact@exemple.fr",
        )

    st.subheader("Commentaires généraux")

    commentaires_generaux = st.text_area(
        "Commentaires",
        value=_safe_str(projet.commentaires_generaux),
        placeholder="Contexte du dossier, remarques d'accès, informations générales utiles à l'audit...",
        height=120,
    )

    if st.button("Enregistrer le dossier", type="primary"):
        projet.operation = operation or None
        projet.maitre_ouvrage = maitre_ouvrage or None
        projet.exploitant = exploitant or None
        projet.mainteneur = mainteneur or None

        adresse.ligne_1 = ligne_1 or None
        adresse.ligne_2 = ligne_2 or None
        adresse.code_postal = code_postal or None
        adresse.commune = commune or None
        adresse.departement = departement or None
        adresse.pays = pays or "France"

        projet.latitude = latitude if latitude != 0.0 else None
        projet.longitude = longitude if longitude != 0.0 else None

        contact_site.nom = nom_contact or None
        contact_site.fonction = fonction_contact or None
        contact_site.organisme = organisme_contact or None
        contact_site.telephone = telephone_contact or None
        contact_site.email = email_contact or None

        projet.commentaires_generaux = commentaires_generaux or None

        audit = touch_audit(audit)
        save_audit(audit)

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
            "latitude": projet.latitude or "",
            "longitude": projet.longitude or "",
        }

        st.success("Dossier enregistré.")