from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from domain.docx_service import build_checklist_docx, build_docx_report
from domain.report_service import build_report_data, build_report_markdown
from ui.studio_panel import render_studio_summary

PAGE_TITLE = "06 - Export du rapport"
SESSION_CONCLUSION_KEY = "synthese_conclusion_expert"


def _get_context_from_session() -> dict[str, Any]:
    installation = st.session_state.get("installation_context", {})
    if not isinstance(installation, dict):
        installation = {}

    return {
        "systeme_capteurs": installation.get("systeme_capteurs"),
        "type_echangeur": installation.get("type_echangeur"),
        "type_stockage_solaire": (
            installation.get("type_stockage_solaire")
            or installation.get("type_stockage")
        ),
        "type_comptage": installation.get("type_comptage", []),
        "requires_monitoring": bool(installation.get("requires_monitoring", False)),
        "requires_telecontrole": bool(installation.get("requires_telecontrole", False)),
    }


def _get_export_metadata(payload: dict[str, Any] | None = None) -> dict[str, str]:
    payload_metadata = {}
    if isinstance(payload, dict):
        payload_metadata = payload.get("metadata", {}) or {}
        if not isinstance(payload_metadata, dict):
            payload_metadata = {}

    audit_meta = st.session_state.get("audit_meta", {})
    if not isinstance(audit_meta, dict):
        audit_meta = {}

    site_name = (
        payload_metadata.get("site_name")
        or audit_meta.get("site_name")
        or audit_meta.get("site")
        or audit_meta.get("nom_site")
        or audit_meta.get("operation")
        or "Site non renseigné"
    )

    reference = (
        payload_metadata.get("reference")
        or audit_meta.get("reference")
        or audit_meta.get("numero_audit")
        or audit_meta.get("audit_id")
        or audit_meta.get("site_slug")
        or "AUDIT-SOLAIRE"
    )

    audit_date = (
        payload_metadata.get("audit_date")
        or audit_meta.get("audit_date")
        or audit_meta.get("date_audit")
        or ""
    )

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
    ga = payload.get("global_assessment", {})
    counts = payload.get("counts", {})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Statut global", ga.get("statut_global", "-"))
    c2.metric("Constats", counts.get("total_findings", 0))
    c3.metric("Actions", counts.get("total_actions", 0))
    c4.metric("Critiques", counts.get("critical_findings", 0))


def _build_export_checklist(
    meta: dict[str, str],
    payload: dict[str, Any],
) -> list[tuple[str, bool, str]]:
    ga = payload.get("global_assessment", {})
    counts = payload.get("counts", {})
    metadata = payload.get("metadata", {}) or {}
    installation_context = st.session_state.get("installation_context", {})
    expert_conclusion = st.session_state.get(SESSION_CONCLUSION_KEY, "")

    return [
        (
            "Site renseigné",
            bool(meta["site_name"] and meta["site_name"] != "Site non renseigné"),
            "Le nom du site ou de l'opération doit être identifiable dans le livrable.",
        ),
        (
            "Référence audit renseignée",
            bool(meta["reference"] and meta["reference"] != "AUDIT-SOLAIRE"),
            "Une référence claire évite les confusions de version et de diffusion.",
        ),
        (
            "Installation qualifiée",
            bool(isinstance(installation_context, dict) and installation_context),
            "Le contexte technique doit être présent pour que le rapport soit cohérent.",
        ),
        (
            "Constats présents",
            counts.get("total_findings", 0) > 0,
            "Un rapport vide ou quasi vide doit être évité.",
        ),
        (
            "Audit suffisamment complété",
            ga.get("taux_completion_pct", 0) >= 80,
            "Sous 80 %, le rapport risque d’être interprété comme incomplet ou provisoire.",
        ),
        (
            "Conclusion experte disponible",
            bool(str(expert_conclusion).strip())
            or bool(str(ga.get("commentaire_global", "")).strip()),
            "Une conclusion éditorialisée améliore fortement la lisibilité du livrable.",
        ),
        (
            "Métadonnées exportables",
            bool(metadata),
            "Le service de rapport doit produire des métadonnées minimales pour fiabiliser le livrable.",
        ),
    ]


def _render_export_checklist(meta: dict[str, str], payload: dict[str, Any]) -> None:
    st.subheader("Vérification avant export")

    checklist = _build_export_checklist(meta, payload)
    cols = st.columns(len(checklist))

    for col, (label, ok, _) in zip(cols, checklist):
        if ok:
            col.success(label)
        else:
            col.warning(label)

    with st.expander("Détail des contrôles", expanded=False):
        for label, ok, help_text in checklist:
            icon = "✅" if ok else "⚠️"
            st.write(f"{icon} **{label}**")
            st.caption(help_text)

    if all(ok for _, ok, _ in checklist):
        st.success("Le dossier paraît prêt pour une génération de rapport exploitable.")
    else:
        st.info("Le rapport peut être généré, mais il est préférable de consolider les points signalés.")


