from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from domain.audit_studio import (
    FORMULATIONS_BY_CODE,
    MODE_RAPPORT_LABELS,
    SCENARIOS_BY_CODE,
    AuditStudioBlock,
    ModeRapport,
    extract_studio_from_session,
)
from domain.energy import EnergyResults, compute_energy, inputs_have_payload
from domain.report_service import build_report_data


# ---------------------------------------------------------------------------
# Charte graphique OPT'HELIOS
# ---------------------------------------------------------------------------

OPTHELIOS_BLEU_NUIT_HEX = "0B1F3A"
OPTHELIOS_BLEU_NUIT_RGB = RGBColor(0x0B, 0x1F, 0x3A)
OPTHELIOS_JAUNE_SOLAIRE_HEX = "F4B400"
OPTHELIOS_JAUNE_SOLAIRE_RGB = RGBColor(0xF4, 0xB4, 0x00)
OPTHELIOS_JAUNE_PALE_HEX = "FFF2CC"
OPTHELIOS_GRIS_DOUX_HEX = "F4F4F4"
OPTHELIOS_BLANC = RGBColor(0xFF, 0xFF, 0xFF)


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


# ---------------------------------------------------------------------------
# Helpers DOCX bas niveau
# ---------------------------------------------------------------------------


def _set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)


def _paragraph_border(paragraph, edges: Iterable[str], color: str, size: int = 6) -> None:
    """Adds borders to a paragraph (top, bottom, left, right)."""
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    for edge in edges:
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(size))
        border.set(qn("w:space"), "1")
        border.set(qn("w:color"), color)
        p_bdr.append(border)
    p_pr.append(p_bdr)


def _set_document_language(document: Document, lang_code: str = "fr-FR") -> None:
    styles = document.styles
    for style in styles:
        try:
            rpr = style.element.get_or_add_rPr()
            lang = rpr.find(qn("w:lang"))
            if lang is None:
                lang = OxmlElement("w:lang")
                rpr.append(lang)
            lang.set(qn("w:val"), lang_code)
            lang.set(qn("w:eastAsia"), lang_code)
            lang.set(qn("w:bidi"), lang_code)
        except Exception:
            continue


def _configure_page(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)


def _set_default_font(document: Document) -> None:
    styles = document.styles

    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)

    heading_specs = [
        ("Title", 22, True, OPTHELIOS_BLEU_NUIT_RGB),
        ("Heading 1", 15, True, OPTHELIOS_BLEU_NUIT_RGB),
        ("Heading 2", 12, True, OPTHELIOS_BLEU_NUIT_RGB),
        ("Heading 3", 10.5, True, OPTHELIOS_BLEU_NUIT_RGB),
    ]
    for style_name, size, bold, color in heading_specs:
        if style_name in styles:
            styles[style_name].font.name = "Calibri"
            styles[style_name].font.size = Pt(size)
            styles[style_name].font.bold = bold
            styles[style_name].font.color.rgb = color


# ---------------------------------------------------------------------------
# Page de garde / en-têtes / pieds
# ---------------------------------------------------------------------------


def _add_header(document: Document, report_title: str, reference: str | None = None) -> None:
    section = document.sections[0]
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    text = report_title
    if reference:
        text += f" — {reference}"
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(8)
    run.font.color.rgb = OPTHELIOS_BLEU_NUIT_RGB


def _add_footer(document: Document) -> None:
    section = document.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "OPT'HELIOS — Audit solaire thermique · contact@opthelios.fr · Document généré automatiquement"
    )
    run.font.size = Pt(8)
    run.font.color.rgb = OPTHELIOS_BLEU_NUIT_RGB


