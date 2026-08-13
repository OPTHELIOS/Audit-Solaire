# Audit-Solaire — état du dossier après intervention

Ce dossier contient une reconstruction complète et fonctionnelle du projet
`OPTHELIOS/Audit-Solaire`, avec tous les correctifs déjà appliqués. Vérifié :
la chaîne d'imports complète se charge sans erreur avec le vrai catalogue de
contrôles (80 contrôles réels chargés, 69 applicables pour un audit vide).

Le dossier `audit-solaire-sharepoint/` présent à côté est une livraison
intermédiaire antérieure (mêmes fichiers de correctifs, sans le reste du
projet) — il peut être ignoré/supprimé, tout son contenu est repris ici.

## Ce qui a été corrigé (résumé — détail technique complet plus bas)

1. `audit.meta.audit_id` manquant sur le modèle → ajouté. Sans ça, tout ajout
   de preuve plantait immédiatement.
2. Modèle `Preuve` incohérent avec le code qui le remplissait → champs
   alignés (`fichier_path`, `nom_original`, `date_capture`, `auteur`). Le
   chemin du fichier n'était jusque-là jamais réellement conservé.
3. Deux définitions différentes et incompatibles de `TypePreuve` → unifiées.
4. `constat.preuves_ids` (typo) → `constat.preuve_ids`. Rattacher une preuve
   à un contrôle plantait systématiquement.
5. Les preuves ajoutées depuis "Preuves et annexes" n'apparaissaient jamais
   dans le rapport DOCX/Markdown (deux circuits déconnectés) → une preuve
   rattachée à un contrôle alimente maintenant aussi `constat.photos`.
6. Upload mono-fichier incohérent sur "Preuves et annexes" → multi-fichiers.
7. Photos non compressées → redimensionnement automatique (1600 px, JPEG 85)
   à l'upload, `Pillow` ajouté explicitement aux dépendances.
8. Conclusion experte (page Synthèse) jamais réellement persistée dans
   l'audit → écrite dans `audit.synthese.conclusion_generale` et sauvegardée.
9. **Sauvegarde automatique** : remplacement du flux OneDrive personnel
   (connexion interactive, "device code") par une authentification "app-only"
   Microsoft Graph vers un site SharePoint partagé — voir la section dédiée
   ci-dessous, c'est la partie qui nécessite une action de ta part.
10. Les fichiers de preuves (photos, PDF) sont désormais aussi envoyés dans
    le cloud, pas seulement sauvegardés localement.

## Prochaine étape technique : mettre ce dossier sous Git et le pousser sur GitHub

Ce dossier n'est pas (encore) un dépôt Git. Pour le relier à
`OPTHELIOS/Audit-Solaire` et pousser ces correctifs :

```
cd "C:\Users\moran\OneDrive - opthelios.fr\Bureau\APPLI AUDIT via Claude"
git init
git remote add origin https://github.com/OPTHELIOS/Audit-Solaire.git
git fetch origin
git checkout -b fix/sauvegarde-auto-et-bugs main --track origin/main
```

Cette dernière commande va probablement signaler des conflits ou des
fichiers "untracked" puisque ce dossier a été reconstruit à côté plutôt que
cloné puis modifié. Le plus sûr et le plus simple, si tu as un doute :

1. Clone le vrai dépôt dans un dossier temporaire séparé :
   `git clone https://github.com/OPTHELIOS/Audit-Solaire.git C:\temp\Audit-Solaire`
2. Copie par-dessus les fichiers listés dans "Fichiers concernés" ci-dessous
   depuis ce dossier-ci vers `C:\temp\Audit-Solaire`.
3. Dans `C:\temp\Audit-Solaire` : `git status` pour vérifier ce qui a changé,
   `git add -A`, `git commit -m "Correctifs bugs + sauvegarde automatique SharePoint"`,
   `git push`.

### Fichiers concernés (nouveaux ou modifiés par rapport au dépôt GitHub actuel)

Nouveaux : `services/sharepoint_auth.py`, `repositories/sharepoint_repository.py`.

Modifiés : `domain/models.py`, `services/evidence_service.py`,
`services/autosave_service.py` (nouveau en réalité, n'existait pas avant ces
correctifs), `ui/state.py`, `ui/pages/_02_controles.py`,
`ui/pages/_03_preuves.py`, `ui/pages/_05_synthese.py`, `app.py`,
`requirements.txt`.

