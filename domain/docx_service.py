from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

import domain.opthelios_style as style
from domain.audit_studio import (
    FORMULATIONS_BY_CODE,
    MODE_RAPPORT_LABELS,
    SCENARIOS_BY_CODE,
    AuditStudioBlock,
    extract_studio_from_session,
)
from domain.control_service import group_controls_by_section
from domain.dimensionnement_service import check_surface_vs_besoins, check_volume_stockage
from domain.performance_service import compute_performance_indicators
from domain.report_service import build_report_data
from domain.socol_reference import get_schema_ref

# CORRECTIF (demande utilisateur, sept. 2026) : le rapport DOCX utilisait le
# thème par defaut de Word (Calibri gris/bleu clair générique) sans le
# moindre logo — aucun rapport à la charte graphique OPT'HELIOS utilisée par
# ailleurs sur les notes techniques (bleu marine / or / bleu ciel, filets
# d'en-tête/pied de page, bandeaux de titre, encarts...). Ce fichier
# applique désormais partout le module `domain/opthelios_style.py`, qui
# reprend les codes exacts de cette charte. `assets/opthelios_logo.png`
# (absent jusqu'ici, voir CHANGES.md) a été ajouté : c'est le logo officiel
# OPT'HELIOS, repris tel quel depuis les notes techniques existantes.

LOGO_PATH = style.LOGO_PATH


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _set_document_language(document: Document, lang_code: str = "fr-FR") -> None:
    styles = document.styles
    for s in styles:
        try:
            rpr = s.element.get_or_add_rPr()
            lang = rpr.find(qn("w:lang"))
            if lang is None:
                lang = document.element.makeelement(qn("w:lang"), {})
                rpr.append(lang)
            lang.set(qn("w:val"), lang_code)
            lang.set(qn("w:eastAsia"), lang_code)
            lang.set(qn("w:bidi"), lang_code)
        except Exception:
            continue


def _is_image_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def _add_picture_if_exists(document: Document, image_path: str | Path, width_inches: float = 2.2) -> bool:
    p = Path(image_path)
    if not p.exists():
        return False
    if not _is_image_file(p):
        return False

    try:
        document.add_picture(str(p), width=Inches(width_inches))
        last_paragraph = document.paragraphs[-1]
        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return True
    except Exception:
        return False


def _add_bullets(document: Document, lines: list[str]) -> None:
    for line in lines:
        p = document.add_paragraph(line, style="List Bullet")
        for run in p.runs:
            run.font.name = style.FONT_NAME
            run.font.size = Pt(10)
            run.font.color.rgb = style._rgb(style.BODY_TEXT)


def _new_table(document: Document, rows: int, cols: int):
    table = document.add_table(rows=rows, cols=cols)
    return table


# --------------------------------------------------------------------------
# Page de garde
# --------------------------------------------------------------------------