def _add_cover_page(
    document: Document,
    *,
    report_title: str,
    mode_label: str,
    site_name: str | None,
    address_lines: list[str],
    reference: str | None,
    audit_date: str | None,
    operation: str | None,
    maitre_ouvrage: str | None,
    auditeur: str | None,
) -> None:
    """Cover page in OPT'HELIOS livery — no external logo dependency."""

    # Top brand band — bleu nuit with optional placeholder "logo".
    brand = document.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _paragraph_shading(brand, OPTHELIOS_BLEU_NUIT_HEX)
    run = brand.add_run("  OPT'HELIOS  ")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = OPTHELIOS_JAUNE_SOLAIRE_RGB
    tag = brand.add_run("   AUDIT SOLAIRE THERMIQUE")
    tag.bold = True
    tag.font.size = Pt(12)
    tag.font.color.rgb = OPTHELIOS_BLANC

    document.add_paragraph("")

    # Yellow solar accent band.
    accent = document.add_paragraph()
    _paragraph_shading(accent, OPTHELIOS_JAUNE_SOLAIRE_HEX)
    accent_run = accent.add_run("  ")
    accent_run.font.size = Pt(4)

    document.add_paragraph("")
    document.add_paragraph("")

    # Report title.
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_run = title.add_run(report_title.upper())
    title_run.bold = True
    title_run.font.size = Pt(24)
    title_run.font.color.rgb = OPTHELIOS_BLEU_NUIT_RGB
    _paragraph_border(title, ("bottom",), OPTHELIOS_JAUNE_SOLAIRE_HEX, size=18)

    # Mode chip
    mode = document.add_paragraph()
    mode.alignment = WD_ALIGN_PARAGRAPH.LEFT
    chip = mode.add_run(f"  {mode_label}  ")
    chip.bold = True
    chip.font.size = Pt(11)
    chip.font.color.rgb = OPTHELIOS_BLEU_NUIT_RGB
    _paragraph_shading(mode, OPTHELIOS_JAUNE_PALE_HEX)

    document.add_paragraph("")

    # Site identity card (table).
    table = document.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.style = "Table Grid"

    def _row(label: str, value: str) -> None:
        row = table.add_row().cells
        _set_cell_text(row[0], label, bold=True, color=OPTHELIOS_BLEU_NUIT_RGB)
        _shade_cell(row[0], OPTHELIOS_JAUNE_PALE_HEX)
        _set_cell_text(row[1], _safe_str(value))

    if site_name:
        _row("Site / Bâtiment", site_name)
    if operation:
        _row("Opération", operation)
    if maitre_ouvrage:
        _row("Maître d'ouvrage", maitre_ouvrage)
    if address_lines:
        _row("Adresse", " — ".join(filter(None, address_lines)))
    if reference:
        _row("Référence audit", reference)
    if audit_date:
        _row("Date d'audit", audit_date)
    else:
        _row("Date de génération", datetime.now().strftime("%d/%m/%Y %H:%M"))
    if auditeur:
        _row("Auditeur", auditeur)

    # Spacer — push the contact footer down.
    for _ in range(2):
        document.add_paragraph("")

    # Bottom contact band.
    contact = document.add_paragraph()
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _paragraph_shading(contact, OPTHELIOS_BLEU_NUIT_HEX)
    contact_run = contact.add_run(
        "OPT'HELIOS — Bureau d'études solaire thermique  ·  contact@opthelios.fr"
    )
    contact_run.bold = True
    contact_run.font.size = Pt(11)
    contact_run.font.color.rgb = OPTHELIOS_JAUNE_SOLAIRE_RGB

    document.add_page_break()


# ---------------------------------------------------------------------------
# Tables / bullets / images
# ---------------------------------------------------------------------------


def _styled_header_row(table, headers: list[str]) -> None:
    hdr = table.rows[0].cells
    for cell, label in zip(hdr, headers):
        _set_cell_text(cell, label, bold=True, color=OPTHELIOS_BLANC)
        _shade_cell(cell, OPTHELIOS_BLEU_NUIT_HEX)


def _add_bullets(document: Document, lines: list[str]) -> None:
    for line in lines:
        document.add_paragraph(line, style="List Bullet")


