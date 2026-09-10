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
23. **Bug réel corrigé : impossible de recharger un audit avec un point
    classé "Information".** Sur la page "Contrôles techniques", le
    sélecteur "Criticité retenue" propose 4 niveaux (`domain/control_catalog.py`
    : critique, majeure, mineure, information), mais le modèle de
    sauvegarde (`domain/models.py::Criticite`, utilisé par
    `ConstatControle.criticite`/`criticite_finale`) n'en acceptait que 3
    (il manquait "information"). Résultat : choisir "Information" pour un
    point s'enregistrait sans erreur en session (Python ne revalide pas une
    simple assignation de champ), mais l'audit devenait ensuite impossible
    à recharger — `Audit.model_validate(...)` rejetait la valeur
    "information" comme invalide, avec une erreur du type *"Input should
    be 'mineure', 'majeure' or 'critique'"*. Corrigé en ajoutant
    `information` à `domain/models.py::Criticite`, pour que les deux
    énumérations restent alignées. Les audits déjà sauvegardés avec un
    point "Information" (dont le JSON contient déjà la bonne valeur)
    redeviennent chargeables sans aucune manipulation supplémentaire.
    `domain/report_service.py` (tri des constats par criticité, libellés du
    rapport) a aussi été mis à jour pour traiter explicitement ce 4e
    niveau. Test de non-régression ajouté :
    `tests/test_models.py::test_criticite_information_survives_json_roundtrip`.
24. **Bug réel corrigé : génération du DOCX plantait avec `Erreur lors de la
    génération du DOCX : 'impact'`.** `domain/docx_service.py::_add_action_plan`
    lit `item["impact"]` pour remplir la colonne "Impact" du tableau du plan
    d'actions, mais `domain/control_service.py::build_action_plan` (et
    `extract_findings`, dont il dépend) ne produisaient jamais cette clé —
    le DOCX plantait donc systématiquement dès qu'un audit contenait au
    moins un constat non conforme/non présent/non vérifiable. Corrigé en
    reprenant l'impact par défaut du catalogue de contrôles
    (`ControleCatalogueItem.impact_defaut`) dans `extract_findings`, propagé
    dans `build_action_plan`, avec en plus un `.get("impact", "")`
    défensif côté `docx_service.py`. Test de non-régression ajouté :
    `tests/test_control_service.py::test_extract_findings_and_action_plan_include_impact_key`.
25. **Mise en forme du rapport DOCX alignée sur la charte graphique
    OPT'HELIOS.** Le rapport d'audit (et la checklist terrain) utilisaient
    le thème par défaut de Word (Calibri gris/bleu clair générique), sans
    logo ni aucune des couleurs de marque utilisées par ailleurs sur les
    notes techniques OPT'HELIOS (bleu marine / or / bleu ciel, filets
    d'en-tête/pied de page, bandeaux de titre, encarts) — signalé comme
    "pas très sexy" et sans logo par l'utilisateur. Deux causes : (1)
    `domain/docx_service.py` construisait le document avec les styles Word
    par défaut (pas de couleur, pas de bandeau, tableaux à liseré gris) ;
    (2) `assets/opthelios_logo.png` (référencé par `docx_service.py` ET par
    la barre latérale de `app.py`) n'existait tout simplement pas dans le
    dépôt — ajouté ici (logo officiel, repris tel quel des notes
    techniques existantes).

    Ajout de `domain/opthelios_style.py`, qui reprend les codes exacts de
    la charte (bleu marine `#1C1E3D`, or `#F9B13A`, bleu ciel `#8FC4E4`,
    crème doré `#FAEAB6`, jaune pâle `#FBED94`, police Calibri, format A4,
    marges 1000 twips) et expose des fonctions réutilisables avec
    `python-docx` : bandeaux de titre H1/H2/H3, en-tête/pied de page avec
    filet or et pagination "Page X / Y", tableaux à en-tête marine/texte
    blanc et lignes alternées crème, encarts ("callout") pour les messages
    clés et l'appréciation globale, page de garde avec logo. `CORRECTIF`
    notable rencontré en le construisant : le style Word intégré
    "En-tête"/"Pied de page" embarque son propre taquet de tabulation
    centré, qui prenait le pas sur le taquet aligné à droite ajouté
    directement au paragraphe (le texte de droite atterrissait au milieu
    de la page au lieu d'être aligné à droite) — corrigé en repassant ces
    paragraphes au style "Normal" avant d'y ajouter le taquet voulu.

    `domain/docx_service.py` a été entièrement restylé avec ce module
    (page de garde, en-tête/pied de page courants, titres, tableaux,
    encarts), sans changer sa signature publique (`build_docx_report`,
    `build_checklist_docx`) : aucun autre fichier appelant n'a besoin
    d'être modifié. Vérifié visuellement (conversion LibreOffice → PDF →
    capture des pages clés) sur un rapport de démonstration couvrant les 4
    niveaux de criticité. Tests ajoutés :
    `tests/test_docx_service.py` (génération sans erreur du rapport et de
    la checklist, présence du logo, couleurs de la charte).
