from __future__ import annotations

import streamlit as st

from domain.documents_catalog import DOCUMENTS_BY_CODE
from services.audit_service import touch_audit
from services.documents_service import (
    completion_stats,
    ensure_documents_state,
    save_document_file,
    update_document,
)
from ui.state import get_audit, save_audit

PAGE_TITLE = "Documents fournis"


def render() -> None:
    audit = get_audit()
    ensure_documents_state(audit)

    st.header(PAGE_TITLE)
    st.caption(
        "Suivi des documents administratifs et techniques attendus pour un dossier "
        "d'audit complet (DOE, schémas, garanties, contrats...). Distinct des preuves "
        "de « Preuves et annexes », qui documentent des constats terrain précis."
    )

    stats = completion_stats(audit)
    st.progress(
        (stats["fournis"] / stats["total"]) if stats["total"] else 0.0,
        text=f"{stats['fournis']} / {stats['total']} document(s) fourni(s)",
    )

    # Un seul formulaire, un seul bouton d'enregistrement pour toute la
    # liste (même logique que "Contrôles techniques" : éviter de devoir
    # cliquer après chaque ligne).
    with st.form("documents_form", clear_on_submit=False):
        for item in audit.documents_fournis:
            st.markdown(f"### {item.libelle}")

            description = DOCUMENTS_BY_CODE.get(item.code, {}).get("description", "")
            if description:
                st.caption(description)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.checkbox("Fourni", value=item.fourni, key=f"doc_{item.code}_fourni")
            with col2:
                st.text_input(
                    "Commentaire",
                    value=item.commentaire or "",
                    key=f"doc_{item.code}_commentaire",
                    placeholder="Ex. version datée du..., transmis par email le...",
                )

            if item.fichier_path:
                st.caption(f"📎 Fichier actuel : {item.fichier_path}")

            st.file_uploader(
                "Joindre / remplacer le fichier",
                key=f"doc_{item.code}_uploader",
            )

            st.markdown("---")

        submitted = st.form_submit_button(
            "Enregistrer les documents",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    for item in audit.documents_fournis:
        code = item.code
        fourni = st.session_state.get(f"doc_{code}_fourni", False)
        commentaire = st.session_state.get(f"doc_{code}_commentaire", "")
        uploaded = st.session_state.get(f"doc_{code}_uploader")

        fichier_path = None
        if uploaded is not None:
            try:
                fichier_path = save_document_file(audit, code, uploaded)
            except Exception as exc:
                st.error(f"{item.libelle} : échec de l'enregistrement du fichier — {exc}")

        update_document(
            audit,
            code,
            fourni=fourni,
            commentaire=commentaire,
            fichier_path=fichier_path,
        )

    audit = touch_audit(audit)
    save_audit(audit)
    st.success("Documents mis à jour.")
    st.rerun()