def _is_image_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def _add_picture_if_exists(
    document: Document,
    image_path: str | Path,
    width_inches: float = 2.4,
    caption: str | None = None,
) -> bool:
    p = Path(image_path)
    if not p.exists():
        return False
    if not _is_image_file(p):
        return False

    try:
        document.add_picture(str(p), width=Inches(width_inches))
        last_paragraph = document.paragraphs[-1]
        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            cap = document.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_run = cap.add_run(caption)
            cap_run.italic = True
            cap_run.font.size = Pt(9)
            cap_run.font.color.rgb = OPTHELIOS_BLEU_NUIT_RGB
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Sections du rapport
# ---------------------------------------------------------------------------


def _resolve_expert_conclusion(payload: dict[str, Any]) -> str:
    return _safe_str(
        payload.get("expert_conclusion")
        or payload.get("global_assessment", {}).get("commentaire_global", "")
    )


def _add_global_assessment(document: Document, payload: dict[str, Any]) -> None:
    ga = payload["global_assessment"]
    counts = payload["counts"]

    document.add_heading("1. Appréciation globale", level=1)
    document.add_paragraph(_safe_str(ga["commentaire_global"]))

    table = document.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    _styled_header_row(
        table,
        [
            "Statut global",
            "Taux de complétion",
            "Taux de conformité",
            "Constats critiques",
            "Constats majeurs",
        ],
    )

    row = table.add_row().cells
    values = [
        ga["statut_global"],
        f"{ga['taux_completion_pct']} %",
        f"{ga['taux_conformite_pct']} %",
        str(counts["critical_findings"]),
        str(counts["major_findings"]),
    ]
    for cell, value in zip(row, values):
        _set_cell_text(cell, value)


def _add_executive_summary(document: Document, payload: dict[str, Any]) -> None:
    document.add_heading("2. Synthèse exécutive", level=1)
    _add_bullets(document, payload["executive_summary"])

    document.add_heading("2.1 Messages clés", level=2)
    _add_bullets(document, payload["key_messages"])

    document.add_heading("2.2 Note méthodologique", level=2)
    _add_bullets(document, payload["methodology_note"])


def _add_expert_conclusion_section(document: Document, payload: dict[str, Any]) -> None:
    expert_conclusion = _resolve_expert_conclusion(payload)
    if not expert_conclusion:
        return
    document.add_heading("2.3 Conclusion experte", level=2)
    document.add_paragraph(expert_conclusion)


def _add_section_summary(document: Document, payload: dict[str, Any]) -> None:
    document.add_heading("3. Lecture par section", level=1)

    rows = payload["section_summaries"]
    if not rows:
        document.add_paragraph("Aucun constat structurant n'est disponible à ce stade.")
        return

    table = document.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    _styled_header_row(
        table,
        [
            "Section",
            "Constats",
            "Critiques",
            "Majeures",
            "Non conformes",
            "Non vérifiables",
        ],
    )

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
            _set_cell_text(cell, value)

    document.add_paragraph("")

    for item in rows:
        document.add_heading(item["section"], level=2)
        document.add_paragraph(item["texte_intro"])


def _photo_caption(audit, photo_path: str) -> str:
    """Best-effort lookup of a caption for a local photo path."""
    if audit is None:
        return ""
    try:
        preuves = list(getattr(audit, "preuves", []) or [])
    except Exception:
        return ""
    for preuve in preuves:
        chemin = getattr(preuve, "chemin_fichier", None)
        if chemin and Path(chemin) == Path(photo_path):
            return _safe_str(getattr(preuve, "legende", "") or getattr(preuve, "commentaire", ""))
    return ""


def _resolve_audit(session_state: Any):
    if session_state is None:
        return None
    if hasattr(session_state, "get"):
        audit = session_state.get("audit") or session_state.get("current_audit")
        if audit is not None:
            return audit
    return getattr(session_state, "audit", None) or getattr(session_state, "current_audit", None)