Inchangés (présents ici pour que le dossier soit complet et testable tel
quel, mais identiques au dépôt GitHub) : tout le reste.

Devenus obsolètes une fois la bascule faite (à supprimer, plus utilisés par
`app.py`) : `services/onedrive_auth.py`, `repositories/onedrive_repository.py`.
Existaient déjà comme code mort avant mon intervention (non liés à `app.py`,
non modifiés ici) : `services/control_service.py`, `services/report_service.py`,
`services/scoring_service.py`, `ui/pages/_10_synthese.py`,
`ui/pages/_11_rapport.py`, `repositories/audit_repository.py`.

## Sauvegarde automatique — ce qu'il te reste à faire

J'ai tenté de faire l'inscription d'application directement via le
navigateur (Claude dans Chrome), mais Microsoft bloque la requête
automatisée sur ses pages de connexion admin ("The request is blocked" —
protection anti-bot côté Microsoft, pas contournable depuis mon côté). Il
faut donc faire ces étapes toi-même :

### 1. Créer un espace de stockage partagé

Crée une équipe Teams "Audits OPT'HELIOS" (ou réutilise un site SharePoint
existant) — ça crée automatiquement une bibliothèque de documents.

### 2. Inscrire l'application dans Azure AD (Entra ID)

Sur [entra.microsoft.com](https://entra.microsoft.com) (ou portal.azure.com
→ Microsoft Entra ID) :

1. **Inscriptions d'applications** → **Nouvelle inscription**. Nom libre,
   ex. "Audit-Solaire-Backend". Note l'**ID d'application (client)** et
   l'**ID de l'annuaire (locataire)**.
