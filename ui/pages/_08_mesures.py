from __future__ import annotations

from typing import Any

import streamlit as st

from domain.releves_catalog import RELEVES_CATALOG
from repositories.sharepoint_repository import SharePointNotConfigured, list_audits, load_audit
from services.audit_service import touch_audit
from services.comparison_service import compare_audits
from services.releves_service import add_releve, list_releves_sorted, remove_releve
from ui.state import get_audit, save_audit

PAGE_TITLE = "Mesures et comparaison"

CUSTOM_OPTION = "Personnalisé..."


def _catalog_options() -> dict[str, dict[str, str]]:
    options = {item["libelle"]: item for item in RELEVES_CATALOG}
    options[CUSTOM_OPTION] = {"code": "", "libelle": "", "type_mesure": "autre", "unite": ""}
    return options


def _render_add_releve_form(audit: Any) -> None:
    st.subheader("Ajouter un relevé")

    options = _catalog_options()
    control_labels = ["Aucun"] + [
        f"{c.controle_id} - {c.libelle}" for c in audit.constats
    ]

    with st.form("releve_form", clear_on_submit=True):
        selected_label = st.selectbox(
            "Type de relevé",
            options=list(options.keys()),
            index=0,
        )
        selected = options[selected_label]
        is_custom = selected_label == CUSTOM_OPTION

        col1, col2 = st.columns(2)
        with col1:
            libelle = st.text_input(
                "Libellé",
                value="" if is_custom else selected["libelle"],
                disabled=not is_custom,
                placeholder="Ex. Température retour ballon",
            )
        with col2:
            unite = st.text_input(
                "Unité",
                value="" if is_custom else selected["unite"],
                placeholder="Ex. °C, bar, L/min...",
            )

        valeur = st.number_input("Valeur", value=0.0, step=0.1, format="%.2f")

        controle_choice = st.selectbox("Rattacher à un point de contrôle (optionnel)", control_labels)
        commentaire = st.text_input(
            "Commentaire",
            placeholder="Ex. mesuré au manomètre chaufferie, conditions ensoleillées...",
        )

        submitted = st.form_submit_button("Ajouter le relevé", type="primary", use_container_width=True)

    if not submitted:
        return

    final_libelle = (libelle or selected["libelle"] or "").strip()
    if not final_libelle:
        st.error("Le libellé du relevé est obligatoire.")
        return

    controle_id = None
    section = None
    if controle_choice != "Aucun":
        controle_id = controle_choice.split(" - ", 1)[0]
        constat = next((c for c in audit.constats if c.controle_id == controle_id), None)
        section = constat.section if constat else None

    add_releve(
        audit,
        libelle=final_libelle,
        valeur=float(valeur),
        unite=unite.strip(),
        type_mesure=selected.get("type_mesure", "autre") or "autre",
        controle_id=controle_id,
        section=section,
        commentaire=commentaire.strip() or None,
    )

    audit = touch_audit(audit)
    save_audit(audit)
    st.success(f"Relevé « {final_libelle} » ajouté.")
    st.rerun()


def _render_releves_list(audit: Any) -> None:
    st.subheader("Relevés enregistrés")

    releves = list_releves_sorted(audit)
    if not releves:
        st.info("Aucun relevé enregistré pour le moment.")
        return

    for releve in releves:
        col1, col2 = st.columns([5, 1])
        with col1:
            details = f"**{releve.libelle}** : {releve.valeur} {releve.unite}"
            if releve.controle_id:
                details += f" · rattaché à `{releve.controle_id}`"
            details += f" · {releve.date_mesure.strftime('%d/%m/%Y %H:%M')}"
            st.write(details)
            if releve.commentaire:
                st.caption(releve.commentaire)
        with col2:
            if st.button("Supprimer", key=f"del_releve_{releve.releve_id}"):
                remove_releve(audit, releve.releve_id)
                audit_updated = touch_audit(audit)
                save_audit(audit_updated)
                st.rerun()


def _render_comparison(audit: Any) -> None:
    st.subheader("Comparer avec un audit antérieur")
    st.caption(
        "Compare le taux de complétion, le taux de conformité, les non-conformités "
        "critiques/majeures, et les relevés de mesure communs (rapprochés par libellé) "
        "avec un audit précédemment sauvegardé."
    )

    try:
        audits = list_audits()
    except SharePointNotConfigured as exc:
        st.info(str(exc))
        return
    except Exception as exc:
        st.error(f"Impossible de lister les audits sauvegardés : {exc}")
        return

    current_folder_ids = {audit.meta.dossier_cloud, audit.meta.audit_id}
    candidates = [a for a in audits if a.get("audit_id") not in current_folder_ids]

    if not candidates:
        st.info("Aucun autre audit sauvegardé n'est disponible pour comparaison.")
        return

    options: dict[str, str] = {}
    for item in candidates:
        label = (
            f"{item.get('numero_audit', '')} | {item.get('commune', '')} | "
            f"{item.get('date_modification', '')} | {item.get('audit_id', '')}"
        )
        options[label] = item.get("audit_id", "")

    selected_label = st.selectbox("Audit à comparer", list(options.keys()))

    if st.button("Comparer"):
        try:
            previous_audit = load_audit(options[selected_label])
        except Exception as exc:
            st.error(f"Impossible de charger cet audit : {exc}")
            return

        if previous_audit is None:
            st.error("Impossible de charger cet audit.")
            return

        comparison = compare_audits(audit, previous_audit)

        st.markdown("#### Indicateurs globaux")
        for row in comparison["audit_indicators"]:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(row["indicateur"])
            c2.write(f"{row['actuel']} {row['unite']}".strip())
            c3.write(f"{row['precedent']} {row['unite']}".strip())
            ecart = row["ecart"]
            sign = "+" if ecart > 0 else ""
            c4.write(f"{sign}{ecart} {row['unite']}".strip())

        if comparison["measure_indicators"]:
            st.markdown("#### Relevés de mesure communs")
            for row in comparison["measure_indicators"]:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(row["indicateur"])
                c2.write(f"{row['actuel']} {row['unite']}".strip())
                c3.write(f"{row['precedent']} {row['unite']}".strip())
                ecart = row["ecart"]
                sign = "+" if ecart > 0 else ""
                c4.write(f"{sign}{ecart} {row['unite']}".strip())
        else:
            st.caption(
                "Aucun relevé de mesure avec le même libellé n'a été trouvé dans les "
                "deux audits — impossible de les rapprocher automatiquement."
            )


def render() -> None:
    audit = get_audit()

    st.header(PAGE_TITLE)
    st.caption(
        "Relevés de mesure horodatés pris sur site (température, pression, débit...), "
        "et comparaison des indicateurs clés avec un audit antérieur du même site."
    )

    _render_add_releve_form(audit)
    st.divider()
    _render_releves_list(audit)
    st.divider()
    _render_comparison(audit)