def _add_findings(
    document: Document,
    payload: dict[str, Any],
    *,
    audit_for_captions: Any,
    include_evidences: bool = True,
) -> None:
    document.add_heading("4. Constats détaillés", level=1)

    findings_by_section = payload["findings_by_section"]
    if not findings_by_section:
        document.add_paragraph("Aucun constat détaillé n'est disponible.")
        return

    for section, rows in findings_by_section.items():
        document.add_heading(section, level=2)

        for row in rows:
            document.add_heading(f"{row['controle_id']} — {row['libelle']}", level=3)

            p = document.add_paragraph()
            r = p.add_run("Verdict : ")
            r.bold = True
            p.add_run(_safe_str(row["verdict"]))

            p = document.add_paragraph()
            r = p.add_run("Criticité : ")
            r.bold = True
            p.add_run(_safe_str(row["criticite"]))

            document.add_paragraph(_safe_str(row["phrase_constat"]))
            document.add_paragraph(_safe_str(row["phrase_impact"]))
            document.add_paragraph(_safe_str(row["phrase_action"]))

            if row.get("preuve_documentaire"):
                p = document.add_paragraph()
                r = p.add_run("Preuve documentaire : ")
                r.bold = True
                p.add_run(_safe_str(row["preuve_documentaire"]))

            if include_evidences and row.get("photos"):
                document.add_paragraph("Preuves photographiques / pièces jointes :")
                added_any = False
                for photo_path in row["photos"][:4]:
                    caption = _photo_caption(audit_for_captions, photo_path)
                    added = _add_picture_if_exists(
                        document, photo_path, width_inches=2.4, caption=caption
                    )
                    added_any = added_any or added
                    if not added:
                        bullet = f"- {photo_path}"
                        if caption:
                            bullet += f" — {caption}"
                        document.add_paragraph(bullet, style="List Bullet")

                if not added_any:
                    document.add_paragraph(
                        "Les fichiers associés n'ont pas pu être intégrés comme images dans le document."
                    )


def _add_action_plan(document: Document, payload: dict[str, Any]) -> None:
    document.add_heading("5. Plan d'actions", level=1)

    rows = payload["action_plan"]
    if not rows:
        document.add_paragraph("Aucune action corrective n'est actuellement générée.")
        return

    table = document.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    _styled_header_row(
        table,
        ["Priorité", "ID", "Section", "Objet", "Impact", "Action recommandée"],
    )

    for item in rows:
        row = table.add_row().cells
        values = [
            item["priorite"],
            item["controle_id"],
            item["section"],
            item["objet"],
            item["impact"],
            item["action_recommandee"],
        ]
        for cell, value in zip(row, values):
            _set_cell_text(cell, _safe_str(value))


def _add_studio_sections(document: Document, studio: AuditStudioBlock | None) -> None:
    if studio is None:
        return

    document.add_heading("6. Studio OPT'HELIOS — orientations stratégiques", level=1)

    mode_label = MODE_RAPPORT_LABELS.get(studio.mode_rapport.value, studio.mode_rapport.value)
    p = document.add_paragraph()
    p.add_run("Mode de rapport : ").bold = True
    p.add_run(mode_label)

    selected = studio.selected_scenarios()
    document.add_heading("6.1 Scénarios retenus", level=2)
    if selected:
        for sel in selected:
            scenario = SCENARIOS_BY_CODE.get(sel.code)
            title = scenario.libelle if scenario else sel.code
            horizon = f" — {scenario.horizon}" if scenario and scenario.horizon else ""
            document.add_heading(f"{title}{horizon}", level=3)
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

    document.add_heading("6.2 Formulations OPT'HELIOS appliquées", level=2)
    if studio.formulations:
        for idx, applied in enumerate(studio.formulations, start=1):
            template = FORMULATIONS_BY_CODE.get(applied.code)
            title = template.titre if template else applied.code
            section = applied.section or (template.theme if template else "")
            document.add_heading(f"{idx}. {title} — {section}".strip(" —"), level=3)

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
        document.add_heading("6.3 Note stratégique", level=2)
        document.add_paragraph(_safe_str(studio.note_strategique))