2. **Certificats et secrets** → **Nouveau secret client**. Copie la valeur
   immédiatement (elle n'est plus jamais réaffichée).
3. **Autorisations API** → **Ajouter une autorisation** → **Microsoft
   Graph** → **Autorisations d'application** (pas "déléguées") → coche
   `Sites.Selected`. Valide.
4. **Accorder le consentement administrateur pour [ton organisation]**
   (nécessite d'être admin M365, ou de le faire faire par un admin).

### 3. Autoriser l'application sur le site SharePoint créé à l'étape 1

`Sites.Selected` ne donne accès à rien tant qu'on ne l'autorise pas
explicitement sur un site précis. Via [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer)
connecté avec un compte admin :

```
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
Content-Type: application/json

{
  "roles": ["write"],
  "grantedToIdentities": [{
    "application": {
      "id": "{client-id-de-l-etape-2}",
      "displayName": "Audit-Solaire-Backend"
    }
  }]
}
```

Pour trouver `{site-id}` : dans Graph Explorer, exécute
`GET https://graph.microsoft.com/v1.0/sites/{tondomaine}.sharepoint.com:/sites/{NomDuSite}`
— la réponse contient le champ `id`.

### 4. Renseigner les secrets dans l'appli Streamlit

Dans `.streamlit/secrets.toml` (en local) ou dans les secrets du service
d'hébergement (Streamlit Community Cloud → Settings → Secrets, ou équivalent) :

```toml
[microsoft_app]
tenant_id = "{ID de l'annuaire, étape 2}"
client_id = "{ID d'application, étape 2}"
client_secret = "{valeur du secret, étape 2}"
site_id = "{site-id, étape 3}"
root_folder = "AuditsOPTHELIOS"
```

### 5. Vérifier

Ouvre l'appli, va sur "Infos audit" : le message doit passer de
l'avertissement à "☁️ Sauvegarde automatique active". Ajoute un dossier et
une photo, vérifie dans SharePoint que
`AuditsOPTHELIOS/{audit_id}/audit.json`, `metadata.json` et le fichier photo
sous `evidences/photos/` apparaissent bien.

Si un écran ne correspond pas à ce qui est décrit ici (Microsoft change
régulièrement ces interfaces), colle-moi une capture ou le texte affiché et
je t'aide à identifier le bon bouton.

## Correctifs du 13/08/2026 (suite à la mise en service)

11. **Photos de "Contrôles techniques" désormais aussi sauvegardées dans le
    cloud.** Jusque-là, seules les preuves ajoutées depuis "Preuves et
    annexes" étaient envoyées vers SharePoint ; celles ajoutées directement
    sur un point de contrôle restaient uniquement locales.
    (`services/evidence_service.py::backup_control_evidence_file`,
    appelée depuis `ui/pages/_02_controles.py`.)
12. **Nommage lisible des dossiers SharePoint.** Le dossier créé pour chaque
    audit portait le nom brut de `audit.meta.audit_id` (un UUID illisible
    dans la navigation SharePoint, ex. `33a47ec8-8d49-489f-b7db-8e...`). Il
    porte désormais un nom du type `Nom-Operation-xxxxxxxx` (slug du nom
    d'opération ou, à défaut, de la commune, + suffixe technique pour
    garantir l'unicité), calculé une seule fois et mémorisé sur
    `audit.meta.dossier_cloud`. Les audits déjà sauvegardés avant ce
    correctif gardent leur dossier existant (nommé par UUID) : ils
    continuent de fonctionner normalement, seuls les nouveaux audits (ou une
    prochaine sauvegarde d'un audit qui n'a pas encore de `dossier_cloud`)
    bénéficient du nouveau nommage.
    (`repositories/sharepoint_repository.py::get_cloud_folder_name`.)
13. **Enregistrement par section plutôt que par point de contrôle.** La page
    "Contrôles techniques" imposait de cliquer "Enregistrer" après chaque
    point, ce qui interrompait la saisie terrain. Chaque section a
    maintenant un seul formulaire et un seul bouton "Enregistrer la
    section" : tu peux remplir tous les points d'une section puis valider en
    une fois. La réinitialisation d'un point reste possible individuellement,
    regroupée dans un petit expander "Réinitialiser un point de cette
    section" en bas de chaque section (action rare, volontairement séparée
    du flux principal de saisie).
    (`ui/pages/_02_controles.py`.)

## Nouveautés du 13/08/2026 (dossier d'audit complet)

14. **Nouvelle page "Documents fournis"** (`ui/pages/_07_documents.py`,
    `services/documents_service.py`, `domain/documents_catalog.py`) : suivi
    de 10 documents administratifs/techniques usuels (DOE, schémas
    hydraulique/électrique, garanties, contrat de maintenance, PV de
    réception...), avec case "fourni", commentaire libre et upload de
    fichier par document, sauvegardés en cloud comme les autres pièces.
15. **Page de garde et signature dans le rapport DOCX** : le rapport a
    maintenant une vraie page de garde (logo, titre, nom du site, photo de
    couverture si renseignée) suivie d'un saut de page, et se termine par un
    bloc "Validation" (auditeur, date, ligne de signature manuscrite). La
    photo de couverture se choisit sur la page Dossier, section dédiée
    (distincte des preuves de "Preuves et annexes").
    (`domain/docx_service.py`, `domain/models.py::Projet.photo_couverture_path`.)
16. **Dupliquer un audit** (page Infos audit) : crée un nouvel audit à
    partir d'un audit chargé, en reprenant l'installation technique et le
    maître d'ouvrage/exploitant/mainteneur, mais en remettant à zéro
    l'adresse, les constats et les preuves — utile pour un site similaire du
    même parc. (`services/audit_service.py::duplicate_audit`.)
17. **Checklist terrain imprimable** (page Export, onglet dédié) : liste
    condensée DOCX de tous les points de contrôle applicables (pas
    seulement les non-conformités), avec cases vides à remplir à la main
    pendant la visite, avant la saisie détaillée dans l'appli.
    (`domain/docx_service.py::build_checklist_docx`.)
18. **Recherche transversale + progression globale permanente** : champ de
    recherche par mot-clé (ID, libellé, observation...) sur la page
    Contrôles techniques, et barre de progression de l'audit visible dans
    la barre latérale sur toutes les pages (plus seulement sur Contrôles
    techniques). (`app.py`, `ui/pages/_02_controles.py`.)
19. **Export Excel du plan d'actions** (page Export, onglet "Exports
    techniques") : fichier .xlsx avec priorité/section/action recommandée
    et colonnes vides Échéance/Responsable/Statut à compléter côté suivi de
    chantier. Nécessite `openpyxl` (ajouté à requirements.txt).
20. **Export PDF direct** (page Export, onglet "Livrable DOCX") : convertit
    le dernier DOCX généré en PDF en pilotant Microsoft Word installé
    localement (`docx2pdf`, ajouté à requirements.txt). Fonctionne
    uniquement en local sur Windows/Mac avec Word installé — pas sur un
    hébergement cloud sans Word ; message d'erreur clair sinon.
21. **Tests automatisés** (voir section dédiée plus bas) et **historique des
    versions SharePoint documenté** (voir section dédiée plus bas).

22. **Nouvelle page "Mesures et comparaison"** (`ui/pages/_08_mesures.py`,
    `services/releves_service.py`, `services/comparison_service.py`,
    `domain/releves_catalog.py`) :
    - Relevés de mesure horodatés (température, pression, débit,
      concentration antigel, énergie...), avec des modèles usuels
      pré-remplis ou un relevé entièrement personnalisé, rattachables à un
      point de contrôle (optionnel). Liste des relevés avec suppression
      individuelle.
    - Comparaison avec un audit antérieur du même site (choisi dans la liste
      des audits sauvegardés) : taux de complétion, taux de conformité,
      non-conformités critiques/majeures, et relevés de mesure communs
      (rapprochés par libellé identique) avec l'écart affiché.
    - Lecture seule : la comparaison ne modifie ni ne sauvegarde l'audit
      antérieur chargé, elle sert uniquement à l'affichage.

## Historique des versions SharePoint (filet de sécurité en cas d'erreur)

Les bibliothèques de documents SharePoint activent le versioning par défaut
(chaque écriture d'`audit.json` crée une nouvelle version, les anciennes
restent accessibles). Pour vérifier/l'activer sur ta bibliothèque :

1. Ouvre la bibliothèque de documents du site (celle où apparaît le dossier
   `AuditsOPTHELIOS`) dans le navigateur.
2. Roue crantée (Paramètres) → **Paramètres de la bibliothèque** → sous
   "Paramètres généraux", **Paramètres de contrôle des versions**.
3. Vérifie que "Créer une version à chaque modification d'un fichier dans
   cette bibliothèque de documents ?" est sur **Oui**. Par défaut c'est déjà
   le cas sur un site créé via Teams/SharePoint moderne.

Pour restaurer une version antérieure d'un audit (ex. après une mauvaise
manipulation ou une sauvegarde automatique malvenue) :

1. Dans la bibliothèque, navigue jusqu'au fichier `audit.json` du dossier
   concerné (`AuditsOPTHELIOS/{nom-du-dossier}/audit.json`).
2. Clic droit → **Historique des versions**.
3. Sélectionne une version antérieure → **Restaurer**.

L'application elle-même ne gère pas de bouton "restaurer" : ça se fait
directement dans SharePoint, en dehors de l'appli, ce qui évite de risquer
d'écraser une bonne version par erreur depuis l'appli elle-même.

## Tests automatisés

Un dossier `tests/` (pytest) couvre le modèle de données, le cycle de vie
d'un point de contrôle, l'écriture des preuves et la génération du rapport.
Volontairement, les appels réseau vers SharePoint (`save_audit`,
`load_audit`, `upload_evidence_file`) ne sont PAS testés automatiquement
(nécessiteraient un vrai site ou un mock HTTP complet) : seule la partie
pure (`get_cloud_folder_name`, `_slugify`) l'est. Le reste continue de se
vérifier manuellement dans l'appli (voir section "Vérifier" plus haut).

Pour lancer les tests, depuis la racine du projet :

```
pip install -r requirements-dev.txt
pytest
```

## Ce qui n'a pas été fait (choix ouverts, pas des bugs)

- Renouvellement du secret client à son expiration (24 mois par exemple) :
  à surveiller, sans quoi la sauvegarde automatique s'arrête silencieusement
  (l'appli continue de fonctionner en local, juste sans sauvegarde cloud).
- Nettoyage du code mort listé plus haut (aucun impact fonctionnel
  actuellement, ces fichiers ne sont importés par aucune page active).
- Renommage automatique, dans SharePoint, du dossier `33a47ec8-8d49-...`
  déjà créé lors du test initial : il continuera de fonctionner tel quel
  (nommage par UUID), rien ne le distingue fonctionnellement des nouveaux
  dossiers nommés lisiblement. Si tu veux l'harmoniser, tu peux même le
  renommer à la main directement dans SharePoint : l'appli retrouve et
  recharge toujours un audit par le nom réel de son dossier (pas par un
  identifiant technique caché), donc un renommage manuel ne casse rien.
