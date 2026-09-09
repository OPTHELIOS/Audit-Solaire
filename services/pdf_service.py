"""Conversion DOCX -> PDF, portable entre poste local (Windows/Mac avec
Microsoft Word) et hébergement cloud Linux (Streamlit Community Cloud, pas
de Word disponible).

Deux méthodes essayées dans l'ordre :
1. `docx2pdf` (pilote Word en arrière-plan) — fonctionne seulement si Word
   est installé sur la machine qui exécute Streamlit (poste local
   Windows/Mac). N'est même pas installé sur Linux (voir requirements.txt,
   marqueur `sys_platform`).
2. LibreOffice en ligne de commande (`soffice --headless --convert-to pdf`)
   — fonctionne sur Linux si le paquet système `libreoffice` est installé
   (voir packages.txt, lu automatiquement par Streamlit Community Cloud).

Si aucune des deux n'est disponible, lève `PdfConversionError` avec un
message clair plutôt que de planter silencieusement.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PdfConversionError(RuntimeError):
    pass


def _convert_with_word(docx_path: Path, pdf_path: Path) -> bool:
    try:
        from docx2pdf import convert
    except ImportError:
        return False

    try:
        convert(str(docx_path), str(pdf_path))
        return pdf_path.exists()
    except Exception:
        return False


def _convert_with_libreoffice(docx_path: Path, pdf_path: Path) -> bool:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return False

    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf_path.parent),
                str(docx_path),
            ],
            check=True,
            timeout=120,
            capture_output=True,
        )
    except Exception:
        return False

    # LibreOffice nomme toujours le fichier de sortie d'après le nom du DOCX
    # source (dans le dossier --outdir) ; on le déplace vers le chemin
    # `pdf_path` attendu par l'appelant si les deux diffèrent.
    produced = docx_path.with_suffix(".pdf")
    if produced.exists() and produced != pdf_path:
        produced.replace(pdf_path)

    return pdf_path.exists()


def convert_docx_to_pdf(docx_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    """Convertit un DOCX en PDF. Retourne le chemin du PDF généré, ou lève
    `PdfConversionError` si ni Word ni LibreOffice ne sont disponibles sur
    cette machine."""
    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path) if pdf_path else docx_path.with_suffix(".pdf")

    if _convert_with_word(docx_path, pdf_path):
        return pdf_path

    if _convert_with_libreoffice(docx_path, pdf_path):
        return pdf_path

    raise PdfConversionError(
        "Impossible de convertir en PDF : ni Microsoft Word (via docx2pdf, en local) ni "
        "LibreOffice (commande `soffice`, en hébergement cloud) ne sont disponibles sur "
        "cette machine."
    )
