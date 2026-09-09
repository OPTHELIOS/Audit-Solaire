"""Génère les 3 schémas de principe hydrauliques génériques de
`domain/socol_reference.SOCOL_SCHEMA_LIBRARY`, redessinés intégralement
(symboles génériques, palette OPT'HELIOS) — voir le docstring de
`domain/socol_reference.py` pour la note de propriété intellectuelle sur la
nomenclature SOCOL reprise.

Usage : python scripts/generate_schemas_socol.py
Sortie : assets/schemas_socol/*.png (300 dpi, écrase si déjà présent —
script rejouable à volonté, par ex. si la charte de couleurs évolue).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle
from matplotlib.lines import Line2D

NAVY = "#1C1E3D"
GOLD = "#F9B13A"
SKY = "#8FC4E4"
CREAM = "#FAEAB6"
BODY = "#3A3A3A"
WHITE = "#FFFFFF"

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "schemas_socol"


def _new_fig():
    fig, ax = plt.subplots(figsize=(8.5, 5.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    return fig, ax


def _pipe(ax, x1, y1, x2, y2, color=NAVY, lw=2.4, style="-"):
    ax.add_line(Line2D([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=style, zorder=2))


def _arrow(ax, x1, y1, x2, y2, color=NAVY):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>", mutation_scale=14, color=color, linewidth=0, zorder=3,
        )
    )


def _box(ax, x, y, w, h, label, fill=WHITE, edge=NAVY, fontsize=8.5, text_color=NAVY, lw=1.8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=lw, zorder=4))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize,
             color=text_color, wrap=True, zorder=5, fontweight="bold")


def _label(ax, x, y, text, fontsize=7.5, color=BODY, ha="center", style="normal"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, color=color, style=style, zorder=5)


def _pump(ax, x, y, r=1.3):
    ax.add_patch(Circle((x, y), r, facecolor=WHITE, edgecolor=NAVY, linewidth=1.8, zorder=4))
    ax.text(x, y, "P", ha="center", va="center", fontsize=7, color=NAVY, fontweight="bold", zorder=5)


def _capteurs(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=SKY, edgecolor=NAVY, linewidth=1.8, zorder=4))
    n = 4
    for i in range(1, n):
        xi = x + i * w / n
        _pipe(ax, xi, y, xi, y + h, color=NAVY, lw=0.8)
    ax.text(x + w / 2, y + h + 1.6, "Champ de capteurs solaires", ha="center", va="bottom",
            fontsize=8, color=NAVY, fontweight="bold", zorder=5)


def _title(ax, text):
    ax.text(50, 58.5, text, ha="center", va="center", fontsize=11, color=NAVY, fontweight="bold")


def _legend(ax, x, y):
    _pipe(ax, x, y, x + 4, y, color=GOLD, lw=2.4)
    _label(ax, x + 5.5, y, "circuit primaire solaire", fontsize=6.5, ha="left", color=BODY)
    _pipe(ax, x, y - 2.2, x + 4, y - 2.2, color=NAVY, lw=2.4)
    _label(ax, x + 5.5, y - 2.2, "circuit secondaire / ECS", fontsize=6.5, ha="left", color=BODY)


# --------------------------------------------------------------------------
# REF1-SSC1 : préchauffage solaire, échangeur externe, appoint en série
# --------------------------------------------------------------------------

def draw_ref1_ssc1():
    fig, ax = _new_fig()
    _title(ax, "REF1-SSC1 — Préchauffage solaire à échangeur externe, appoint en série")

    _capteurs(ax, 6, 44, 20, 8)

    # boucle primaire solaire (or)
    _pipe(ax, 8, 44, 8, 30, color=GOLD)
    _pump(ax, 8, 27, r=1.6)
    _pipe(ax, 8, 25.4, 8, 22)
    _pipe(ax, 8, 22, 34, 22, color=GOLD)
    _pipe(ax, 24, 44, 24, 34, color=GOLD)
    _pipe(ax, 24, 34, 34, 34, color=GOLD)
    _arrow(ax, 20, 22, 24, 22, color=GOLD)
    _arrow(ax, 20, 34, 24, 34, color=GOLD)

    # échangeur externe
    _box(ax, 34, 20, 9, 16, "Échangeur\nexterne\nà plaques", fill=CREAM, fontsize=8)

    # ballon stockage solaire
    _box(ax, 49, 14, 13, 26, "Ballon de\nstockage\nsolaire\n(eau sanitaire)", fill=WHITE, fontsize=8)
    _pipe(ax, 43, 34, 49, 34, color=NAVY)
    _pipe(ax, 43, 22, 49, 22, color=NAVY)
    _arrow(ax, 46, 34, 49, 34, color=NAVY)
    _arrow(ax, 46, 22, 49, 22, color=NAVY)

    # appoint en série
    _box(ax, 68, 20, 12, 12, "Appoint\n(chaudière /\nréseau chaleur)", fill=WHITE, fontsize=8)
    _pipe(ax, 62, 34, 74, 34, color=NAVY)
    _pipe(ax, 74, 34, 74, 32)
    _arrow(ax, 68, 34, 71, 34, color=NAVY)

    # distribution ECS
    _pipe(ax, 74, 20, 74, 10, color=NAVY)
    _pipe(ax, 74, 10, 90, 10, color=NAVY)
    _arrow(ax, 84, 10, 88, 10, color=NAVY)
    _label(ax, 91, 10, "ECS distribuée", fontsize=7.5, ha="left", color=NAVY)

    # eau froide
    _pipe(ax, 55, 14, 55, 6, color=SKY)
    _pipe(ax, 30, 6, 55, 6, color=SKY)
    _arrow(ax, 40, 6, 44, 6, color=SKY)
    _label(ax, 28, 6, "Eau froide", fontsize=7.5, ha="right", color=NAVY)

    _legend(ax, 6, 4)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# REF1-SSC2 : préchauffage solaire, échangeur immergé, appoint en série
# --------------------------------------------------------------------------

def draw_ref1_ssc2():
    fig, ax = _new_fig()
    _title(ax, "REF1-SSC2 — Préchauffage solaire à échangeur immergé, appoint en série")

    _capteurs(ax, 6, 44, 20, 8)

    _pipe(ax, 8, 44, 8, 30, color=GOLD)
    _pump(ax, 8, 27, r=1.6)
    _pipe(ax, 8, 25.4, 8, 22)
    _pipe(ax, 8, 22, 40, 22, color=GOLD)
    _pipe(ax, 24, 44, 24, 34, color=GOLD)
    _pipe(ax, 24, 34, 40, 34, color=GOLD)
    _arrow(ax, 20, 22, 24, 22, color=GOLD)
    _arrow(ax, 20, 34, 24, 34, color=GOLD)

    # ballon avec serpentin immergé (pas d'échangeur externe ni de 2e circulateur)
    _box(ax, 40, 12, 16, 28, "", fill=WHITE, fontsize=8)
    ax.text(48, 37, "Ballon de stockage solaire\navec échangeur serpentin\nimmergé (eau sanitaire)",
            ha="center", va="center", fontsize=7.3, color=NAVY, fontweight="bold", zorder=5)
    # serpentin schématique (sous le libellé, ne le recouvre pas)
    for i in range(3):
        yy = 15.5 + i * 4.2
        ax.add_patch(plt.matplotlib.patches.Arc((48, yy), 9, 3.4, theta1=0, theta2=180,
                                                  edgecolor=GOLD, linewidth=1.6, zorder=5))

    _box(ax, 68, 18, 12, 12, "Appoint\n(chaudière /\nréseau chaleur)", fill=WHITE, fontsize=8)
    _pipe(ax, 56, 32, 74, 32, color=NAVY)
    _arrow(ax, 66, 32, 70, 32, color=NAVY)
    _pipe(ax, 74, 32, 74, 30)

    _pipe(ax, 74, 18, 74, 10, color=NAVY)
    _pipe(ax, 74, 10, 90, 10, color=NAVY)
    _arrow(ax, 84, 10, 88, 10, color=NAVY)
    _label(ax, 91, 10, "ECS distribuée", fontsize=7.5, ha="left", color=NAVY)

    _pipe(ax, 44, 12, 44, 6, color=SKY)
    _pipe(ax, 26, 6, 44, 6, color=SKY)
    _arrow(ax, 34, 6, 38, 6, color=SKY)
    _label(ax, 24, 6, "Eau froide", fontsize=7.5, ha="right", color=NAVY)

    _legend(ax, 6, 4)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# REF3-SSC1 : production ECS instantanée sur stockage eau technique
# --------------------------------------------------------------------------

def draw_ref3_ssc1():
    fig, ax = _new_fig()
    _title(ax, "REF3-SSC1 — Production ECS instantanée sur stockage en eau technique")

    _capteurs(ax, 6, 44, 20, 8)

    _pipe(ax, 8, 44, 8, 30, color=GOLD)
    _pump(ax, 8, 27, r=1.6)
    _pipe(ax, 8, 25.4, 8, 22)
    _pipe(ax, 8, 22, 34, 22, color=GOLD)
    _pipe(ax, 24, 44, 24, 34, color=GOLD)
    _pipe(ax, 24, 34, 34, 34, color=GOLD)
    _arrow(ax, 20, 22, 24, 22, color=GOLD)
    _arrow(ax, 20, 34, 24, 34, color=GOLD)

    _box(ax, 34, 20, 9, 16, "Échangeur\nexterne\nà plaques", fill=CREAM, fontsize=8)

    # ballon eau technique (boucle fermee, pas d'eau sanitaire dedans)
    _box(ax, 49, 16, 13, 24, "Ballon de\nstockage\nEAU TECHNIQUE\n(boucle fermée)", fill=WHITE, fontsize=7.8)
    _pipe(ax, 43, 34, 49, 34, color=NAVY)
    _pipe(ax, 43, 22, 49, 22, color=NAVY)
    _arrow(ax, 46, 34, 49, 34, color=NAVY)
    _arrow(ax, 46, 22, 49, 22, color=NAVY)

    _pump(ax, 66, 34, r=1.4)
    _pipe(ax, 62, 34, 64.6, 34, color=NAVY)
    _pipe(ax, 67.4, 34, 72, 34, color=NAVY)

    # échangeur ECS instantané
    _box(ax, 72, 20, 11, 16, "Échangeur ECS\nà production\nINSTANTANÉE", fill=CREAM, fontsize=7.8)
    _pipe(ax, 72, 22, 62, 22, color=NAVY)
    _arrow(ax, 68, 22, 65, 22, color=NAVY)

    _pipe(ax, 77, 20, 77, 10, color=NAVY)
    _pipe(ax, 77, 10, 92, 10, color=NAVY)
    _arrow(ax, 86, 10, 90, 10, color=NAVY)
    _label(ax, 93, 10, "ECS distribuée\n(pointe de soutirage)", fontsize=7, ha="left", color=NAVY)

    _pipe(ax, 82, 20, 82, 14, color=SKY)
    _pipe(ax, 60, 14, 82, 14, color=SKY)
    _pipe(ax, 60, 14, 60, 20)
    _arrow(ax, 70, 14, 74, 14, color=SKY)
    _label(ax, 58, 14, "Eau froide", fontsize=7.5, ha="right", color=NAVY)

    _legend(ax, 6, 4)
    fig.tight_layout()
    return fig


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for code, draw_fn, filename in [
        ("REF1-SSC1", draw_ref1_ssc1, "ref1_ssc1_echangeur_externe.png"),
        ("REF1-SSC2", draw_ref1_ssc2, "ref1_ssc2_echangeur_immerge.png"),
        ("REF3-SSC1", draw_ref3_ssc1, "ref3_ssc1_eau_technique.png"),
    ]:
        fig = draw_fn()
        out_path = OUT_DIR / filename
        fig.savefig(out_path, dpi=300, facecolor="white")
        plt.close(fig)
        print(f"[generate_schemas_socol] {code} -> {out_path}")


if __name__ == "__main__":
    main()
