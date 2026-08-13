from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from domain.enums import TypePreuve
from services.audit_service import touch_audit
from services.evidence_service import (
    attach_preuve_to_audit,
    attach_preuve_to_constat,
    save_uploaded_file,
)
from ui.state import get_audit, save_audit

TYPE_LABELS = {
    TypePreuve.PHOTO: "Photo",
    TypePreuve.DOCUMENT: "Document",
    TypePreuve.MESURE: "Mesure",
    TypePreuve.CAPTURE: "Capture",
    TypePreuve.PLAQUE_SIGNALETIQUE: "Plaque signalétique",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _safe_str(value: Any, default: str = "") -> str:
    return str(value) if value not in (None, "") else default


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    return getattr(obj, attr, default)


def _build_control_options(audit: Any) -> dict[str, dict[str, str]]:
    options: dict[str, dict[str, str]] = {}

    for constat in _safe_get(audit, "constats", []) or []:
        controle_id = _safe_get(constat, "controle_id")
        libelle = _safe_get(constat, "libelle", "Sans libellé")
        section = _safe_get(constat, "section", "")

        if not controle_id:
            continue

        label = f"{controle_id} - {libelle}"
        options[label] = {
            "controle_id": controle_id,
            "libelle": libelle,
            "section": section,
        }

    return options


def _build_evidence_rows(audit: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    preuves = _safe_get(audit, "preuves", []) or []

    for preuve in preuves:
        type_preuve = _safe_get(preuve, "type_preuve")
        type_value = _safe_get(type_preuve, "value", "Inconnu")
        file_path = _safe_str(_safe_get(preuve, "fichier_path"))
        suffix = Path(file_path).suffix.lower() if file_path else ""
        is_image = suffix in IMAGE_EXTENSIONS

        rows.append(
            {
                "preuve": preuve,
                "preuve_id": _safe_str(_safe_get(preuve, "preuve_id"), "Sans identifiant"),
                "type": type_value,
                "type_label": TYPE_LABELS.get(type_preuve, type_value),
                "nom_original": _safe_str(
                    _safe_get(preuve, "nom_original"),
                    Path(file_path).name if file_path else "Fichier sans nom",
                ),
                "section": _safe_str(_safe_get(preuve, "section"), "Non renseignée"),
                "controle_id": _safe_str(_safe_get(preuve, "controle_id")),
                "legende": _safe_str(_safe_get(preuve, "legende"), "Sans légende"),
                "auteur": _safe_str(_safe_get(preuve, "auteur"), "Non renseigné"),
                "file_path": file_path,
                "cloud_url": _safe_str(_safe_get(preuve, "cloud_url")),
                "is_orphan": not bool(_safe_get(preuve, "controle_id")),
                "is_image": is_image,
            }
        )

    return rows


def _render_top_metrics(rows: list[dict[str, Any]]) -> None:
    total = len(rows)
    linked = sum(1 for row in rows if row["controle_id"])
    orphan = sum(1 for row in rows if row["is_orphan"])
    photos = sum(1 for row in rows if row["type"] == TypePreuve.PHOTO.value)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preuves totales", total)
    c2.metric("Rattachées à un contrôle", linked)
    c3.metric("Preuves orphelines", orphan)
    c4.metric("Photos", photos)


def _render_add_form(audit: Any, control_options: dict[str, dict[str, str]]) -> None:
    st.subheader("Ajouter une ou plusieurs preuves")

    labels = ["Aucun"] + list(control_options.keys())
    selected_label = st.selectbox("Rattacher à un contrôle", options=labels, index=0)

    selected_control = control_options.get(selected_label) if selected_label != "Aucun" else None
    suggested_section = selected_control["section"] if selected_control else ""
    suggested_legend = (
        f"{selected_control['controle_id']} - {selected_control['libelle']}"
        if selected_control
        else ""
    )

    with st.form("preuve_form", clear_on_submit=False):
        uploaded_files = st.file_uploader(
            "Fichier(s)",
            type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "xls", "xlsx"],
            accept_multiple_files=True,
            help="Tu peux sélectionner plusieurs fichiers d'un coup (ex. plusieurs photos prises sur site).",
        )

        col1, col2 = st.columns(2)
        with col1:
            type_preuve = st.selectbox(
                "Type de preuve",
                options=list(TYPE_LABELS.keys()),
                format_func=lambda x: TYPE_LABELS[x],
            )
        with col2:
            auteur = st.text_input(
                "Auteur / origine",
                value=_safe_str(_safe_get(_safe_get(audit, "meta"), "auditeur")),
                placeholder="Nom de l'auditeur ou origine du document",
            )

        section = st.text_input(
            "Section",
            value=suggested_section,
            placeholder="Ex. Hydraulique solaire",
        )

        legende = st.text_input(
            "Légende",
            value=suggested_legend,
            placeholder="Ex. Soupape de sécurité absente sur le groupe solaire",
            help="Si tu ajoutes plusieurs fichiers, la même légende leur sera appliquée : à affiner ensuite si besoin.",
        )

        submitted = st.form_submit_button(
            "Enregistrer la/les preuve(s)",
            type="primary",
            use_container_width=True,
        )

        if not submitted:
            return

        if not uploaded_files:
            st.error("Ajoute d'abord au moins un fichier.")
            return

        controle_id = selected_control["controle_id"] if selected_control else None

        audit_updated = audit
        saved_count = 0
        errors: list[str] = []

        for uploaded_file in uploaded_files:
            try:
                preuve = save_uploaded_file(
                    audit=audit_updated,
                    uploaded_file=uploaded_file,
                    type_preuve=type_preuve,
                    section=section or None,
                    controle_id=controle_id,
                    legende=legende or None,
                    auteur=auteur or None,
                )

                audit_updated = attach_preuve_to_audit(audit_updated, preuve)

                if controle_id:
                    audit_updated = attach_preuve_to_constat(
                        audit_updated,
                        controle_id,
                        preuve.preuve_id,
                    )

                saved_count += 1

            except Exception as exc:
                errors.append(f"{uploaded_file.name} : {exc}")

        if saved_count:
            audit_updated = touch_audit(audit_updated)
            save_audit(audit_updated)
            st.success(f"{saved_count} preuve(s) enregistrée(s) et rattachée(s) à l'audit.")

        for message in errors:
            st.error(f"Erreur lors de l'enregistrement d'une preuve — {message}")

        if saved_count:
            st.rerun()


def _render_filters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    st.subheader("Filtrer les preuves")

    all_types = sorted({row["type_label"] for row in rows})
    all_sections = sorted({row["section"] for row in rows if row["section"]})
    all_controles = sorted({row["controle_id"] for row in rows if row["controle_id"]})

    c1, c2 = st.columns(2)
    with c1:
        selected_types = st.multiselect("Type", options=all_types, default=[])
        selected_sections = st.multiselect("Section", options=all_sections, default=[])
    with c2:
        selected_controles = st.multiselect("Contrôle lié", options=all_controles, default=[])
        orphan_only = st.checkbox("Afficher seulement les preuves orphelines", value=False)

    filtered = []

    for row in rows:
        if selected_types and row["type_label"] not in selected_types:
            continue
        if selected_sections and row["section"] not in selected_sections:
            continue
        if selected_controles and row["controle_id"] not in selected_controles:
            continue
        if orphan_only and not row["is_orphan"]:
            continue
        filtered.append(row)

    return filtered


def _render_orphan_alert(rows: list[dict[str, Any]]) -> None:
    orphan_count = sum(1 for row in rows if row["is_orphan"])

    if orphan_count:
        st.warning(
            f"{orphan_count} preuve(s) ne sont rattachées à aucun contrôle. "
            "Cela peut affaiblir la traçabilité du rapport."
        )
    else:
        st.success("Toutes les preuves sont rattachées à un contrôle ou correctement contextualisées.")


def _render_image_preview(file_path: str, caption: str) -> None:
    try:
        path = Path(file_path)
        if path.exists():
            st.image(str(path), caption=caption, use_container_width=True)
        else:
            st.caption("Aperçu image indisponible : fichier non accessible localement.")
    except Exception:
        st.caption("Aperçu image indisponible.")


def _render_evidence_card(row: dict[str, Any]) -> None:
    badge = "Orpheline" if row["is_orphan"] else f"Contrôle {row['controle_id']}"
    title = f"{row['type_label'].upper()} - {row['nom_original']}"

    with st.expander(title, expanded=False):
        col1, col2 = st.columns([1.2, 1])

        with col1:
            if row["is_image"]:
                _render_image_preview(row["file_path"], row["nom_original"])
            else:
                st.info("Aperçu non disponible pour ce type de fichier.")

        with col2:
            st.write(f"**ID** : {row['preuve_id']}")
            st.write(f"**Type** : {row['type_label']}")
            st.write(f"**Statut** : {badge}")
            st.write(f"**Section** : {row['section']}")
            st.write(f"**Légende** : {row['legende']}")
            st.write(f"**Auteur** : {row['auteur']}")
            st.write(f"**Fichier local** : {row['file_path'] or 'Non renseigné'}")
            if row["cloud_url"]:
                st.write(f"**Sauvegarde cloud** : [ouvrir dans SharePoint]({row['cloud_url']})")
            else:
                st.caption("☁️ Pas encore sauvegardée dans le cloud (secrets non configurés ou échec réseau).")

            if row["is_orphan"]:
                st.caption(
                    "Conseil : rattacher cette preuve à un contrôle améliore la traçabilité du rapport."
                )


def _render_existing_evidences(rows: list[dict[str, Any]]) -> None:
    st.subheader("Preuves enregistrées")

    if not rows:
        st.info("Aucune preuve ne correspond aux filtres sélectionnés.")
        return

    for row in rows:
        _render_evidence_card(row)


def render() -> None:
    audit = get_audit()

    st.header("03 - Preuves et annexes")
    st.caption("Gestion centralisée des photos, documents et pièces justificatives.")

    control_options = _build_control_options(audit)
    rows = _build_evidence_rows(audit)

    _render_top_metrics(rows)
    st.divider()

    _render_add_form(audit, control_options)
    st.divider()

    _render_orphan_alert(rows)

    if not rows:
        st.info("Aucune preuve enregistrée pour le moment.")
        return

    filtered_rows = _render_filters(rows)
    st.divider()
    _render_existing_evidences(filtered_rows)
