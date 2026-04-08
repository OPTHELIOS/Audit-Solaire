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


def _safe_str(value, default: str = "-") -> str:
    return value if value not in (None, "") else default


def render() -> None:
    audit = get_audit()

    st.header("03 - Preuves et annexes")
    st.caption("Gestion centralisée des photos, documents et pièces justificatives.")

    st.subheader("Ajouter une preuve")

    uploaded_file = st.file_uploader(
        "Fichier",
        type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "xls", "xlsx"],
        accept_multiple_files=False,
    )

    type_preuve = st.selectbox(
        "Type de preuve",
        options=list(TYPE_LABELS.keys()),
        format_func=lambda x: TYPE_LABELS[x],
    )

    legende = st.text_input(
        "Légende",
        placeholder="Ex. Soupape de sécurité absente sur le groupe solaire",
    )

    section = st.text_input(
        "Section",
        placeholder="Ex. Hydraulique solaire",
    )

    controle_options = {}
    for constat in getattr(audit, "constats", []):
        controle_id = getattr(constat, "controle_id", None)
        libelle = getattr(constat, "libelle", None)
        if controle_id:
            label = f"{controle_id} - {libelle or 'Sans libellé'}"
            controle_options[label] = controle_id

    selected_label = st.selectbox(
        "Rattacher à un contrôle",
        options=["Aucun"] + list(controle_options.keys()),
    )

    auteur = st.text_input(
        "Auteur / origine",
        value=getattr(audit.meta, "auditeur", "") or "",
    )

    if st.button("Enregistrer la preuve", type="primary"):
        if uploaded_file is None:
            st.error("Ajoute d'abord un fichier.")
        else:
            try:
                controle_id = None if selected_label == "Aucun" else controle_options[selected_label]

                preuve = save_uploaded_file(
                    audit_id=audit.meta.audit_id,
                    uploaded_file=uploaded_file,
                    type_preuve=type_preuve,
                    section=section or None,
                    controle_id=controle_id,
                    legende=legende or None,
                    auteur=auteur or None,
                )

                audit = attach_preuve_to_audit(audit, preuve)

                if controle_id:
                    audit = attach_preuve_to_constat(audit, controle_id, preuve.preuve_id)

                audit = touch_audit(audit)
                save_audit(audit)

                st.success("Preuve enregistrée et rattachée à l'audit.")
                st.rerun()

            except Exception as exc:
                st.error(f"Erreur lors de l'enregistrement de la preuve : {exc}")

    st.divider()
    st.subheader("Preuves enregistrées")

    preuves = getattr(audit, "preuves", [])

    if not preuves:
        st.info("Aucune preuve enregistrée.")
        return

    for preuve in preuves:
        titre = f"{getattr(getattr(preuve, 'type_preuve', None), 'value', 'PREUVE').upper()} - {_safe_str(getattr(preuve, 'nom_original', None), getattr(preuve, 'preuve_id', 'Sans identifiant'))}"

        with st.expander(titre):
            st.write(f"ID : {_safe_str(getattr(preuve, 'preuve_id', None))}")
            st.write(
                f"Type : {_safe_str(getattr(getattr(preuve, 'type_preuve', None), 'value', None))}"
            )
            st.write(f"Section : {_safe_str(getattr(preuve, 'section', None))}")
            st.write(f"Contrôle lié : {_safe_str(getattr(preuve, 'controle_id', None))}")
            st.write(f"Légende : {_safe_str(getattr(preuve, 'legende', None))}")
            st.write(f"Fichier : {_safe_str(getattr(preuve, 'fichier_path', None))}")
            st.write(f"Auteur : {_safe_str(getattr(preuve, 'auteur', None))}")