def _add_installation_section(document: Document, audit: Any) -> None:
    """Description longue de l'installation (rapport audit complet)."""
    if audit is None:
        return
    installation = getattr(audit, "installation", None)
    if installation is None:
        return

    document.add_heading("0. Description de l'installation", level=1)

    def _line(label: str, value: Any) -> None:
        if value in (None, "", 0):
            return
        p = document.add_paragraph()
        p.add_run(f"{label} : ").bold = True
        p.add_run(_safe_str(value))

    _line("Type d'installation", getattr(installation, "type_installation", None))
    _line("Usage principal", getattr(installation, "usage_principal", None))
    _line("Mise en service", getattr(installation, "annee_mise_en_service", None))
    _line("Description générale", getattr(installation, "description_generale", None))

    champ = getattr(installation, "champ_capteurs", None)
    if champ is not None:
        document.add_heading("Champ capteurs", level=2)
        _line("Modèle", getattr(champ, "marque_modele", None))
        _line("Nombre de capteurs", getattr(champ, "nombre_capteurs", None))
        _line("Surface totale (m²)", getattr(champ, "surface_totale_m2", None))
        _line("Azimut (°)", getattr(champ, "azimut_deg", None))
        _line("Inclinaison (°)", getattr(champ, "inclinaison_deg", None))

    stockage = getattr(installation, "stockage_solaire", None)
    if stockage is not None:
        document.add_heading("Stockage solaire", level=2)
        _line("Nombre de ballons", getattr(stockage, "nombre_ballons", None))
        _line("Volume total (L)", getattr(stockage, "volume_total_litres", None))


def _add_energy_section(document: Document, audit: Any) -> None:
    """Section dédiée aux calculs énergétiques (chantier 4)."""
    if audit is None:
        return
    energy_block = getattr(audit, "energy", None)
    if energy_block is None:
        return
    results = getattr(energy_block, "results", None)
    inputs = getattr(energy_block, "inputs", None)
    if not isinstance(results, EnergyResults):
        # Auto-calcul si des entrées ont été saisies sans déclenchement explicite.
        if inputs_have_payload(inputs):
            results = compute_energy(inputs)
            energy_block.results = results
        else:
            return

    document.add_heading("Calculs énergétiques", level=1)

    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"

    def _row(label: str, value: str) -> None:
        row = table.add_row().cells
        _set_cell_text(row[0], label, bold=True, color=OPTHELIOS_BLEU_NUIT_RGB)
        _shade_cell(row[0], OPTHELIOS_JAUNE_PALE_HEX)
        _set_cell_text(row[1], value)

    def _fmt(value, unit=""):
        if value is None:
            return "non calculé"
        return f"{value:,.1f}{(' ' + unit) if unit else ''}".replace(",", " ")

    _row("Énergie ECS annuelle", _fmt(results.energie_ecs_kwh_an, "kWh/an"))
    _row("Productible solaire retenu", _fmt(results.productible_retenu_kwh_m2_an, "kWh/m².an"))
    _row("Énergie solaire utile estimée", _fmt(results.energie_solaire_utile_kwh_an, "kWh/an"))
    _row("Productivité spécifique", _fmt(results.productivite_kwh_m2_an, "kWh/m².an"))
    if results.taux_couverture is None:
        _row("Taux de couverture solaire", "non calculé")
    elif results.taux_couverture > 1.0:
        _row(
            "Taux de couverture solaire",
            f"{results.taux_couverture * 100:.0f} % — > 100 %, vérifier saisie / dimensionnement",
        )
    else:
        _row("Taux de couverture solaire", f"{results.taux_couverture * 100:.0f} %")
    _row(
        "Ratio stockage",
        f"{results.ratio_stockage_l_m2:.0f} L/m²" if results.ratio_stockage_l_m2 is not None else "non calculé",
    )
    _row("Proposition de redimensionnement", results.proposition_redimensionnement or "indeterminé")

    if results.messages:
        document.add_heading("Commentaires", level=2)
        for msg in results.messages:
            document.add_paragraph(msg, style="List Bullet")


