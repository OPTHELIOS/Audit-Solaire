from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from domain.docx_service import build_docx_report
from domain.report_service import build_report_data, build_report_markdown
from repositories import onedrive_repository
from services.onedrive_auth import OneDriveNotConfiguredError
from ui.state import get_audit, save_audit
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

            generated_path = build_docx_report(
                st.session_state,
                output_path=output_path,
                contexte_technique=context,
                report_title=report_title.strip(),
                site_name=site_name.strip(),
                reference=reference.strip(),
                audit_date=audit_date.strip() or None,
                include_evidences=include_evidences,
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

    except Exception as exc:
        st.error(f"Erreur lors de la génération du DOCX : {exc}")


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


def _render_onedrive_sync() -> None:
    st.subheader("Synchronisation OneDrive (photos & preuves)")
    st.caption(
        "Pousse les photos et documents associés aux preuves vers le dossier "
        "OneDrive de l'audit (`audits/<id>/evidences/<type>/...`). "
        "Le stockage local n'est pas modifié."
    )

    audit = get_audit()
    preuves = list(audit.preuves) if audit and audit.preuves else []
    syncables = [p for p in preuves if p.chemin_fichier]
    if not preuves:
        st.info("Aucune preuve enregistrée — rien à synchroniser.")
        return

    st.write(
        f"**{len(syncables)}** preuve(s) avec fichier local sur **{len(preuves)}** total."
    )

    if st.button("Synchroniser les photos & preuves OneDrive", type="secondary"):
        progress = st.progress(0.0, text="Préparation de l'upload…")
        log_placeholder = st.empty()
        total_count = max(len(audit.preuves), 1)

        def _on_progress(index: int, total: int, preuve) -> None:
            progress.progress(min(1.0, index / max(total, 1)), text=f"Upload {index}/{total}")

        try:
            results = onedrive_repository.upload_audit_evidences(audit, on_progress=_on_progress)
            save_audit(audit)
        except OneDriveNotConfiguredError as exc:
            progress.empty()
            st.warning(str(exc))
            return
        except Exception as exc:
            progress.empty()
            st.error(f"Authentification ou upload OneDrive impossible : {exc}")
            return

        progress.progress(1.0, text="Terminé")

        uploaded = [r for r in results if r["status"] == "uploaded"]
        skipped = [r for r in results if r["status"] == "skipped"]
        errors = [r for r in results if r["status"] == "error"]

        if uploaded:
            st.success(f"{len(uploaded)} preuve(s) uploadée(s) sur OneDrive.")
        if skipped:
            st.info(f"{len(skipped)} preuve(s) ignorée(s) (fichier local absent ou non renseigné).")
        if errors:
            st.error(f"{len(errors)} preuve(s) en erreur — détails ci-dessous.")

        with log_placeholder.expander("Détail par preuve", expanded=bool(errors)):
            for r in results:
                icon = {"uploaded": "✅", "skipped": "⚠️", "error": "❌"}.get(r["status"], "•")
                line = f"{icon} `{r['preuve_id']}` — {r['status']}"
                if r.get("onedrive_path"):
                    line += f" → `{r['onedrive_path']}`"
                if r.get("reason"):
                    line += f" — {r['reason']}"
                st.write(line)


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

    tab1, tab2 = st.tabs(["Livrable DOCX", "Exports techniques"])

    with tab1:
        _render_docx_export(meta, context, base_name, payload)

    with tab2:
        _render_markdown_export(context, base_name)
        st.markdown("---")
        _render_json_export(payload, base_name)
        st.markdown("---")
        _render_onedrive_sync()


def render() -> None:
    main()


if __name__ == "__main__":
    main()