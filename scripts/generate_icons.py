#!/usr/bin/env python3
"""Genere toutes les icones de l'appli a partir d'une image source unique.

Source par defaut : assets/icons/source/icone-opt-audit.jpg — l'icone
"Opt'Audit" retenue en sept. 2026 parmi trois propositions (carre marine a
coins arrondis et rebord en relief sur fond gris, soleil orange, mention
"Opt'Audit" en bas, retiree par defaut).

POURQUOI UN SCRIPT plutot que des fichiers retouches a la main : chaque
plateforme impose ses propres contraintes, et l'image source n'en respecte
aucune telle quelle.

- iOS (apple-touch-icon.png, 180 px) applique LUI-MEME son masque arrondi.
  Une image deja arrondie sur fond blanc donnerait des coins blancs visibles
  a l'interieur du masque d'iOS : il faut un carre marine plein jusqu'aux
  bords, et sans transparence (iOS remplace la transparence par du noir).
- Android (icone "maskable") peut rogner l'icone en cercle, en goutte, en
  carre arrondi... selon le lanceur. Seul un disque central de 80 % du
  diametre est garanti visible : l'embleme doit y tenir entierement.
- Onglet du navigateur (favicon, 16 et 32 px) : a cette taille, le texte et
  les pictogrammes internes deviennent illisibles ; seul l'embleme, cadre
  serre, reste reconnaissable.

Le script redetecte a chaque execution le carre marine, la couleur de fond
et la position du texte : une nouvelle version de l'image source, meme de
dimensions differentes, se traite en relancant simplement le script.

Usage :
    python scripts/generate_icons.py                        # sans texte (defaut)
    python scripts/generate_icons.py --variante avec-texte
    python scripts/generate_icons.py --sortie <dossier>     # sans toucher assets/
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
SOURCE_DEFAUT = REPO / "assets" / "icons" / "source" / "icone-opt-audit.jpg"
SORTIE_DEFAUT = REPO / "assets" / "icons"

# Ecart a la couleur de fond au-dela duquel un pixel est du "contenu"
# (embleme, halo, texte) plutot que du fond marine. Calibre pour que le halo
# lumineux autour du soleil soit compte comme contenu.
SEUIL_CONTENU = 90

# Rayon (en fraction du cote) du disque dans lequel l'embleme doit tenir pour
# la version maskable. La norme garantit 0,40 ; 0,38 laisse de la place au
# halo, dont la partie la plus diffuse est sous le seuil de detection.
RAYON_SUR_MASKABLE = 0.38


def _est_marine(c) -> bool:
    r, g, b = c[:3]
    return r < 70 and g < 70 and b < 110 and b > r


def _ecart(c, ref) -> int:
    return sum(abs(c[i] - ref[i]) for i in range(3))


def _est_contenu(c, fond) -> bool:
    """Pixel appartenant a l'embleme, au halo ou au texte ? Il doit s'ecarter
    du fond ET etre soit colore, soit clair. Les gris sombres et peu satures
    sont exclus : ce sont les restes d'un rebord en relief ou d'une ombre
    portee (constate sur une image source a effet 3D), jamais de l'embleme.
    Sans ce filtre, un liseré gris invisible a l'oeil faussait le centrage
    et reduisait inutilement la version maskable."""
    if _ecart(c, fond) <= SEUIL_CONTENU:
        return False
    haut, bas = max(c[:3]), min(c[:3])
    saturation = (haut - bas) / haut if haut else 0.0
    return saturation > 0.25 or haut > 170


def detecter_carre(im: Image.Image):
    """Boite du carre marine, couleur de fond et rayon approximatif des coins."""
    px = im.load()
    w, h = im.size
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if _est_marine(px[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        raise SystemExit("Aucun carre marine detecte dans l'image source.")
    gauche, droite, haut, bas = min(xs), max(xs), min(ys), max(ys)

    # Couleur de fond : mediane d'une bande interieure, loin de l'embleme.
    milieu = (haut + bas) // 2
    echantillon = [
        px[x, y]
        for y in range(milieu - 40, milieu + 40)
        for x in range(gauche + 8, gauche + 28)
    ]
    fond = tuple(int(statistics.median(c[i] for c in echantillon)) for i in range(3))

    # Rayon des coins : ou commence le marine sur la ligne du haut.
    ligne = haut + 1
    premier = next((x for x in range(gauche, droite) if _est_marine(px[x, ligne])), gauche)
    return (gauche, haut, droite, bas), fond, max(premier - gauche, 0)


def carre_plein(im, boite, fond, rayon, marge=12) -> Image.Image:
    """Carre marine plein : coins arrondis et fond blanc remplaces par du marine."""
    gauche, haut, droite, bas = boite
    zone = im.crop((gauche + marge, haut + marge, droite - marge + 1, bas - marge + 1))
    w, h = zone.size
    masque = Image.new("L", (w, h), 0)
    # Rayon volontairement tres agrandi (x 1,35). Le rayon detecte (premier
    # pixel marine de la ligne du haut) sous-estime les coins a courbure
    # continue facon iOS, qui mordent plus loin dans le carre qu'un arc de
    # cercle : un masque au rayon detecte laissait des croissants de fond
    # blanc visibles (constate sur une image source). Sans risque pour
    # l'embleme, toujours loin des coins.
    ImageDraw.Draw(masque).rounded_rectangle(
        (0, 0, w - 1, h - 1), radius=max(round(rayon * 1.35) - marge, 0), fill=255
    )
    cote = max(w, h)
    toile = Image.new("RGB", (cote, cote), fond)
    toile.paste(zone, ((cote - w) // 2, (cote - h) // 2), masque)
    return toile


def _blocs_de_contenu(im, fond):
    """Bandes horizontales contenant du contenu : [(debut, fin), ...]."""
    px = im.load()
    w, h = im.size
    blocs, debut = [], None
    for y in range(h):
        plein = any(_est_contenu(px[x, y], fond) for x in range(0, w, 2))
        if plein and debut is None:
            debut = y
        elif not plein and debut is not None:
            blocs.append((debut, y - 1))
            debut = None
    if debut is not None:
        blocs.append((debut, h - 1))
    # Bandes de 1 a 3 lignes : bruit de compression JPEG, pas du contenu.
    return [b for b in blocs if b[1] - b[0] >= 3]


def sans_texte(carre, fond):
    """Retire la mention texte situee sous l'embleme, puis recentre
    verticalement l'embleme, que la place reservee au texte decalait vers le
    haut. On repeint le texte plutot que de decouper l'embleme : le halo
    lumineux, qui s'estompe progressivement, reste ainsi intact, sans arete
    de decoupe visible."""
    blocs = _blocs_de_contenu(carre, fond)
    principal = max(blocs, key=lambda b: b[1] - b[0])
    cote = carre.size[0]
    resultat = carre.copy()
    dessin = ImageDraw.Draw(resultat)
    retires = []
    for debut, fin in blocs:
        if debut > principal[1]:
            haut = max(debut - 4, principal[1] + 2)
            bas = min(fin + 4, cote - 1)
            dessin.rectangle((0, haut, cote, bas), fill=fond)
            retires.append((haut, bas))
    # Recentrage sur TOUT le contenu conserve (embleme et eventuels
    # pictogrammes isoles au-dessus), pas sur le seul bloc principal : sinon
    # un pictogramme separe, place en haut, serait ignore du calcul et
    # l'ensemble se retrouverait trop bas.
    haut_contenu = min(b[0] for b in blocs if b[0] <= principal[1])
    decalage = round(cote / 2 - (haut_contenu + principal[1]) / 2)
    recentre = Image.new("RGB", (cote, cote), fond)
    recentre.paste(resultat, (0, decalage))
    return recentre, retires, decalage


def _etendue(img, fond):
    """Distance maximale au centre du contenu : radiale, et par axe."""
    px = img.load()
    cote = img.size[0]
    c = cote / 2
    radiale = axiale = 0.0
    for y in range(0, cote, 2):
        for x in range(0, cote, 2):
            if _est_contenu(px[x, y], fond):
                dx, dy = abs(x - c), abs(y - c)
                radiale = max(radiale, (dx * dx + dy * dy) ** 0.5)
                axiale = max(axiale, dx, dy)
    return radiale, axiale


def version_maskable(img, fond, taille=512):
    """Version Android "maskable" : l'embleme entier tient dans le disque
    central garanti visible, quel que soit le masque applique par le lanceur."""
    cote = img.size[0]
    radiale, _ = _etendue(img, fond)
    facteur = min(1.0, RAYON_SUR_MASKABLE * cote / radiale) if radiale else 1.0
    reduit = img.resize((round(cote * facteur),) * 2, Image.LANCZOS)
    toile = Image.new("RGB", (cote, cote), fond)
    decalage = (cote - reduit.size[0]) // 2
    toile.paste(reduit, (decalage, decalage))
    return toile.resize((taille, taille), Image.LANCZOS), facteur


def cadre_serre(img, fond, marge=0.04):
    """Carre centre au plus pres de l'embleme, pour les favicons : a 16 px,
    chaque pixel de fond marine gaspille est un pixel d'embleme en moins."""
    cote = img.size[0]
    _, axiale = _etendue(img, fond)
    demi = min(cote / 2, axiale * (1 + marge))
    c = cote / 2
    return img.crop((round(c - demi), round(c - demi), round(c + demi), round(c + demi)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAUT)
    parser.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    parser.add_argument(
        "--variante",
        choices=("sans-texte", "avec-texte"),
        default="sans-texte",
        help="Icones d'ecran d'accueil (iOS et Android). Les favicons et la "
        "version maskable sont TOUJOURS sans texte : illisible a leur taille, "
        "ou rogne par le masque.",
    )
    parser.add_argument(
        "--marge",
        type=int,
        default=12,
        help="Pixels rognes a l'interieur du carre detecte. A augmenter si "
        "l'image source a un rebord en relief (effet 3D) qui resterait "
        "visible comme un liseré le long des bords.",
    )
    args = parser.parse_args()

    im = Image.open(args.source).convert("RGB")
    boite, fond, rayon = detecter_carre(im)
    carre = carre_plein(im, boite, fond, rayon, marge=args.marge)
    epure, retires, decalage = sans_texte(carre, fond)
    ecran = carre if args.variante == "avec-texte" else epure

    args.sortie.mkdir(parents=True, exist_ok=True)

    def enregistrer(img, nom, taille):
        img.resize((taille, taille), Image.LANCZOS).save(args.sortie / nom, optimize=True)

    enregistrer(ecran, "icon-512.png", 512)
    enregistrer(ecran, "icon-192.png", 192)
    enregistrer(ecran, "apple-touch-icon.png", 180)
    maskable, facteur = version_maskable(epure, fond)
    maskable.save(args.sortie / "icon-maskable-512.png", optimize=True)
    serre = cadre_serre(epure, fond)
    enregistrer(serre, "favicon-32.png", 32)
    enregistrer(serre, "favicon-16.png", 16)
    serre.resize((256, 256), Image.LANCZOS).save(
        args.sortie / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)]
    )

    print(f"Source            : {args.source.name} {im.size[0]}x{im.size[1]}")
    print(f"Carre detecte     : {boite}, fond #%02X%02X%02X, coins ~{rayon} px" % fond)
    print(f"Texte retire      : lignes {retires or 'aucune'} ; embleme recentre de {decalage:+d} px")
    print(f"Variante accueil  : {args.variante}")
    print(f"Maskable          : embleme reduit a {facteur:.0%} pour tenir dans le disque garanti")
    print(f"Fichiers ecrits dans {args.sortie} :")
    for nom in ("apple-touch-icon.png", "icon-192.png", "icon-512.png",
                "icon-maskable-512.png", "favicon-16.png", "favicon-32.png", "favicon.ico"):
        print(f"  {nom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