def _add_priority_focus_table(document: Document, payload: dict[str, Any]) -> None:
    """Diagnostic court — tableau priorisé et chiffré."""
    document.add_heading("Tableau de priorisation", level=1)
    actions = payload.get("action_plan", [])
    if not actions:
        document.add_paragraph("Aucune action prioritaire à signaler à ce stade.")
        return

    counts = {"P1": 0, "P2": 0, "P3": 0}
    for a in actions:
        if a["priorite"] in counts:
            counts[a["priorite"]] += 1

    p = document.add_paragraph()
    p.add_run("Synthèse chiffrée : ").bold = True
    p.add_run(
        f"{counts['P1']} action(s) P1 (urgentes), "
        f"{counts['P2']} action(s) P2, "
        f"{counts['P3']} action(s) P3."
    )

    # Restrict to P1 + P2 in diagnostic court.
    rows = [a for a in actions if a["priorite"] in {"P1", "P2"}]
    if not rows:
        document.add_paragraph("Aucune action P1/P2 à signaler.")
        return

    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _styled_header_row(
        table,
        ["Priorité", "Section", "Objet", "Impact", "Action"],
    )
    for item in rows:
        row = table.add_row().cells
        for cell, value in zip(
            row,
            [
                item["priorite"],
                item["section"],
                item["objet"],
                item["impact"],
                item["action_recommandee"],
            ],
        ):
            _set_cell_text(cell, _safe_str(value))


def _add_key_photos(document: Document, audit: Any, limit: int = 4) -> None:
    """Diagnostic court — photos clés légendées."""
    if audit is None:
        return
    preuves = list(getattr(audit, "preuves", []) or [])
    photos = [p for p in preuves if getattr(p, "type_preuve", None) and
              getattr(p.type_preuve, "value", str(p.type_preuve)) == "photo"]
    if not photos:
        return

    photos.sort(key=lambda p: (getattr(p, "ordre", 0), getattr(p, "preuve_id", "")))

    document.add_heading("Photos clés", level=1)
    rendered = 0
    for preuve in photos:
        if rendered >= limit:
            break
        chemin = getattr(preuve, "chemin_fichier", None)
        if not chemin:
            continue
        caption = _safe_str(getattr(preuve, "legende", "") or getattr(preuve, "commentaire", ""))
        if not _add_picture_if_exists(document, chemin, width_inches=3.5, caption=caption):
            continue
        rendered += 1
    if rendered == 0:
        document.add_paragraph("Aucune photo exploitable à ce stade.")


def _add_appendix_metadata(document: Document, metadata: Mapping[str, Any] | None = None) -> None:
    document.add_heading("Métadonnées", level=1)

    if not metadata:
        document.add_paragraph("Aucune métadonnée d'audit disponible.")
        return

    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"

    _styled_header_row(table, ["Clé", "Valeur"])

    for key, value in metadata.items():
        row = table.add_row().cells
        _set_cell_text(row[0], _safe_str(key))
        _set_cell_text(row[1], _safe_str(value))


def _resolve_mode(audit: Any) -> ModeRapport:
    studio = getattr(audit, "studio", None) if audit is not None else None
    if studio is not None and getattr(studio, "mode_rapport", None):
        return studio.mode_rapport
    if audit is not None and getattr(audit, "mode_rapport", None):
        return audit.mode_rapport
    return ModeRapport.audit_complet