def _add_cover_page(
    document: Document,
    report_title: str,
    site_name: str | None = None,
    reference: str | None = None,
    audit_date: str | None = None,
    cover_photo_path: str | None = None,
    maitre_ouvrage: str | None = None,
    installation_resume: str | None = None,
) -> None:
    """Vraie page de garde à l'image des notes techniques OPT'HELIOS :
    bandeau marine (titre + référence), bandeau jaune pâle (site), photo du
    site le cas échéant, bloc méta centré, puis filet or + bloc coordonnées
    OPT'HELIOS/logo en pied de page de garde."""
    style.add_cover_band(
        document,
        report_title.upper(),
        [s for s in ["Diagnostic technique de l'installation solaire thermique collective", reference] if s],
    )

    site_lines: list[tuple[str, bool, bool]] = []
    if site_name:
        site_lines.append((site_name.upper(), True, False))
    if installation_resume:
        site_lines.append((installation_resume, False, True))
    if site_lines:
        style.add_cover_site_band(document, site_lines)

    if cover_photo_path:
        _add_picture_if_exists(document, cover_photo_path, width_inches=4.3)
        document.add_paragraph("")

    meta_lines = []
    if maitre_ouvrage:
        meta_lines.append(f"Maître d'ouvrage : {maitre_ouvrage}")
    if audit_date:
        meta_lines.append(f"Date d'audit : {audit_date}")
    else:
        meta_lines.append(f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    meta_lines.append("Bureau d'études / MOE-AMO solaire : OPT'HELIOS")

    for line in meta_lines:
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(line)
        run.font.name = style.FONT_NAME
        run.font.size = Pt(10)
        run.font.color.rgb = style._rgb(style.BODY_TEXT)

    document.add_paragraph("")
    style.add_cover_footer_block(document)


def _add_signature_section(document: Document, auditeur: str | None = None) -> None:
    """Bloc de validation en fin de rapport : identifie l'auditeur et laisse
    une ligne pour une signature manuscrite (le document reste un .docx
    éditable, pas de signature électronique intégrée)."""
    style.add_heading(document, "Validation", level=1)
    document.add_paragraph(
        "Ce rapport a été établi par OPT'HELIOS sur la base des constats réalisés lors "
        "de la visite d'audit et des éléments transmis par le client."
    )

    table = _new_table(document, rows=2, cols=2)
    style.set_cell_text(table.rows[0].cells[0], "Auditeur", bold=True)
    style.set_cell_text(table.rows[0].cells[1], "Date", bold=True)
    style.set_cell_text(table.rows[1].cells[0], _safe_str(auditeur))
    style.set_cell_text(table.rows[1].cells[1], datetime.now().strftime("%d/%m/%Y"))
    style.style_table(table)

    document.add_paragraph("")
    p = document.add_paragraph()
    run = p.add_run("Signature :")
    run.bold = True
    run.font.name = style.FONT_NAME
    run.font.color.rgb = style._rgb(style.NAVY)
    document.add_paragraph("")
    document.add_paragraph("_" * 40)


def _resolve_expert_conclusion(payload: dict[str, Any]) -> str:
    return _safe_str(
        payload.get("expert_conclusion")
        or payload.get("global_assessment", {}).get("commentaire_global", "")
    )


def _add_global_assessment(document: Document, payload: dict[str, Any]) -> None:
    ga = payload["global_assessment"]
    counts = payload["counts"]

    style.add_heading(document, "1. Appréciation globale", level=1)
    style.add_callout(
        document,
        f"Statut global : {_safe_str(ga['statut_global']).upper()}",
        [_safe_str(ga["commentaire_global"])],
    )

    table = _new_table(document, rows=1, cols=5)
    headers = [
        "Statut global",
        "Taux de complétion",
        "Taux de conformité",
        "Constats critiques",
        "Constats majeurs",
    ]
    for cell, label in zip(table.rows[0].cells, headers):
        style.set_cell_text(cell, label, bold=True)

    row = table.add_row().cells
    values = [
        ga["statut_global"],
        f"{ga['taux_completion_pct']} %",
        f"{ga['taux_conformite_pct']} %",
        str(counts["critical_findings"]),
        str(counts["major_findings"]),
    ]
    for cell, value in zip(row, values):
        style.set_cell_text(cell, value)
    style.style_table(table)


def _add_executive_summary(document: Document, payload: dict[str, Any]) -> None:
    style.add_heading(document, "2. Synthèse exécutive", level=1)
    _add_bullets(document, payload["executive_summary"])

    style.add_heading(document, "2.1 Messages clés", level=2)
    style.add_callout(document, "Messages clés", payload["key_messages"])

    style.add_heading(document, "2.2 Note méthodologique", level=2)
    _add_bullets(document, payload["methodology_note"])


def _add_expert_conclusion_section(document: Document, payload: dict[str, Any]) -> None:
    expert_conclusion = _resolve_expert_conclusion(payload)
    if not expert_conclusion:
        return

    style.add_heading(document, "2.3 Conclusion experte", level=2)
    document.add_paragraph(expert_conclusion)


def _add_section_summary(document: Document, payload: dict[str, Any]) -> None:
    style.add_heading(document, "3. Lecture par section", level=1)

    rows = payload["section_summaries"]
    if not rows:
        document.add_paragraph("Aucun constat structurant n’est disponible à ce stade.")
        return

    table = _new_table(document, rows=1, cols=6)
    headers = [
        "Section",
        "Constats",
        "Critiques",
        "Majeures",
        "Non conformes",
        "Non vérifiables",
    ]
    for cell, label in zip(table.rows[0].cells, headers):
        style.set_cell_text(cell, label, bold=True)

    for item in rows:
        row = table.add_row().cells
        values = [
            item["section"],
            str(item["nb_constats"]),
            str(item["nb_critiques"]),
            str(item["nb_majeures"]),
            str(item["nb_non_conformes"]),
            str(item["nb_non_verifiables"]),
        ]
        for cell, value in zip(row, values):
            style.set_cell_text(cell, value)
    style.style_table(table)

    document.add_paragraph("")

    for item in rows:
        style.add_heading(document, item["section"], level=2)
        document.add_paragraph(item["texte_intro"])


def _add_findings(document: Document, payload: dict[str, Any], include_evidences: bool = True) -> None:
    style.add_heading(document, "4. Constats détaillés", level=1)

    findings_by_section = payload["findings_by_section"]
    if not findings_by_section:
        document.add_paragraph("Aucun constat détaillé n’est disponible.")
        return

    for section, rows in findings_by_section.items():
        style.add_heading(document, section, level=2)

        for row in rows:
            style.add_heading(document, f"{row['controle_id']} — {row['libelle']}", level=3)

            # Pastilles couleur feu tricolore (demande utilisateur, sept.
            # 2026) : le maître d'ouvrage, destinataire de ce rapport, doit
            # pouvoir repérer d'un coup d'œil les points qui exigent une
            # action (rouge/orange) de ceux qui sont acquis (vert), sans
            # avoir à lire chaque phrase de constat.
            p = document.add_paragraph()
            r = p.add_run("Verdict : ")
            r.bold = True
            r.font.name = style.FONT_NAME
            r.font.color.rgb = style._rgb(style.NAVY)
            style.add_status_badge(p, row["verdict"], kind="verdict")

            p = document.add_paragraph()
            r = p.add_run("Criticité : ")
            r.bold = True
            r.font.name = style.FONT_NAME
            r.font.color.rgb = style._rgb(style.NAVY)
            style.add_status_badge(p, row["criticite"], kind="criticite")

            document.add_paragraph(_safe_str(row["phrase_constat"]))
            document.add_paragraph(_safe_str(row["phrase_impact"]))
            document.add_paragraph(_safe_str(row["phrase_action"]))

            if row.get("preuve_documentaire"):
                p = document.add_paragraph()
                r = p.add_run("Preuve documentaire : ")
                r.bold = True
                r.font.color.rgb = style._rgb(style.NAVY)
                p.add_run(_safe_str(row["preuve_documentaire"]))

            if include_evidences and row.get("photos"):
                document.add_paragraph("Preuves photographiques / pièces jointes disponibles :")
                added_any = False
                for photo_path in row["photos"][:4]:
                    added = _add_picture_if_exists(document, photo_path, width_inches=2.2)
                    added_any = added_any or added
                    if not added:
                        document.add_paragraph(f"- {photo_path}", style="List Bullet")

                if not added_any:
                    document.add_paragraph(
                        "Les fichiers associés n’ont pas pu être intégrés comme images dans le document."
                    )


def _add_action_plan(document: Document, payload: dict[str, Any]) -> None:
    style.add_heading(document, "5. Plan d’actions", level=1)

    rows = payload["action_plan"]
    if not rows:
        document.add_paragraph("Aucune action corrective n’est actuellement générée.")
        return

    table = _new_table(document, rows=1, cols=6)
    headers = ["Priorité", "ID", "Section", "Objet", "Impact", "Action recommandée"]
    for cell, label in zip(table.rows[0].cells, headers):
        style.set_cell_text(cell, label, bold=True)

    for item in rows:
        row = table.add_row().cells
        values = [
            item["priorite"],
            item["controle_id"],
            item["section"],
            item["objet"],
            # .get() defensif : "impact" est desormais toujours fourni par
            # domain/control_service.py::build_action_plan, mais un plan
            # d'actions construit differemment (ancien format, appel direct)
            # ne doit pas faire planter la generation du DOCX.
            item.get("impact", ""),
            item["action_recommandee"],
        ]
        for cell, value in zip(row, values):
            style.set_cell_text(cell, _safe_str(value))
    style.style_table(table)


def _add_studio_sections(document: Document, studio: AuditStudioBlock | None) -> None:
    if studio is None:
        return

    style.add_heading(document, "6. Studio OPT'HELIOS — orientations stratégiques", level=1)

    mode_label = MODE_RAPPORT_LABELS.get(studio.mode_rapport.value, studio.mode_rapport.value)
    p = document.add_paragraph()
    p.add_run("Mode de rapport : ").bold = True
    p.add_run(mode_label)

    selected = studio.selected_scenarios()
    style.add_heading(document, "6.1 Scénarios retenus", level=2)
    if selected:
        for sel in selected:
            scenario = SCENARIOS_BY_CODE.get(sel.code)
            title = scenario.libelle if scenario else sel.code
            horizon = f" — {scenario.horizon}" if scenario and scenario.horizon else ""
            style.add_heading(document, f"{title}{horizon}", level=3)
            if scenario and scenario.description:
                document.add_paragraph(scenario.description)
            if sel.commentaire:
                p = document.add_paragraph()
                p.add_run("Justification OPT'HELIOS : ").bold = True
                p.add_run(_safe_str(sel.commentaire))
            if scenario and scenario.actions_types:
                document.add_paragraph("Actions types associées :")
                _add_bullets(document, list(scenario.actions_types))
    else:
        document.add_paragraph("Aucun scénario stratégique n'a été retenu à ce stade.")

    style.add_heading(document, "6.2 Formulations OPT'HELIOS appliquées", level=2)
    if studio.formulations:
        for idx, applied in enumerate(studio.formulations, start=1):
            template = FORMULATIONS_BY_CODE.get(applied.code)
            title = template.titre if template else applied.code
            section = applied.section or (template.theme if template else "")
            style.add_heading(document, f"{idx}. {title} — {section}".strip(" —"), level=3)

            constat = applied.constat_personnalise or (template.constat if template else "")
            impact = applied.impact_personnalise or (template.impact if template else "")
            recommandation = applied.recommandation_personnalisee or (
                template.recommandation if template else ""
            )

            if constat:
                p = document.add_paragraph()
                p.add_run("Constat : ").bold = True
                p.add_run(_safe_str(constat))
            if impact:
                p = document.add_paragraph()
                p.add_run("Impact : ").bold = True
                p.add_run(_safe_str(impact))
            if recommandation:
                p = document.add_paragraph()
                p.add_run("Recommandation : ").bold = True
                p.add_run(_safe_str(recommandation))
    else:
        document.add_paragraph("Aucune formulation type OPT'HELIOS n'a été appliquée.")

    if studio.note_strategique:
        style.add_heading(document, "6.3 Note stratégique", level=2)
        document.add_paragraph(_safe_str(studio.note_strategique))


def _add_appendix_metadata(document: Document, metadata: Mapping[str, Any] | None = None) -> None:
    style.add_heading(document, "7. Métadonnées", level=1)

    if not metadata:
        document.add_paragraph("Aucune métadonnée d’audit disponible.")
        return

    table = _new_table(document, rows=1, cols=2)
    style.set_cell_text(table.rows[0].cells[0], "Clé", bold=True)
    style.set_cell_text(table.rows[0].cells[1], "Valeur", bold=True)

    for key, value in metadata.items():
        row = table.add_row().cells
        style.set_cell_text(row[0], _safe_str(key))
        style.set_cell_text(row[1], _safe_str(value))
    style.style_table(table)


# --------------------------------------------------------------------------
# Performance mesurée, dimensionnement et annexe schéma SOCOL (demande
# utilisateur, sept. 2026 : "d'autres axes d'analyse réglementaire" inspirés
# de SOCOL/SOLO2018/THMès — voir CHANGES.md pour le détail de la demande et
# des sources).
# --------------------------------------------------------------------------

def _add_performance_section(document: Document, audit: Any) -> None:
    style.add_heading(document, "8. Performance et dimensionnement solaire", level=1)

    installation = getattr(audit, "installation", None) if audit is not None else None
    dimensionnement = getattr(installation, "dimensionnement", None) if installation else None

    if dimensionnement is not None and any(
        [
            dimensionnement.zone_climatique,
            dimensionnement.besoins_ecs_l_jour,
            dimensionnement.taux_couverture_vise_pct,
            dimensionnement.productible_theorique_kwh_m2_an,
            dimensionnement.source_etude,
        ]
    ):
        style.add_heading(document, "8.1 Dimensionnement d'origine", level=2)
        table = _new_table(document, rows=1, cols=2)
        style.set_cell_text(table.rows[0].cells[0], "Élément", bold=True)
        style.set_cell_text(table.rows[0].cells[1], "Valeur", bold=True)
        rows_data = [
            ("Zone climatique (fiche ratios SOCOL 2021)", dimensionnement.zone_climatique),
            ("Besoins ECS", f"{dimensionnement.besoins_ecs_l_jour} L/jour à 60°C" if dimensionnement.besoins_ecs_l_jour else None),
            ("Taux de couverture visé", f"{dimensionnement.taux_couverture_vise_pct} %" if dimensionnement.taux_couverture_vise_pct else None),
            ("Productible théorique", f"{dimensionnement.productible_theorique_kwh_m2_an} kWh/m².an" if dimensionnement.productible_theorique_kwh_m2_an else None),
            ("Surface de capteurs à l'étude", f"{dimensionnement.surface_capteurs_etude_m2} m²" if dimensionnement.surface_capteurs_etude_m2 else None),
            ("Source de l'étude", dimensionnement.source_etude),
        ]
        for label, value in rows_data:
            if not value:
                continue
            row = table.add_row().cells
            style.set_cell_text(row[0], label)
            style.set_cell_text(row[1], _safe_str(value))
        style.style_table(table)
    else:
        document.add_paragraph(
            "Aucune étude de dimensionnement d'origine n'a été renseignée pour cet audit "
            "(voir page « 04 - Installation », section Dimensionnement)."
        )

    style.add_heading(document, "8.2 Indicateurs de performance mesurée (nomenclature SOCOL)", level=2)
    document.add_paragraph(
        "FSAV (taux d'économie d'énergie d'appoint), Prod (productivité, kWh/m².an) et Taux "
        "(part des auxiliaires électriques) — formules du livret technique SOCOL. Calculés "
        "à partir des relevés d'énergie « sur la période » saisis en page « Mesures et "
        "comparaison » ; comparés au théorique renseigné ci-dessus quand il est disponible."
    )

    if audit is not None:
        indicators = compute_performance_indicators(audit)

        for key, label in [
            ("fsav_statut", "FSAV (taux de couverture réel / visé)"),
            ("prod_statut", "Prod (productivité réelle / théorique)"),
            ("taux_statut", "Taux (auxiliaires électriques)"),
        ]:
            statut = indicators[key]
            p = document.add_paragraph()
            r = p.add_run(f"{label} : ")
            r.bold = True
            r.font.name = style.FONT_NAME
            r.font.color.rgb = style._rgb(style.NAVY)
            style.add_colored_badge(p, statut.label, statut.couleur)
            document.add_paragraph(statut.commentaire)

        installation_surface = getattr(getattr(installation, "champ_capteurs", None), "surface_totale_m2", None) if installation else None
        check_stockage = check_volume_stockage(
            getattr(getattr(installation, "stockage_solaire", None), "volume_total_litres", None) if installation else None,
            installation_surface,
            getattr(getattr(installation, "classification", None), "type_stockage", None) if installation else None,
        )
        check_surface = check_surface_vs_besoins(
            installation_surface,
            getattr(dimensionnement, "besoins_ecs_l_jour", None) if dimensionnement else None,
            getattr(dimensionnement, "zone_climatique", None) if dimensionnement else None,
        )

        if check_stockage.valeur is not None or check_surface.valeur is not None:
            style.add_heading(document, "8.3 Pré-dimensionnement de contrôle (ratios SOCOL 2021)", level=2)
            for check in (check_surface, check_stockage):
                if check.valeur is not None:
                    document.add_paragraph(check.commentaire, style="List Bullet")


def _add_schema_appendix(document: Document, audit: Any) -> None:
    style.add_heading(document, "9. Annexe — schéma de principe de référence (SOCOL)", level=1)

    classification = getattr(getattr(audit, "installation", None), "classification", None) if audit is not None else None
    code = getattr(classification, "schema_reference_socol", None) if classification else None
    schema = get_schema_ref(code)

    if schema is None:
        document.add_paragraph(
            "Aucun schéma de référence SOCOL n'a été rattaché à cet audit (voir page "
            "« 04 - Installation », section Schéma de référence SOCOL)."
        )
        return

    style.add_heading(document, schema.libelle, level=2)
    document.add_paragraph(schema.principe)

    image_path = Path("assets") / "schemas_socol" / schema.image_filename
    _add_picture_if_exists(document, image_path, width_inches=6.0)

    if schema.points_vigilance:
        document.add_paragraph("Points de vigilance associés à ce montage :")
        _add_bullets(document, list(schema.points_vigilance))

    p = document.add_paragraph(
        "Schéma de principe générique redessiné par OPT'HELIOS ; la nomenclature SOCOL "
        "(www.solaire-collectif.fr) est utilisée comme référentiel professionnel, sans "
        "reproduction des schémas SOCOL originaux."
    )
    for run in p.runs:
        run.italic = True
        run.font.size = Pt(8)
        run.font.color.rgb = style._rgb(style.BODY_TEXT)


def build_docx_report(
    session_state: Any,
    output_path: str | Path,
    *,
    contexte_technique: Mapping[str, Any] | None = None,
    report_title: str = "Rapport d’audit technique solaire thermique",
    site_name: str | None = None,
    reference: str | None = None,
    audit_date: str | None = None,
    include_evidences: bool = True,
    cover_photo_path: str | None = None,
) -> Path:
    payload = build_report_data(session_state, contexte_technique=contexte_technique)
    metadata = payload.get("metadata") or {}

    document = Document()
    style.apply_base_document_style(document)
    _set_document_language(document, "fr-FR")

    header_left = report_title
    if site_name:
        header_left += f" — {site_name}"
    header_right = _safe_str(metadata.get("maitre_ouvrage")) or _safe_str(reference)
    style.apply_running_header_footer(document, header_left, header_right)

    _add_cover_page(
        document,
        report_title=report_title,
        site_name=site_name or _safe_str(metadata.get("operation")) or _safe_str(metadata.get("commune")),
        reference=reference or _safe_str(metadata.get("numero_audit")),
        audit_date=audit_date or _safe_str(metadata.get("date_audit")),
        cover_photo_path=cover_photo_path,
        maitre_ouvrage=_safe_str(metadata.get("maitre_ouvrage")),
    )
    document.add_page_break()

    _add_global_assessment(document, payload)
    document.add_page_break()

    _add_executive_summary(document, payload)
    _add_expert_conclusion_section(document, payload)
    document.add_page_break()

    _add_section_summary(document, payload)
    document.add_page_break()

    _add_findings(document, payload, include_evidences=include_evidences)
    document.add_page_break()

    _add_action_plan(document, payload)

    studio = extract_studio_from_session(session_state)
    if studio is not None:
        document.add_page_break()
        _add_studio_sections(document, studio)

    if metadata:
        document.add_page_break()
        _add_appendix_metadata(document, metadata)

    audit = session_state.get("audit") if hasattr(session_state, "get") else None
    if audit is not None:
        document.add_page_break()
        _add_performance_section(document, audit)
        document.add_page_break()
        _add_schema_appendix(document, audit)

    document.add_page_break()
    _add_signature_section(document, auditeur=metadata.get("auditeur"))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path


def build_checklist_docx(
    audit: Any,
    output_path: str | Path,
    *,
    report_title: str = "Checklist terrain — Audit solaire thermique",
) -> Path:
    """Checklist condensée à imprimer et remplir à la main PENDANT la visite,
    avant la saisie détaillée dans l'application (contrairement au rapport
    final, qui ne liste que les non-conformités déjà enregistrées, celle-ci
    liste TOUS les points applicables avec des cases vides à cocher)."""
    document = Document()
    style.apply_base_document_style(document)
    _set_document_language(document, "fr-FR")

    site_name = _safe_str(audit.projet.operation) or _safe_str(audit.projet.adresse.commune)
    header_left = report_title
    if site_name:
        header_left += f" — {site_name}"
    style.apply_running_header_footer(document, header_left, "")

    if Path(LOGO_PATH).exists():
        _add_picture_if_exists(document, LOGO_PATH, width_inches=1.4)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(report_title)
    run.bold = True
    run.font.name = style.FONT_NAME
    run.font.size = Pt(16)
    run.font.color.rgb = style._rgb(style.NAVY)

    if site_name:
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(site_name)
        run.bold = True
        run.font.name = style.FONT_NAME
        run.font.color.rgb = style._rgb(style.GOLD)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(
        "Date de la visite : ______________    |    Auditeur : ______________________"
    )
    document.add_paragraph("")

    legend = document.add_paragraph()
    legend.add_run("Légende verdict : ").bold = True
    legend.add_run("C = conforme · NC = non conforme · NP = non présent · NV = non vérifiable · SO = sans objet")
    document.add_paragraph("")

    grouped = group_controls_by_section(audit)
    for section in sorted(grouped.keys()):
        items = grouped[section]

        style.add_heading(document, section, level=1)

        table = _new_table(document, rows=1, cols=4)
        headers = ["ID", "Point de contrôle", "Verdict", "Observations"]
        for cell, label in zip(table.rows[0].cells, headers):
            style.set_cell_text(cell, label, bold=True)

        for item in items:
            row = table.add_row().cells
            style.set_cell_text(row[0], item.controle_id)
            style.set_cell_text(row[1], item.libelle)
            style.set_cell_text(row[2], "")
            style.set_cell_text(row[3], "")
        style.style_table(table)

        document.add_paragraph("")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