26. **Code couleur "feu tricolore" sur les verdicts et criticités du
    rapport.** Demande explicite : le rapport DOCX est transmis au maître
    d'ouvrage (non technicien), qui doit repérer d'un coup d'œil les points
    qui exigent une action de ceux qui sont acquis, sans lire chaque
    phrase de constat. Ajout dans `domain/opthelios_style.py` de couleurs
    sémantiques ajoutées EN COMPLÉMENT de la charte (pas de recouvrement
    avec le bleu marine/or/bleu ciel, réservés à l'identité visuelle) :
    rouge `#C0392B` (critique / non conforme), orange `#E67E22` (majeure /
    non présent / non vérifiable), jaune `#F2C94C` (mineure), bleu
    `#5DADE2` (information — signalé mais pas noté comme un écart), vert
    `#27AE60` (conforme), gris `#95A5A6` (sans objet / valeur non reconnue,
    repli neutre plutôt que plantage). Nouvelle fonction
    `add_status_badge()` : pastille "●" colorée + libellé en toutes
    lettres (au lieu de la valeur technique brute type "non_conforme"),
    appliquée dans `domain/docx_service.py::_add_findings` sur les lignes
    "Verdict :" et "Criticité :" de chaque constat détaillé (section 4 du
    rapport). Périmètre volontairement limité à cette section pour cette
    itération (l'utilisateur a aussi proposé de colorer la colonne
    Priorité du plan d'actions, le tableau récap par section et un
    "tableau de bord" en page d'appréciation globale — pas retenu pour
    l'instant, à reprendre si besoin). Vérifié visuellement. Tests
    ajoutés : `tests/test_docx_service.py::test_status_badge_covers_every_verdict_and_criticite_value`
    (couverture de toutes les valeurs réellement produites par le modèle,
    dont "information") et `test_add_status_badge_does_not_crash_on_unknown_value`.
27. **Lenteur au démarrage de l'appli, signalée par l'utilisateur.** Deux
    causes réelles trouvées par lecture de code (pas de supposition) :
    - `app.py` importait les 8 modules de pages en tête de fichier,
      systématiquement, à chaque démarrage du serveur Streamlit — y
      compris les pages jamais visitées pendant la session. Or certaines
      importent, à leur propre niveau module, des bibliothèques lourdes à
      charger : `folium` + `geopy` + `streamlit_folium` (page "Dossier"),
      `pandas` (page "Synthèse"), `python-docx` (page "Export"),
      `msal`/`requests` (page "Infos audit", via
      `repositories/sharepoint_repository.py` et
      `services/sharepoint_auth.py`). Le tout premier lancement payait donc
      le coût d'import de TOUTES ces bibliothèques d'un coup, même pour un
      auditeur qui n'utilise que 2-3 pages dans sa session. Corrigé en
      rendant chaque page — et les imports SharePoint/MSAL de
      `render_infos_audit()` — paresseuse (import à l'intérieur du bloc qui
      l'utilise plutôt qu'en tête de fichier) : Python met de toute façon
      en cache un module déjà importé (`sys.modules`), donc naviguer
      plusieurs fois vers la même page ne recharge rien de plus qu'avant —
      seul le tout premier affichage de CETTE page précise a désormais un
      coût d'import, au lieu que les 8 pages le paient toutes au démarrage.
    - `services/sharepoint_auth.py::_get_confidential_app()` recréait un
      nouveau `msal.ConfidentialClientApplication` à CHAQUE appel (donc à
      chaque sauvegarde, chaque affichage de "Infos audit"...). C'est cet
      objet qui porte le cache de jetons interne à MSAL : en le recréant
      systématiquement, le cache était toujours vide et
      `acquire_token_for_client` refaisait un aller-retour réseau complet
      vers Azure AD à chaque fois, alors qu'un jeton "app-only" reste
      valide ~60-90 min. Corrigé avec `@st.cache_resource` : une seule
      instance vit par processus serveur (partagée entre sessions, ce qui
      est correct ici — le jeton n'est pas propre à un auditeur), donc le
      cache MSAL sert enfin à quelque chose et la plupart des appels
      renvoient un jeton déjà en mémoire, sans latence réseau — sensible
      en particulier sur une connexion mobile en 4G depuis le terrain.

    Aucun changement fonctionnel : mêmes pages, mêmes boutons, même
    comportement, juste un chargement différé. Vérifié par compilation de
    l'ensemble du dépôt (`python -m compileall`) après coup.
28. **Échec de sauvegarde cloud rendu visible (retour terrain : mauvaise
    réception réseau en chaufferie sur iPhone).** Jusqu'ici,
    `services/autosave_service.py::try_autosave_to_cloud` échouait en
    silence total en cas de réseau indisponible : un toast "☁️ Sauvegarde
    automatique effectuée" s'affichait en cas de succès, mais RIEN n'était
    montré en cas d'échec — l'auditeur n'avait donc aucun moyen de savoir,
    en zone mal captée, que ses saisies ne partaient plus vers le cloud
    (risque de croire à tort que tout est sauvegardé). Corrigé :
    - `try_autosave_to_cloud` renvoie désormais un tri-état : `True`
      (synchronisé), `False` (cloud configuré mais tentative échouée —
      réseau, permissions...), `None` (cloud non configuré, rien à
      tenter). L'appelant (`ui/state.py::_maybe_autosave`) mémorise cet
      état dans `st.session_state` (`_cloud_sync_ok`,
      `_cloud_sync_last_ok_ts`) et n'affiche un toast QUE sur un
      changement d'état (réussite → échec ou l'inverse), jamais à chaque
      tentative — sinon, avec le throttle de 20s existant, un auditeur en
      zone blanche recevrait un toast d'échec toutes les 20 secondes
      pendant toute sa visite.
    - Nouvel indicateur permanent dans la barre latérale, visible sur
      TOUTES les pages (`app.py::_render_cloud_sync_status_sidebar`) :
      "☁️ Sauvegarde cloud à jour" en fonctionnement normal, ou un
      avertissement explicite ("⚠️ Sauvegarde cloud en attente (réseau ?)
      — dernière réussie il y a X min. Vos saisies restent conservées dans
      cette session ; retentez depuis « Infos audit »...") en cas d'échec.
      L'indicateur ne s'affiche que si une tentative a déjà eu lieu dans la
      session (clé absente sinon) : aucun coût supplémentaire au
      démarrage, cohérent avec le correctif précédent sur les imports
      paresseux.
    - Rappel important, déjà vrai avant ce correctif mais qui reste la
      vraie garantie anti-perte de données : l'écriture locale (JSON de
      l'audit en session, fichiers de preuves sur disque) a TOUJOURS lieu
      en premier et ne dépend jamais du cloud (voir
      `services/evidence_service.py::_try_cloud_backup`, conçu comme une
      couche de sécurité EN PLUS, pas comme le seul filet). Ce correctif ne
      change donc rien à la fiabilité de la sauvegarde elle-même : il la
      rend seulement visible quand elle échoue, pour que l'auditeur sache
      qu'il doit refaire un "Forcer la sauvegarde maintenant" une fois une
      meilleure connexion retrouvée (ou, à défaut de réseau du tout sur le
      site, utiliser la checklist terrain imprimable — voir point 20 —
      puis ressaisir une fois de retour en zone couverte).

    Tests ajoutés : `tests/test_autosave_visibility.py` (tri-état,
    non-régression du throttle, timestamp de dernière réussite préservé en
    cas d'échec, indicateur de barre latérale qui ne plante jamais).

## Déploiement cloud (accès depuis iPhone / tablette / PC)

L'appli tournait jusqu'ici uniquement en local (`streamlit run app.py`),
donc utilisable seulement sur le PC qui l'exécute. Pour y accéder depuis
n'importe quel appareil via une URL, déploiement sur **Streamlit Community
Cloud** (gratuit) :

Deux fichiers ont été ajoutés pour rendre ça possible :
- `packages.txt` : liste `libreoffice`, installé automatiquement par
  Streamlit Cloud (dépendance système, pas Python) pour permettre l'export
  PDF sur ce serveur Linux, où Microsoft Word n'existe pas.
- `services/pdf_service.py` : la conversion DOCX → PDF essaie d'abord Word
  (via `docx2pdf`, en local Windows/Mac), puis LibreOffice en ligne de
  commande (`soffice --headless`) si Word n'est pas disponible — donc le
  même bouton "Convertir en PDF" fonctionne aussi bien en local que
  déployé. `docx2pdf` a été rendu conditionnel dans `requirements.txt`
  (marqueur `sys_platform`) pour ne pas tenter de l'installer sur Linux.

### Étapes de déploiement (à faire par toi, ça nécessite ton compte GitHub)

1. Va sur [share.streamlit.io](https://share.streamlit.io), connecte-toi
   avec ton compte GitHub (celui utilisé pour `OPTHELIOS/Audit-Solaire`),
   autorise l'accès si demandé.
2. **New app** (ou **Create app**) → choisis le dépôt
   `OPTHELIOS/Audit-Solaire`, la branche `main` (une fois ta Pull Request
   fusionnée), fichier principal `app.py`.
3. Avant ou juste après le premier déploiement : **Settings → Secrets**,
   colle le même contenu que ton `.streamlit/secrets.toml` local :
   ```toml
   [microsoft_app]
   tenant_id = "..."
   client_id = "..."
   client_secret = "..."
   site_id = "..."
   root_folder = "AuditsOPTHELIOS"
   ```
4. Lance le déploiement (premier build ~2-5 min, le temps d'installer les
   dépendances Python et LibreOffice).
5. **Important (données clients)** : passe l'appli en **privée** —
   **Settings → Sharing** → restreins l'accès à des emails précis (le tien
   et ceux des collègues concernés). Le plan gratuit autorise une appli
   privée.
6. Une fois en ligne, tu obtiens une URL du type
   `https://xxxxx.streamlit.app`.

### Avoir une icône sur l'écran d'accueil (iPhone/iPad/Android/PC)

- **iPhone/iPad (Safari)** : ouvre l'URL → bouton Partager → **Sur l'écran
  d'accueil**. Ça crée une icône qui s'ouvre en plein écran, sans barre
  d'adresse.
- **Android (Chrome)** : menu ⋮ → **Ajouter à l'écran d'accueil** /
  **Installer l'application**.
- **PC (Chrome/Edge)** : icône d'installation dans la barre d'adresse, ou
  menu → **Installer [nom de l'appli]**.

### Limites du plan gratuit à connaître

RAM limitée (1 Go), l'appli se met en veille après 12h d'inactivité (le
premier accès après veille prend ~30 secondes le temps de redémarrer), pas
de nom de domaine personnalisé. Si ça devient limitant (usage intensif,
image plus pro), un hébergement dédié (VPS, Azure App Service...) reste une
évolution possible plus tard.

### Logo manquant

**Résolu (point 25 plus haut)** : `assets/opthelios_logo.png` a été ajouté
(logo officiel OPT'HELIOS), plus tout un jeu d'icônes carrées dérivées dans
`assets/icons/` (favicon, icône iOS/Android...). Cette note reste ici pour
mémoire mais ne s'applique plus.

## Palier 1 — passage en hébergement pro avec domaine personnalisé

Demande explicite (sept. 2026) : passer d'un lien `*.streamlit.app` à une
"vraie appli" avec une adresse et une présentation pro. Point important
établi avant de choisir une direction : **Streamlit Community Cloud (la
section "Déploiement cloud" ci-dessus) ne supporte pas les domaines
personnalisés** — seulement un sous-domaine `*.streamlit.app` — et n'offre
aucun moyen d'injecter une icône "Ajouter à l'écran d'accueil" correcte
côté iOS. Un vrai domaine (ex. `audit.opthelios.fr`) et une icône
d'installation soignée nécessitent donc un hébergement via **conteneur
Docker**, sur une plateforme qui accepte un domaine personnalisé (Azure
Container Apps, Render, Fly.io, Railway...).

### Ce qui a été préparé côté code (déjà fait, applicable quel que soit l'hébergeur choisi)

29. **Thème visuel natif Streamlit** (`.streamlit/config.toml`, nouveau) :
    l'appli utilisait jusqu'ici le thème bleu générique par défaut de
    Streamlit — rien ne rappelait la charte OPT'HELIOS. Le thème reprend
    désormais les mêmes couleurs que les documents (or `#F9B13A` en couleur
    d'accent/boutons, bleu marine `#1C1E3D` en couleur de texte, fond
    crème très clair `#F4F1E4` pour la barre latérale). Aucune ligne de
    code Python à changer : Streamlit lit ce fichier au démarrage.
30. **Favicon propre** (`app.py`) : l'onglet du navigateur affichait le
    logo rectangulaire complet (700×363 px avec marge blanche), illisible
    à la taille d'un favicon (16-32 px). Utilise désormais
    `assets/icons/favicon-32.png`, un recadrage carré centré sur le seul
    disque solaire (généré depuis le logo officiel, marge blanche
    supprimée par flood-fill pour un raccord invisible avec le fond
    marine). Le logo complet reste utilisé tel quel dans la barre
    latérale, où sa largeur passe bien.
31. **Icônes "Ajouter à l'écran d'accueil" iOS/Android + manifest PWA**
    (`assets/icons/` : `apple-touch-icon.png` 180×180 sans canal alpha —
    obligatoire côté iOS, `icon-192.png`, `icon-512.png`, `manifest.json`).
    Streamlit ne propose aucune option pour injecter des balises dans le
    `<head>` de la page (les injections via `st.markdown`/composants sont
    isolées dans un iframe, sans accès au head du document parent) : la
    seule méthode qui fonctionne réellement consiste à patcher directement
    le `index.html` compilé, livré à l'intérieur du paquet `streamlit`
    installé. C'est le rôle de `scripts/patch_streamlit_pwa.py`, exécuté
    au moment du build Docker (voir `Dockerfile`) — jamais en local, jamais
    sur Streamlit Community Cloud. Le script est défensif de bout en bout
    (jamais d'exception, jamais d'échec de build : si la structure interne
    de Streamlit a changé, il log un avertissement et ne fait rien plutôt
    que de produire une image cassée) et idempotent (relancer le build ne
    duplique pas l'injection). Logique testée en sandbox avec un
    `index.html` factice (injection, idempotence, absence totale de
    crash si `streamlit` ou son dossier `static/` sont introuvables).
32. **`Dockerfile` + `.dockerignore`** (nouveaux, racine du dépôt) : image
    de production (`python:3.12-slim` + LibreOffice + dépendances Python +
    patch PWA ci-dessus), avec un `HEALTHCHECK` pour que l'hébergeur sache
    détecter un conteneur bloqué. Le `.dockerignore` exclut explicitement
    `.streamlit/secrets.toml` et tous les fichiers de secrets de l'image —
    **les secrets `microsoft_app` doivent être injectés au runtime via les
    variables d'environnement/secrets de l'hébergeur choisi, jamais copiés
    dans l'image**, qui peut finir dans un registre partagé.
33. **`docker-entrypoint.sh`** (nouveau) + `Dockerfile` mis à jour
    (`ENTRYPOINT ["./docker-entrypoint.sh"]`, `ENV PORT=8501` en repli) :
    hébergeur choisi (voir ci-dessous) **Render.com**. Sur Render, un
    "Secret File" uploadé dans le dashboard d'un service Docker est monté
    au runtime à un chemin **fixe** : `/etc/secrets/<nom-du-fichier>`
    (impossible de choisir cet emplacement, contrairement aux services non
    Docker) — alors que l'appli lit ses secrets à
    `.streamlit/secrets.toml`. Le script fait le pont entre les deux : au
    démarrage du conteneur, si `/etc/secrets/secrets.toml` existe et que
    `.streamlit/secrets.toml` n'existe pas encore, il copie le premier vers
    le second, puis lance `streamlit run`. Aucune modification du code
    Python n'est nécessaire : `services/sharepoint_auth.py` continue de
    lire `st.secrets["microsoft_app"]` exactement comme en local. Le
    script lit aussi `$PORT` (fourni par Render, avec un repli sur `8501`
    pour un `docker run` local sans cette variable). Testé en sandbox
    (chemins substitués) : copie correcte au premier démarrage, et pas
    d'écrasement d'un `secrets.toml` déjà présent au démarrage suivant.

### Hébergeur choisi : Render.com

Étapes pour mettre l'appli en ligne avec un domaine personnalisé :

1. Créer un compte sur [render.com](https://render.com) (le plan Hobby est
   gratuit, seul le service web lui-même est payant — voir l'offre à
   l'étape 4).
2. **New → Web Service**, puis connecter le dépôt GitHub du projet (le
   pousser sur GitHub au préalable si ce n'est pas déjà fait — rappel :
   les opérations git restent à faire depuis ton poste, voir plus bas).
3. Render détecte automatiquement le `Dockerfile` à la racine du dépôt et
   propose de builder l'image telle quelle — rien à configurer côté build.
4. Choisir l'offre **Starter (7 $/mois, toujours actif)** plutôt que
   l'offre gratuite : celle-ci met le service en veille après 15 minutes
   d'inactivité (retour en ligne après ~30 secondes au prochain accès),
   ce qui reproduit exactement le défaut de lenteur de Streamlit Community
   Cloud qu'on cherche justement à corriger.
5. Onglet **Environment → Secret Files** : ajouter un fichier nommé
   exactement `secrets.toml` (le nom compte : `docker-entrypoint.sh` le
   cherche à `/etc/secrets/secrets.toml`), avec le même contenu que le
   `.streamlit/secrets.toml` local (section `[microsoft_app]` :
   `tenant_id`, `client_id`, `client_secret`, `site_id`). Ne jamais coller
   ces valeurs dans le champ "Environment Variables" classique du même
   onglet — le fichier Secret File est fait pour ça, contrairement aux
   variables d'environnement il n'apparaît pas en clair dans les logs de
   build.
6. Déployer. Premier build plus long (installation LibreOffice + dépendances
   Python) — les déploiements suivants sont plus rapides (cache Docker).
   Vérifier que le service répond sur son adresse `<nom-du-service>.onrender.com`.
7. **Settings → Custom Domains** → ajouter le sous-domaine choisi (ex.
   `audit.opthelios.fr`) → Render indique la valeur CNAME exacte à créer
   (généralement `<nom-du-service>.onrender.com`). Aller ensuite chez le
   registrar où `opthelios.fr` est géré (OVH, Gandi ou autre — à
   identifier côté toi) et créer cet enregistrement CNAME pour le
   sous-domaine `audit`. La propagation DNS peut prendre de quelques
   minutes à quelques heures ; Render émet ensuite automatiquement le
   certificat HTTPS une fois le CNAME détecté.

**Accès protégé : FAIT** (sept. 2026, voir la section "Contrôle d'accès à
l'application" plus bas). L'option retenue est la connexion Microsoft Entra
ID, plus robuste qu'un mot de passe partagé et cohérente avec un locataire
M365 déjà en place. À ne pas confondre avec l'authentification
`microsoft_app`, qui ne protège que l'accès à SharePoint et laissait l'appli
elle-même ouverte à quiconque connaissait l'URL.

## Publication en mode application iPhone/tablette (sept. 2026)

Objectif retenu : l'appli s'installe sur l'écran d'accueil d'un iPhone ou
d'un iPad et s'ouvre en plein écran, sans barre d'adresse. Pas de coque
native, pas de compte développeur Apple, pas de validation App Store — la
voie PWA, distribution par simple lien.

Décision prise en amont : le fonctionnement **hors réseau n'est pas requis**
(réseau fiable sur les sites audités). C'est ce qui rend Streamlit adapté
ici. Streamlit pilote l'écran par websocket permanente : sans réseau, ce
n'est pas un mode dégradé, c'est un écran figé. Si un jour des audits ont
lieu en zone blanche, la seule réponse sérieuse serait de refaire le front
en mode "offline-first" (React ou Flutter + synchronisation), pas d'ajuster
la configuration.

### Ce qui a été ajouté

40. **Service worker** (`assets/pwa/sw.js`, `assets/pwa/offline.html`,
    nouveaux) : deux raisons d'exister, et la mise en cache de l'appli n'en
    fait volontairement pas partie. D'abord l'installabilité sur Android —
    Chrome n'affiche sa bannière "Installer l'application" que si la page
    déclare un service worker muni d'un gestionnaire `fetch` (sur iOS,
    l'ajout reste de toute façon toujours manuel, via le menu Partager de
    Safari). Ensuite le remplacement de la page d'erreur brute du navigateur
    par un écran aux couleurs OPT'HELIOS en cas de coupure : lancée depuis
    l'écran d'accueil, l'appli semblait sinon avoir planté. Cet écran est
    autonome (aucune ressource externe, logo en SVG inline — rien ne peut
    être téléchargé au moment où il s'affiche) et se recharge tout seul au
    retour du réseau.

    **Ce qui n'est pas fait, et pourquoi :** le code de l'appli n'est pas
    mis en cache. Streamlit sert un bundle JS versionné ; un cache agressif
    finirait un jour par servir un bundle périmé face à un serveur à jour,
    panne dont l'utilisateur ne peut pas sortir. Tout ce qui n'est pas une
    icône précachée part au réseau, et les endpoints `/_stcore/` (websocket,
    santé, envoi de fichiers) ne sont jamais interceptés.

41. **Version de Streamlit épinglée** (`requirements.txt`) : `streamlit`
    était non épinglé. Or `scripts/patch_streamlit_pwa.py` modifie le
    `index.html` compilé **à l'intérieur du paquet Streamlit**, structure
    interne couverte par aucune garantie de compatibilité. Le patch étant
    défensif, une montée de version ne planterait pas — elle désactiverait
    le mode "appli" **en silence**, sans le moindre message. D'où
    `streamlit==1.62.0`. Avant de relever cette version : rejouer le build
    Docker et vérifier que le log affiche bien `[patch_streamlit_pwa] OK`.

42. **Configuration Render versionnée** (`render.yaml`, nouveau) : la
    configuration du service vit dans le dépôt plutôt que dans des champs du
    tableau de bord. Région Francfort (la latence compte : Streamlit renvoie
    chaque interaction au serveur), `PORT` fixé à 8501 pour rester cohérent
    avec `EXPOSE` et `HEALTHCHECK` du Dockerfile, contrôle de santé sur
    `/_stcore/health`. Le palier `starter` (payant, 7 $/mois) est retenu
    délibérément : sur le palier gratuit, la mise en veille imposerait 30 à
    60 s de rechargement d'une image contenant LibreOffice (~1 Go) — sur un
    téléphone, lancée depuis l'écran d'accueil, l'appli paraîtrait
    simplement plantée. Remplacer par `free` pour tester sans engagement.

43. **Garde-fou sur les fins de ligne** (`.gitattributes`, nouveau) : la
    machine de développement est sous Windows avec `core.autocrlf=true`, et
    le dépôt n'avait aucun `.gitattributes`. Le dépôt est sain aujourd'hui,
    mais la prochaine extraction sous Windows convertirait
    `docker-entrypoint.sh` en CRLF — le shebang devient alors `/bin/sh\r`,
    et le conteneur meurt sur un `not found` qui désigne le shell et non le
    script, piège classique et difficile à diagnostiquer — et
    `packages.txt` en CRLF ferait échouer le build (`apt-get` recevrait
    `libreoffice\r`). Les `.py` sont volontairement laissés au comportement
    actuel, pour éviter une renormalisation de tout le dépôt.

### Reste à faire côté toi

Créer le service sur Render (`New → Blueprint`, sélectionner ce dépôt :
Render lit `render.yaml`), puis déposer le Secret File nommé exactement
`secrets.toml` — `docker-entrypoint.sh` le recopie au démarrage. Compter
une dizaine de minutes pour le premier build, LibreOffice étant volumineux.

Ensuite, sur iPhone : ouvrir l'URL dans **Safari** (pas Chrome, l'ajout à
l'écran d'accueil n'y fonctionne pas sous iOS) → Partager → **Sur l'écran
d'accueil**.

**Point à vérifier dès le premier essai sur iPhone :**
`scripts/patch_streamlit_pwa.py` déclare
`apple-mobile-web-app-status-bar-style` à `black-translucent`, ce qui fait
passer le contenu **sous** la barre d'état iOS. Streamlit affichant sa
propre barre d'outils tout en haut, le menu hamburger risque d'être
partiellement masqué. Si c'est le cas, basculer cette valeur sur `default` —
un seul mot à changer. Cela se constate en trois secondes sur un vrai
téléphone, d'où le choix de ne pas trancher à l'aveugle.

## Contrôle d'accès à l'application (connexion Microsoft Entra ID)

Jusqu'ici l'appli n'avait **aucune authentification**. Sans conséquence tant
qu'elle tournait sur ton poste ; inacceptable dès lors qu'elle est publiée
sur une URL d'hébergeur, où toute personne disposant du lien pourrait
consulter les audits, les photos et les adresses des clients, et déclencher
des écritures dans le SharePoint OPT'HELIOS via les identifiants
`microsoft_app` embarqués côté serveur. Une URL Render n'est pas devinable,
mais elle n'est pas secrète : elle circule par SMS, par mail, dans les
historiques de navigateur et les journaux des équipements traversés.

44. **Portail d'accès** (`services/app_auth.py`, nouveau ; branché en
    première instruction de `app.py::main()`) : connexion OpenID Connect via
    `st.login()`/`st.user`, seuls les comptes du locataire OPT'HELIOS
    entrent. Rien n'est lu ni écrit — ni session d'audit, ni appel
    SharePoint — tant que l'utilisateur n'est pas authentifié. Identité
    connectée et bouton de déconnexion en pied de barre latérale.

    **Le point de conception qui compte est le comportement quand la
    configuration est absente.** Laisser passer serait le piège classique du
    portail permissif : un secret mal déposé chez l'hébergeur rouvrirait
    l'appli à tous sans que rien ne le signale, puisque tout continuerait de
    fonctionner normalement. Deux cas sont donc distingués — **en local**,
    accès autorisé avec un avertissement visible (exiger une connexion Entra
    ID pour lancer l'appli sur son propre poste serait absurde) ; **sur un
    hébergeur**, détecté par les variables d'environnement `RENDER`,
    `FLY_APP_NAME`, `WEBSITE_SITE_NAME` ou `K_SERVICE`, accès **refusé** avec
    un message explicite. Une erreur de configuration doit fermer l'appli,
    jamais l'ouvrir.

### DEUX inscriptions Azure, à ne pas confondre

| | À quoi ça sert | Type |
|---|---|---|
| `[microsoft_app]` | l'**application** écrit dans SharePoint, sans humain | permissions d'application, consentement admin |
| `[auth.microsoft]` | l'**utilisateur** humain se connecte pour ouvrir l'appli | OpenID Connect, aucune permission Graph |

Elles sont volontairement séparées. La première détient des droits
d'écriture larges : partager son secret avec un flux de connexion
utilisateur serait malsain, et leurs secrets doivent pouvoir être renouvelés
indépendamment. Ne réutilise donc pas l'inscription "Audit-Solaire-Backend"
créée plus haut.

### 1. Créer l'inscription pour la connexion

Sur [entra.microsoft.com](https://entra.microsoft.com) → **Inscriptions
d'applications** → **Nouvelle inscription** :

1. **Nom** : ex. `OPT'HELIOS Audit Solaire — Connexion utilisateurs`.
2. **Types de comptes pris en charge** : *Comptes dans cet annuaire
   d'organisation uniquement (locataire unique)*. **C'est ce réglage qui
   interdit l'entrée à toute personne extérieure à OPT'HELIOS** — surtout
   pas une option multi-locataires.
3. **URI de redirection** : type **Web**, valeur
   `http://localhost:8501/oauth2callback`.
4. **Inscrire**, puis relever l'**ID d'application (client)** et l'**ID
   d'annuaire (locataire)**.
5. **Certificats et secrets** → **Nouveau secret client** → copier la
   **valeur** immédiatement (jamais réaffichée).

Aucune autorisation d'API à ajouter : `User.Read`, présente par défaut,
suffit.

### 2. Renseigner les secrets

Copier `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml` en
**conservant la section `[microsoft_app]` existante**, puis compléter
`[auth]` et `[auth.microsoft]`. Le `server_metadata_url` doit contenir l'ID
de locataire à la place des zéros — c'est lui qui restreint la connexion au
seul annuaire OPT'HELIOS ; ne pas y mettre `common` ni `organizations`, qui
ouvriraient l'appli aux comptes de n'importe quelle entreprise.

Générer le `cookie_secret` (le changer déconnecte tout le monde) :

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Installer les dépendances de connexion, que Streamlit n'installe pas de
lui-même. Passer par l'extra `[auth]` plutôt que par une liste manuelle :
une première version de cette consigne ne mentionnait qu'`Authlib`, alors
que Streamlit 1.62 exige aussi `httpx` — l'appli affichait bien la page de
connexion, puis plantait au clic sur un `ModuleNotFoundError: httpx`.

```
pip install -r requirements.txt
```

### 3. Vérifier

```
streamlit run app.py
```

Une page de connexion doit s'afficher à la place de l'appli. Après
authentification Microsoft, l'appli s'ouvre et ton nom apparaît en bas de la
barre latérale, avec un bouton de déconnexion.

**Si l'appli affiche « Connexion impossible — configuration à corriger »**
à la place du bouton de connexion, elle a reconnu l'une des deux erreurs de
saisie rencontrées lors de la mise en place : le texte d'exemple resté dans
le fichier, ou l'« ID secret » d'Azure collé à la place de sa « Valeur »
(l'ID a la forme de 5 blocs séparés par 4 tirets, la Valeur jamais). Le
message précise laquelle. Ce contrôle ne porte que sur la forme : un secret
expiré ou supprimé dans Azure le passe sans encombre, et échoue au moment de
la connexion.

**Ne jamais faire de capture d'écran de `secrets.toml`**, même partielle,
pour demander de l'aide : un secret visible sur une image doit être
considéré comme compromis et renouvelé. C'est arrivé lors de la mise en
place ; le secret concerné a été supprimé dans Azure et remplacé.

### 4. Au moment de la mise en ligne

**L'URI de redirection doit correspondre au caractère près** entre Azure et
`secrets.toml` : un `http` contre `https`, un `/` final en trop, et Azure
refuse avec un message peu parlant.

Il en faut **deux**, pas une : `http://localhost:8501/oauth2callback` pour
les essais, et `https://<nom-du-service>.onrender.com/oauth2callback` en
ligne. Une seule inscription Azure les accepte toutes les deux — ajouter la
seconde le moment venu. En revanche la clé `redirect_uri` des secrets, elle,
diffère selon l'environnement : celle de ton poste, et celle du Secret File
Render.

## Axes d'analyse réglementaire SOCOL / SOLO2018 (sept. 2026)

Demande explicite : compléter l'audit avec des axes d'analyse réglementaire
supplémentaires, en s'appuyant sur l'outil THMès (INES), sur les notions à
vérifier au sens de la charte SOCOL (solaire thermique collectif — notes
techniques, notes de calcul, schémas de principe nommés) et sur les données
de dimensionnement issues d'outils comme SOLO2018. Comparaison avec THMès
faite au préalable (voir échange du même jour) : THMès est un outil de
**réception/mise en service** d'installations neuves (équivalent numérique
du livret SOCOL), quand cette appli fait un **audit d'installations
existantes** — le point commun exploité ici est le calcul d'indicateurs de
performance chiffrés et colorés (réel/théorique), que THMès vient d'ajouter
et que l'appli n'avait jusque-là que sous forme de contrôles qualitatifs
(PERF_001-003, "cohérent / pas cohérent").

Sources utilisées (recherche web du jour, à jour sept. 2026) : livret
technique SOCOL "Les Systèmes Solaires Combinés pour les bâtiments
collectifs" (éd. 2023, www.solaire-collectif.fr), fiche technique SOCOL 2021
"Ratios des besoins en eau chaude sanitaire...", fiche THMès (INES) et sa
fiche Google Play, page INES "Solo 2018".

34. **Schéma-type SOCOL déduit de la classification** (`domain/socol_reference.py`,
    nouveau ; `domain/models.py::ClassificationInstallation.schema_reference_socol`).
    Bonne surprise en explorant le code existant : les enums
    `SystemeCapteurs`/`TypeEchangeur`/`TypeStockageSolaire` de
    `domain/control_catalog.py` correspondaient déjà presque terme à terme
    aux "sous-ensembles" que SOCOL utilise pour nommer ses schémas de
    référence (REF1-SSC1, REF1-SSC2, REF3-SSC1...). `suggest_schema_reference()`
    propose donc automatiquement un code à partir de ces 3 champs déjà
    saisis en page "04 - Installation", où un nouveau sélecteur permet de
    confirmer ou corriger ce choix. Limite assumée et documentée dans le
    code : la base REFx complète (REF1 à REF5) dépend aussi du type de
    distribution de chauffage et de la présence d'un bouclage sanitaire, des
    informations que l'appli ne collecte pas — la suggestion reste donc un
    point de départ, jamais une certification automatique.
35. **Bibliothèque de schémas de principe SOCOL génériques + argumentaire**
    (`assets/schemas_socol/*.png`, générés par `scripts/generate_schemas_socol.py`,
    insérés en annexe du rapport DOCX par `domain/docx_service.py::_add_schema_appendix`).
    Point de propriété intellectuelle important, documenté dans
    `domain/socol_reference.py` : les schémas hydrauliques publiés par SOCOL
    (livret technique, fiches PDF) sont la propriété de leurs auteurs et ne
    sont PAS reproduits. Les 3 images du dépôt sont redessinées intégralement
    (symboles hydrauliques génériques, palette de couleurs OPT'HELIOS) —
    seuls le principe de fonctionnement (schéma de principe, non
    protégeable en tant que tel) et la nomenclature SOCOL (simple
    identifiant, utilisé comme référentiel professionnel reconnu) sont
    repris. Couvre les 3 configurations directement déductibles des données
    saisies (REF1-SSC1 échangeur externe, REF1-SSC2 échangeur immergé,
    REF3-SSC1 eau technique), chacune avec un texte de principe et des
    points de vigilance rédigés pour cette appli. Script rejouable à volonté
    (`python scripts/generate_schemas_socol.py`), par exemple si la palette
    de couleurs évolue.
36. **Indicateurs de performance FSAV/Prod/Taux** (`domain/performance_service.py`,
    nouveau). Formules du livret technique SOCOL (chapitre "Indicateurs de
    performance") : FSAV = QSTU/(QApp+QSTU) (taux d'économie d'énergie
    d'appoint, ISO 9488), Prod = QSTU/surface (productivité, kWh/m².an,
    critère Fonds Chaleur ADEME), Taux = conso_aux/QSTU (part des
    auxiliaires électriques, seuil SOCOL : doit rester sous 1,5 % pour un
    système efficace — les bornes intermédiaires orange/rouge de l'appli
    sont un choix OPT'HELIOS explicitement documenté comme tel dans le code,
    pas une valeur SOCOL). Nécessite 3 nouveaux relevés "sur la période"
    (pas des valeurs instantanées comme les autres relevés existants) :
    "Production solaire utile sur la période (QSTU)", "Énergie d'appoint
    sur la période (QApp)", "Consommation électrique auxiliaires sur la
    période" — ajoutés à `domain/releves_catalog.py`, à renseigner depuis la
    supervision/télégestion quand elle existe. Le calcul prend
    systématiquement le relevé le plus récent en cas de saisies multiples
    du même libellé. Affiché en page "Mesures et comparaison" (pastilles
    colorées) et dans le rapport DOCX (section "8.2"), avec la même échelle
    de statut réel/théorique (vert/jaune/orange/rouge selon le ratio) que le
    point suivant.
37. **Onglet dimensionnement et besoins ECS** (`domain/models.py::DimensionnementSolaire`,
    nouveau sous-objet de `Installation` ; UI dans "04 - Installation" ;
    calculs dans `domain/dimensionnement_service.py`, nouveau). Permet de
    saisir les résultats d'une étude de dimensionnement d'origine (type
    SOLO2018 : zone climatique, besoins ECS journaliers, taux de couverture
    visé, productible théorique kWh/m².an, surface d'étude, référence de la
    source) pour comparer automatiquement le réel mesuré (voir point 36) au
    théorique attendu. Décision technique importante : PAS de
    réimplémentation du moteur de calcul SOLO2018 (ensoleillement, calcul
    TRNSYS) — solo2018.tecsol.fr n'a pas d'API publique et le moteur est
    trop complexe/spécifique pour être reproduit fiablement. À la place,
    deux approches complémentaires et réalistes : (1) saisie manuelle des
    résultats déjà produits par une étude SOLO2018 existante, quand elle est
    retrouvée ; (2) un **pré-dimensionnement de contrôle indépendant**,
    utile en audit d'existant quand cette étude n'est pas retrouvée, basé
    sur les ratios officiels de la fiche technique SOCOL 2021 (valeurs
    exactes reprises dans `domain/dimensionnement_service.py`) : ratio
    besoins/surface par zone climatique (40-45 l/m² zone nord, 50-75 l/m²
    zone centre, 70-100 l/m² zone sud), ratio de volume de stockage (75-100
    l/m² en stockage sanitaire classique, 50 l/m² minimum en eau technique),
    taux de couverture solaire utile optimal (85-90 % sur le mois critique).
    Ces ratios sont explicitement documentés comme des valeurs indicatives
    de prédimensionnement, pas des seuils réglementaires stricts : les
    fonctions renvoient un statut informatif, jamais un verdict de
    non-conformité du catalogue de contrôles.
38. **Sous-contrôles de sécurité surchauffe/stagnation détaillés**
    (`domain/control_catalog.py`). Le contrôle unique et générique REG_005
    ("Gestion des sécurités haute température et surchauffe opérationnelle")
    est décomposé en 4 contrôles avec des seuils numériques réels (chapitre
    3.3 du livret technique SOCOL, gestion du risque de surchauffe) :
    REG_005 recentré sur le seul seuil de bascule de la protection
    anti-surchauffe (60-75°C), REG_006 (nouveau) sur le seuil de stagnation
    selon la technologie de capteur (140-150°C autoprotégé, 200-220°C
    standard), REG_007 (nouveau) sur les consignes de stockage (~80°C) et de
    sécurité haute température (~90°C), REG_008 (nouveau) sur le
    dimensionnement du vase d'expansion et le tarage de la soupape de
    sécurité. REG_006 et REG_008 sont conditionnés à
    `systeme_capteurs_in: ["sous_pression"]` (mécanisme
    `condition_applicabilite` déjà existant) : une installation
    autovidangeable (drain-back) ne gère pas la stagnation de la même
    façon et n'a pas nécessairement de vase d'expansion sur le circuit
    solaire. L'identifiant `REG_005` est conservé tel quel (seul son
    contenu est affiné) pour ne pas invalider un `controle_id` déjà
    enregistré sur un audit existant.
39. **Correctif connexe découvert en marge** (`ui/pages/_04_installation.py`) :
    le multiselect "Type(s) de comptage" proposait les valeurs `"appoint"`
    et `"bouclage_solaire"`, qui ne correspondaient à AUCUN membre de
    l'enum `domain.control_catalog.TypeComptage` (les vraies valeurs sont
    `"comptage_appoint"` et `"comptage_bouclage_solaire"`). Conséquence :
    un contrôle du catalogue conditionné par
    `type_comptage_any_in: ["comptage_appoint"]` ne pouvait jamais matcher,
    même quand l'auditeur avait bien coché "Appoint" dans le formulaire —
    bug silencieux (pas d'erreur, juste un filtrage d'applicabilité qui ne
    se déclenchait jamais). Corrigé en alignant les valeurs proposées sur
    l'enum réel.

Tests ajoutés : `tests/test_socol_reference.py` (suggestion de schéma,
présence des images sur le disque pour chaque code de la bibliothèque),
`tests/test_dimensionnement_service.py` (ratios SOCOL 2021, zones
climatiques, stockage sanitaire vs eau technique), `tests/test_performance_service.py`
(formules FSAV/Prod/Taux, bornes du ratio réel/théorique, relevé le plus
récent retenu en cas de doublon de libellé), `tests/test_control_catalog.py`
(validité globale du catalogue, couverture REG_005-008, conditions
d'applicabilité sous_pression), et deux nouveaux cas dans
`tests/test_docx_service.py`/`tests/test_models.py` (génération du rapport
avec et sans données SOCOL, roundtrip JSON des nouveaux champs).

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

Depuis sept. 2026, `tests/test_app_auth.py` couvre aussi le contrôle
d'accès. Au-delà des tests unitaires de la règle, deux tests d'intégration
exécutent l'appli réelle via le harnais officiel de Streamlit
(`streamlit.testing.v1.AppTest`) et vérifient qu'avec une variable
d'hébergeur positionnée et aucune authentification configurée, **aucun
contenu applicatif n'est rendu** — ni titre, ni navigation. Sans eux, un
simple oubli d'appel à `require_login()` dans `main()` laisserait tous les
tests au vert avec une appli grande ouverte sur Internet.
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