def _project_address_lines(audit: Any) -> list[str]:
    if audit is None:
        return []
    projet = getattr(audit, "projet", None)
    if projet is None:
        return []
    adresse = getattr(projet, "adresse", None)
    if adresse is None:
        return []
    lines = []
    for attr in ("ligne_1", "ligne_2"):
        value = getattr(adresse, attr, None)
        if value:
            lines.append(str(value))
    cp = getattr(adresse, "code_postal", None)
    commune = getattr(adresse, "commune", None)
    cp_commune = " ".join(filter(None, [str(cp) if cp else None, commune]))
    if cp_commune:
        lines.append(cp_commune)
    return lines


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_docx_report(
    session_state: Any,
    output_path: str | Path,
    *,
    contexte_technique: Mapping[str, Any] | None = None,
    report_title: str | None = None,
    site_name: str | None = None,
    reference: str | None = None,
    audit_date: str | None = None,
    include_evidences: bool = True,
) -> Path:
    payload = build_report_data(session_state, contexte_technique=contexte_technique)
    audit = _resolve_audit(session_state)
    studio = extract_studio_from_session(session_state)
    mode = _resolve_mode(audit) if studio is None else studio.mode_rapport
    mode_label = MODE_RAPPORT_LABELS.get(mode.value, mode.value)

    if report_title is None:
        report_title = (
            "Rapport d'audit solaire thermique"
            if mode == ModeRapport.audit_complet
            else "Diagnostic court — installation solaire thermique"
        )

    # Pull metadata defaults from the audit when call-site didn't override.
    meta = getattr(audit, "meta", None) if audit is not None else None
    projet = getattr(audit, "projet", None) if audit is not None else None
    if site_name is None and projet is not None:
        site_name = getattr(projet, "operation", None)
    if reference is None and meta is not None:
        reference = getattr(meta, "numero_audit", None)
    if audit_date is None and meta is not None:
        audit_date_value = getattr(meta, "date_audit", None)
        audit_date = str(audit_date_value) if audit_date_value else None

    auditeur = getattr(meta, "auditeur", None) if meta is not None else None
    operation = getattr(projet, "operation", None) if projet is not None else None
    maitre_ouvrage = getattr(projet, "maitre_ouvrage", None) if projet is not None else None

    document = Document()
    _configure_page(document)
    _set_default_font(document)
    _set_document_language(document, "fr-FR")
    _add_header(document, report_title=report_title, reference=reference)
    _add_footer(document)

    _add_cover_page(
        document,
        report_title=report_title,
        mode_label=mode_label,
        site_name=site_name,
        address_lines=_project_address_lines(audit),
        reference=reference,
        audit_date=audit_date,
        operation=operation,
        maitre_ouvrage=maitre_ouvrage,
        auditeur=auditeur,
    )

    if mode == ModeRapport.audit_complet:
        _add_installation_section(document, audit)
        document.add_page_break()

        _add_global_assessment(document, payload)
        document.add_page_break()

        _add_executive_summary(document, payload)
        _add_expert_conclusion_section(document, payload)
        document.add_page_break()

        _add_section_summary(document, payload)
        document.add_page_break()

        _add_findings(
            document,
            payload,
            audit_for_captions=audit,
            include_evidences=include_evidences,
        )
        document.add_page_break()

        _add_action_plan(document, payload)

        _add_energy_section(document, audit)

        if studio is not None:
            document.add_page_break()
            _add_studio_sections(document, studio)

        metadata = payload.get("metadata") or {}
        if metadata:
            document.add_page_break()
            _add_appendix_metadata(document, metadata)
    else:
        # Diagnostic court — synthèse resserrée.
        _add_global_assessment(document, payload)
        document.add_paragraph("")
        _add_executive_summary(document, payload)
        _add_expert_conclusion_section(document, payload)
        document.add_page_break()

        _add_priority_focus_table(document, payload)
        document.add_page_break()

        _add_energy_section(document, audit)
        _add_key_photos(document, audit, limit=4)

        if studio is not None and (studio.selected_scenarios() or studio.note_strategique):
            document.add_heading("Orientations stratégiques", level=1)
            for sel in studio.selected_scenarios():
                scenario = SCENARIOS_BY_CODE.get(sel.code)
                title = scenario.libelle if scenario else sel.code
                horizon = f" — {scenario.horizon}" if scenario and scenario.horizon else ""
                p = document.add_paragraph()
                p.add_run(f"{title}{horizon}").bold = True
                if sel.commentaire:
                    document.add_paragraph(_safe_str(sel.commentaire))
            if studio.note_strategique:
                document.add_paragraph(_safe_str(studio.note_strategique))

        document.add_heading("Conclusion opérationnelle", level=1)
        ga = payload["global_assessment"]
        p = document.add_paragraph()
        p.add_run("Appréciation : ").bold = True
        p.add_run(_safe_str(ga.get("statut_global", "")))
        document.add_paragraph(_safe_str(ga.get("commentaire_global", "")))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