def _get_export_profile_defaults(profile: str) -> dict[str, Any]:
    profiles = {
        "brouillon_interne": {
            "label": "Brouillon interne",
            "include_evidences": True,
            "report_title": "Brouillon interne - Rapport d’audit technique solaire thermique",
        },
        "version_client": {
            "label": "Version client",
            "include_evidences": False,
            "report_title": "Rapport d’audit technique solaire thermique",
        },
        "version_complete": {
            "label": "Version complète avec annexes",
            "include_evidences": True,
            "report_title": "Rapport complet d’audit technique solaire thermique",
        },
    }
    return profiles[profile]


def _render_docx_export(
    meta: dict[str, str],
    context: dict[str, Any],
    base_name: str,
    payload: dict[str, Any],
) -> None:
    st.subheader("Export DOCX")

    profile = st.selectbox(
        "Profil de livrable",
        options=["brouillon_interne", "version_client", "version_complete"],
        format_func=lambda p: _get_export_profile_defaults(p)["label"],
        index=2,
    )
    profile_defaults = _get_export_profile_defaults(profile)

    ga = payload.get("global_assessment", {})
    counts = payload.get("counts", {})

    with st.expander("Résumé du livrable", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Statut", ga.get("statut_global", "-"))
        c2.metric("Complétion", f"{ga.get('taux_completion_pct', 0)} %")
        c3.metric("Constats", counts.get("total_findings", 0))
        c4.metric("Actions", counts.get("total_actions", 0))

    with st.form("docx_export_form", clear_on_submit=False):
        report_title = st.text_input("Titre du rapport", value=profile_defaults["report_title"])
        site_name = st.text_input("Nom du site", value=meta["site_name"])
        reference = st.text_input("Référence audit", value=meta["reference"])
        audit_date = st.text_input(
            "Date d’audit",
            value=meta["audit_date"],
            placeholder="Ex. 08/04/2026",
        )
        include_evidences = st.checkbox(
            "Intégrer les preuves images disponibles",
            value=profile_defaults["include_evidences"],
        )

        submitted = st.form_submit_button("Générer le DOCX", use_container_width=True)

    if not submitted:
        return

    errors = []
    if not report_title.strip():
        errors.append("Le titre du rapport est obligatoire.")
    if not site_name.strip():
        errors.append("Le nom du site est obligatoire.")
    if not reference.strip():
        errors.append("La référence audit est obligatoire.")

    if errors:
        for error in errors:
            st.error(error)
        return

    try:
        with st.spinner("Génération du rapport Word en cours...", show_time=True):
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"{base_name}_{profile}.docx"

            audit = st.session_state.get("audit")
            cover_photo_path = getattr(getattr(audit, "projet", None), "photo_couverture_path", None)

            generated_path = build_docx_report(
                st.session_state,
                output_path=output_path,
                contexte_technique=context,
                report_title=report_title.strip(),
                site_name=site_name.strip(),
                reference=reference.strip(),
                audit_date=audit_date.strip() or None,
                include_evidences=include_evidences,
                cover_photo_path=cover_photo_path,
            )

            with open(generated_path, "rb") as f:
                docx_bytes = f.read()

        st.success("Rapport DOCX généré.")

        st.download_button(
            label="Télécharger le rapport DOCX",
            data=docx_bytes,
            file_name=Path(generated_path).name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
            help="Le fichier est généré à la demande puis proposé au téléchargement.",
        )

        # Memorise le chemin pour permettre une conversion PDF juste apres,
        # sans devoir regenerer le DOCX (voir _render_pdf_export, rendu en
        # dehors de ce formulaire).
        st.session_state["last_generated_docx_path"] = str(generated_path)

    except Exception as exc:
        st.error(f"Erreur lors de la génération du DOCX : {exc}")


def _render_pdf_export() -> None:
    st.subheader("Export PDF")
    st.caption(
        "Convertit le dernier rapport DOCX généré ci-dessus en PDF, en pilotant "
        "Microsoft Word installé sur cette machine. Fonctionne en local (Windows ou Mac "
        "avec Word installé) ; ne fonctionnera pas sur un hébergement cloud sans Word."
    )

    docx_path = st.session_state.get("last_generated_docx_path")
    if not docx_path or not Path(docx_path).exists():
        st.info("Génère d'abord un rapport DOCX ci-dessus avant de pouvoir le convertir en PDF.")
        return

    if st.button("Convertir le dernier DOCX généré en PDF", use_container_width=True):
        try:
            from docx2pdf import convert

            pdf_path = Path(docx_path).with_suffix(".pdf")
            with st.spinner("Conversion en PDF via Word en cours...", show_time=True):
                convert(str(docx_path), str(pdf_path))

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            st.success("PDF généré.")
            st.download_button(
                label="Télécharger le PDF",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                width="stretch",
            )
        except ImportError:
            st.error(
                "Le module `docx2pdf` n'est pas installé. Lance "
                "`pip install -r requirements.txt` puis relance l'application."
            )
        except Exception as exc:
            st.error(
                "Échec de la conversion en PDF. Cette fonctionnalité nécessite Microsoft "
                f"Word installé sur cette machine (Windows ou Mac). Détail : {exc}"
            )


def _render_checklist_export(base_name: str) -> None:
    st.subheader("Checklist terrain à imprimer")
    st.caption(
        "Liste condensée de TOUS les points de contrôle applicables (contrairement au "
        "rapport final, qui ne liste que les non-conformités déjà enregistrées), avec des "
        "cases vides à cocher. À imprimer et remplir à la main pendant la visite, avant la "
        "saisie détaillée dans l'application."
    )

    audit = st.session_state.get("audit")
    if audit is None:
        st.info("Aucun audit actif en session.")
        return

    if st.button("Générer la checklist terrain (DOCX)", use_container_width=True):
        try:
            with st.spinner("Génération de la checklist en cours...", show_time=True):
                output_dir = Path("output")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{base_name}_checklist_terrain.docx"

                generated_path = build_checklist_docx(audit, output_path=output_path)

                with open(generated_path, "rb") as f:
                    checklist_bytes = f.read()

            st.success("Checklist générée.")
            st.download_button(
                label="Télécharger la checklist (DOCX)",
                data=checklist_bytes,
                file_name=Path(generated_path).name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )
        except Exception as exc:
            st.error(f"Erreur lors de la génération de la checklist : {exc}")


def _render_markdown_export(context: dict[str, Any], base_name: str) -> None:
    st.subheader("Export Markdown")

    try:
        markdown_text = build_report_markdown(
            st.session_state,
            contexte_technique=context,
        )
    except Exception as exc:
        st.error(f"Erreur lors de la génération Markdown : {exc}")
        return

    with st.expander("Aperçu Markdown", expanded=True):
        st.text_area("Contenu Markdown", value=markdown_text, height=320)

    st.download_button(
        label="Télécharger le rapport Markdown",
        data=markdown_text.encode("utf-8"),
        file_name=f"{base_name}.md",
        mime="text/markdown",
        width="stretch",
    )


def _render_excel_export(payload: dict[str, Any], base_name: str) -> None:
    st.subheader("Export Excel du plan d'actions")
    st.caption(
        "Plan d'actions correctives au format tableur, avec des colonnes vides "
        "« Échéance », « Responsable » et « Statut » à compléter côté suivi de chantier."
    )

    actions = payload.get("action_plan") or []
    if not actions:
        st.info("Aucune action corrective à exporter pour le moment.")
        return

    try:
        import io

        import pandas as pd

        column_labels = {
            "priorite": "Priorité",
            "controle_id": "ID contrôle",
            "section": "Section",
            "objet": "Objet",
            "action_recommandee": "Action recommandée",
            "preuve_associee": "Preuve associée",
        }

        dataframe = pd.DataFrame(actions).rename(columns=column_labels)
        for extra_column in ["Échéance", "Responsable", "Statut"]:
            dataframe[extra_column] = ""

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Plan d'actions")

        st.download_button(
            label="Télécharger le plan d'actions (Excel)",
            data=buffer.getvalue(),
            file_name=f"{base_name}_plan_actions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    except Exception as exc:
        st.error(f"Erreur lors de la génération de l'export Excel : {exc}")


def _render_json_export(payload: dict[str, Any], base_name: str) -> None:
    st.subheader("Export JSON")

    json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    with st.expander("Aperçu JSON", expanded=False):
        st.text_area("Contenu JSON", value=json_text[:10000], height=320)

    st.download_button(
        label="Télécharger l'export JSON",
        data=json_text.encode("utf-8"),
        file_name=f"{base_name}.json",
        mime="application/json",
        width="stretch",
        help="Export technique utile pour contrôle qualité, archivage ou reprise de données.",
    )


def main() -> None:
    context = _get_context_from_session()

    try:
        payload = build_report_data(st.session_state, contexte_technique=context)
    except Exception as exc:
        st.title(PAGE_TITLE)
        st.error(f"Impossible de construire les données de rapport : {exc}")
        return

    meta = _get_export_metadata(payload)
    base_name = _safe_filename(f"{meta['reference']}_rapport_audit_technique")

    _render_header(meta)
    _render_payload_overview(payload)

    with st.expander("Studio OPT'HELIOS — synthèse rapide", expanded=False):
        render_studio_summary()

    _render_export_checklist(meta, payload)

    tab1, tab2, tab3 = st.tabs(["Livrable DOCX", "Checklist terrain", "Exports techniques"])

    with tab1:
        _render_docx_export(meta, context, base_name, payload)
        st.markdown("---")
        _render_pdf_export()

    with tab2:
        _render_checklist_export(base_name)

    with tab3:
        _render_markdown_export(context, base_name)
        st.markdown("---")
        _render_excel_export(payload, base_name)
        st.markdown("---")
        _render_json_export(payload, base_name)


def render() -> None:
    main()


if __name__ == "__main__":
    main()
