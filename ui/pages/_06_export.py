from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st

from domain.docx_service import build_docx_report
from domain.report_service import build_report_data, build_report_markdown

PAGE_TITLE = "06 - Export du rapport"


def _get_context_from_session() -> dict[str, Any]:
    installation = st.session_state.get("installation_context", {})
    if not isinstance(installation, dict):
        installation = {}

    return {
        "systeme_capteurs": installation.get("systeme_capteurs"),
        "type_echangeur": installation.get("type_echangeur"),
        "type_stockage_solaire": installation.get("type_stockage_solaire"),
        "type_comptage": installation.get("type_comptage", []),
        "requires_monitoring": bool(installation.get("requires_monitoring", False)),
        "requires_telecontrole": bool(installation.get("requires_telecontrole", False)),
    }


def _get_export_metadata() -> dict[str, str]:
    audit_meta = st.session_state.get("audit_meta", {})
    if not isinstance(audit_meta, dict):
        audit_meta = {}

    site_name = (
        audit_meta.get("site_name")
        or audit_meta.get("site")
        or audit_meta.get("nom_site")
        or "Site non renseigné"
    )
    reference = (
        audit_meta.get("reference")
        or audit_meta.get("audit_id")
        or audit_meta.get("site_slug")
        or "AUDIT-SOLAIRE"
    )
    audit_date = audit_meta.get("audit_date") or ""

    return {
        "site_name": str(site_name),
        "reference": str(reference),
        "audit_date": str(audit_date),
    }


def _safe_filename(text: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "rapport_audit"


def _render_header(meta: dict[str, str]) -> None:
    st.title(PAGE_TITLE)
    st.caption("Génération et téléchargement des livrables d’audit technique.")

    c1, c2, c3 = st.columns(3)
    c1.write(f"**Site** : {meta['site_name']}")
    c2.write(f"**Référence** : {meta['reference']}")
    c3.write(f"**Date audit** : {meta['audit_date'] or 'Non renseignée'}")


def _render_payload_overview(payload: dict[str, Any]) -> None:
    ga = payload["global_assessment"]
    counts = payload["counts"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Statut global", ga["statut_global"])
    c2.metric("Constats", counts["total_findings"])
    c3.metric("Actions", counts["total_actions"])
    c4.metric("Critiques", counts["critical_findings"])


def _render_markdown_export(payload: dict[str, Any], context: dict[str, Any], base_name: str) -> None:
    st.subheader("Export Markdown")

    markdown_text = build_report_markdown(
        st.session_state,
        contexte_technique=context,
    )

    st.text_area(
        "Aperçu Markdown",
        value=markdown_text,
        height=320,
    )

    st.download_button(
        label="Télécharger le rapport Markdown",
        data=markdown_text.encode("utf-8"),
        file_name=f"{base_name}.md",
        mime="text/markdown",
        width="stretch",
    )


def _render_json_export(payload: dict[str, Any], base_name: str) -> None:
    st.subheader("Export JSON")

    json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    st.text_area(
        "Aperçu JSON",
        value=json_text[:10000],
        height=320,
    )

    st.download_button(
        label="Télécharger l'export JSON",
        data=json_text.encode("utf-8"),
        file_name=f"{base_name}.json",
        mime="application/json",
        width="stretch",
    )


def _render_docx_export(meta: dict[str, str], context: dict[str, Any], base_name: str) -> None:
    st.subheader("Export DOCX")

    with st.form("docx_export_form", clear_on_submit=False):
        report_title = st.text_input(
            "Titre du rapport",
            value="Rapport d’audit technique solaire thermique",
        )
        site_name = st.text_input(
            "Nom du site",
            value=meta["site_name"],
        )
        reference = st.text_input(
            "Référence audit",
            value=meta["reference"],
        )
        audit_date = st.text_input(
            "Date d’audit",
            value=meta["audit_date"],
            placeholder="Ex. 08/04/2026",
        )
        include_evidences = st.checkbox(
            "Intégrer les preuves images disponibles",
            value=True,
        )

        submitted = st.form_submit_button("Générer le DOCX", use_container_width=True)

    if not submitted:
        return

    with st.spinner("Génération du rapport Word en cours...", show_time=True):
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{base_name}.docx"

        generated_path = build_docx_report(
            st.session_state,
            output_path=output_path,
            contexte_technique=context,
            report_title=report_title,
            site_name=site_name,
            reference=reference,
            audit_date=audit_date or None,
            include_evidences=include_evidences,
        )

        with open(generated_path, "rb") as f:
            docx_bytes = f.read()

    st.success("Rapport DOCX généré.")

    st.download_button(
        label="Télécharger le rapport DOCX",
        data=docx_bytes,
        file_name=generated_path.name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        width="stretch",
    )


def main() -> None:
    context = _get_context_from_session()
    meta = _get_export_metadata()
    payload = build_report_data(st.session_state, contexte_technique=context)

    base_name = _safe_filename(f"{meta['reference']}_rapport_audit_technique")

    _render_header(meta)
    _render_payload_overview(payload)

    tab1, tab2, tab3 = st.tabs(["Markdown", "JSON", "DOCX"])

    with tab1:
        _render_markdown_export(payload, context, base_name)

    with tab2:
        _render_json_export(payload, base_name)

    with tab3:
        _render_docx_export(meta, context, base_name)


if __name__ == "__main__":
    main()