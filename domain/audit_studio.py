"""OPT'HELIOS Audit Studio — modules metier additionnels.

Ce module apporte deux briques inspirees du prototype Audit Solaire Builder V2 :

- un catalogue de **scenarios de decision** d'audit solaire thermique (conserver,
  rehabiliter, redimensionner, remplacer, abandonner, portefeuille multi-batiments) ;
- une **bibliotheque de formulations types OPT'HELIOS** capitalisee sur les rapports
  reels (schemas incoherents, surdimensionnement, capteurs integres, etc.).

Ces structures sont volontairement decrites comme des donnees simples (Pydantic +
constantes) afin de pouvoir etre :

* exposees dans l'interface Streamlit (selecteurs, expanders) ;
* serialisees dans le JSON d'audit sans casser les audits existants ;
* exploitees par l'export DOCX/Markdown pour enrichir le rapport final.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Mode de rapport
# ---------------------------------------------------------------------------


class ModeRapport(str, Enum):
    """Profil editorial du livrable produit par l'auditeur."""

    audit_complet = "audit_complet"
    diagnostic_court = "diagnostic_court"


MODE_RAPPORT_LABELS: dict[str, str] = {
    ModeRapport.audit_complet.value: "Audit complet (rapport detaille)",
    ModeRapport.diagnostic_court.value: "Diagnostic court (note de synthese)",
}


MODE_RAPPORT_DESCRIPTIONS: dict[str, str] = {
    ModeRapport.audit_complet.value: (
        "Rapport long format avec contexte, methodologie detaillee, constats par "
        "section, plan d'actions priorise et annexes documentaires completes."
    ),
    ModeRapport.diagnostic_court.value: (
        "Note de synthese resserree : appreciation globale, principaux constats, "
        "scenarios envisages et recommandations prioritaires uniquement."
    ),
}


# ---------------------------------------------------------------------------
# Scenarios d'audit
# ---------------------------------------------------------------------------


class ScenarioAudit(BaseModel):
    """Decrit un scenario de decision propose a l'issue de l'audit."""

    code: str
    libelle: str
    horizon: str = ""
    description: str = ""
    conditions: list[str] = Field(default_factory=list)
    actions_types: list[str] = Field(default_factory=list)
    risques: list[str] = Field(default_factory=list)


SCENARIOS_CATALOG: list[ScenarioAudit] = [
    ScenarioAudit(
        code="conserver_optimiser",
        libelle="Conserver et optimiser",
        horizon="Court terme",
        description=(
            "Installation fonctionnellement satisfaisante. Privilegier le maintien en "
            "etat et l'optimisation fine (regulation, equilibrage, metrologie)."
        ),
        conditions=[
            "Productible solaire mesure ou estime acceptable.",
            "Champ capteurs en bon etat general, vieillissement maitrise.",
            "Schema hydraulique coherent et exploitable.",
        ],
        actions_types=[
            "Reglages fins de regulation et equilibrage hydraulique.",
            "Mise en place ou consolidation de la metrologie.",
            "Plan de maintenance preventive renforce.",
        ],
        risques=[
            "Derive de performance non detectee sans monitoring.",
        ],
    ),
    ScenarioAudit(
        code="rehabiliter_court_terme",
        libelle="Rehabiliter a court terme",
        horizon="6 a 18 mois",
        description=(
            "Installation presentant des defauts cibles mais recuperables sans depose "
            "lourde : intervention rapide pour restaurer la performance."
        ),
        conditions=[
            "Defauts hydrauliques ou de regulation localises.",
            "Composants encore disponibles aupres des fabricants.",
            "Pas de corrosion structurelle des capteurs ou des ballons.",
        ],
        actions_types=[
            "Reprise du schema hydraulique et du purgeage.",
            "Remplacement cible de circulateur, regulateur, vannes 3 voies.",
            "Mise a niveau de la metrologie et de la telegestion.",
        ],
        risques=[
            "Glissement de couts si defauts sous-estimes lors du diagnostic.",
        ],
    ),
    ScenarioAudit(
        code="rehabiliter_lourdement",
        libelle="Rehabiliter lourdement",
        horizon="12 a 36 mois",
        description=(
            "Refection lourde necessaire : reprise importante du champ, du stockage "
            "ou de la salle des machines, avec depose partielle puis reinstallation."
        ),
        conditions=[
            "Defauts multiples touchant plusieurs lots techniques.",
            "Vieillissement avance mais valeur residuelle exploitable.",
            "Besoin couvert toujours pertinent a long terme.",
        ],
        actions_types=[
            "Reprise complete du champ capteurs et de la fixation.",
            "Remplacement du stockage solaire, des echangeurs et des vases.",
            "Reecriture de l'analyse fonctionnelle et reprise de la regulation.",
        ],
        risques=[
            "Indisponibilite prolongee pendant les travaux.",
            "Surcouts si interference avec le reseau ECS existant.",
        ],
    ),
    ScenarioAudit(
        code="redimensionner",
        libelle="Redimensionner l'installation",
        horizon="12 a 24 mois",
        description=(
            "Installation surdimensionnee ou sous-dimensionnee par rapport au besoin "
            "reel : adapter le champ ou le stockage pour caler le productible."
        ),
        conditions=[
            "Surdimensionnement avere (taux de couverture solaire excessif).",
            "Usage modifie depuis la mise en service (saisonnalite, occupation).",
            "Risque de surchauffe estivale recurrent.",
        ],
        actions_types=[
            "Reduction du nombre de capteurs ou bridage de rangees.",
            "Ajustement du volume de stockage solaire.",
            "Reetude du schema de couplage a l'appoint.",
        ],
        risques=[
            "Mauvaise estimation du besoin futur (renovation thermique, usage).",
        ],
    ),
    ScenarioAudit(
        code="remplacer",
        libelle="Remplacer l'installation",
        horizon="12 a 36 mois",
        description=(
            "Installation en fin de vie technique ou economique : remplacement par "
            "une nouvelle installation solaire thermique ou par un autre vecteur."
        ),
        conditions=[
            "Fabricant disparu, pieces detachees indisponibles.",
            "Corrosion generalisee, fuites recurrentes.",
            "Cout d'exploitation superieur au gain energetique.",
        ],
        actions_types=[
            "Etude de faisabilite d'une nouvelle installation solaire.",
            "Comparaison multi-vecteurs (solaire, PAC, biomasse, recuperation).",
            "Programmation de la depose et du recyclage.",
        ],
        risques=[
            "Delai de decision long si arbitrage budgetaire complexe.",
        ],
    ),
    ScenarioAudit(
        code="abandonner",
        libelle="Abandonner l'installation",
        horizon="Court terme",
        description=(
            "Installation non recuperable ou sans valeur d'usage : deposer sans "
            "remplacement solaire, securiser le reseau ECS residuel."
        ),
        conditions=[
            "Usage du batiment supprime ou tres fortement reduit.",
            "Installation hors service, dangereuse ou non reparable.",
            "Aucun ROI envisageable meme apres rehabilitation.",
        ],
        actions_types=[
            "Depose du champ et neutralisation hydraulique.",
            "Reprise des appoints pour assurer la continuite ECS.",
            "Communication aux exploitants et au gestionnaire.",
        ],
        risques=[
            "Perte d'image / objectifs energie-climat non tenus.",
        ],
    ),
    ScenarioAudit(
        code="portefeuille_multi_batiments",
        libelle="Strategie portefeuille multi-batiments",
        horizon="24 a 60 mois",
        description=(
            "Plusieurs installations comparables : hierarchiser les interventions, "
            "mutualiser les marches et capitaliser sur un retour d'experience commun."
        ),
        conditions=[
            "Au moins trois installations du meme maitre d'ouvrage.",
            "Donnees d'exploitation comparables disponibles.",
            "Volonte de pilotage de parc a moyen terme.",
        ],
        actions_types=[
            "Hierarchisation P1/P2/P3 sur le portefeuille.",
            "Marche-cadre maintenance / instrumentation mutualise.",
            "Tableau de bord de suivi consolide (productible, disponibilite).",
        ],
        risques=[
            "Disparite technique entre sites mal prise en compte.",
        ],
    ),
]


SCENARIOS_BY_CODE: dict[str, ScenarioAudit] = {sc.code: sc for sc in SCENARIOS_CATALOG}


def get_scenario(code: str) -> Optional[ScenarioAudit]:
    return SCENARIOS_BY_CODE.get(code)


def list_scenario_codes() -> list[str]:
    return [sc.code for sc in SCENARIOS_CATALOG]


# ---------------------------------------------------------------------------
# Bibliotheque de formulations OPT'HELIOS
# ---------------------------------------------------------------------------


class FormulationType(BaseModel):
    """Formulation type capitalisee a partir des rapports OPT'HELIOS."""

    code: str
    titre: str
    theme: str = ""
    constat: str = ""
    impact: str = ""
    recommandation: str = ""
    mots_cles: list[str] = Field(default_factory=list)


FORMULATIONS_CATALOG: list[FormulationType] = [
    FormulationType(
        code="schema_hydraulique_incoherent",
        titre="Schema hydraulique incoherent",
        theme="Hydraulique",
        constat=(
            "Le schema hydraulique en place ne correspond pas a l'analyse fonctionnelle "
            "attendue : raccordements croises, sens d'ecoulement non garanti, organes "
            "d'equilibrage absents ou mal positionnes."
        ),
        impact=(
            "Productible solaire degrade, risque de stratification inversee du stockage, "
            "difficulte a diagnostiquer un defaut futur faute de schema de reference."
        ),
        recommandation=(
            "Reprendre le schema hydraulique sur la base des releves terrain, le faire "
            "valider par le bureau d'etudes et l'afficher en chaufferie."
        ),
        mots_cles=["schema", "hydraulique", "incoherent", "raccordement"],
    ),
    FormulationType(
        code="surdimensionnement",
        titre="Installation surdimensionnee",
        theme="Dimensionnement",
        constat=(
            "Le ratio surface capteurs / besoin ECS conduit a un taux de couverture "
            "solaire excessif au regard de l'usage reel observe sur site."
        ),
        impact=(
            "Surchauffes estivales recurrentes, sollicitation accrue des organes de "
            "securite, vieillissement premature du fluide caloporteur."
        ),
        recommandation=(
            "Etudier un bridage de rangees ou une reduction du champ, recaler le volume "
            "de stockage solaire et revoir la strategie de dissipation thermique."
        ),
        mots_cles=["surdimensionnement", "surchauffe", "stagnation"],
    ),
    FormulationType(
        code="metrologie_insuffisante",
        titre="Metrologie insuffisante",
        theme="Metrologie",
        constat=(
            "Les points de mesure indispensables (temperature depart/retour capteurs, "
            "comptage d'energie solaire, debit primaire) sont absents, hors service ou "
            "non raccordes a la telegestion."
        ),
        impact=(
            "Impossible de mesurer le productible reel, de detecter une derive de "
            "performance ou de justifier les eventuelles aides a l'exploitation."
        ),
        recommandation=(
            "Mettre en place un comptage d'energie solaire conforme, instrumenter les "
            "points critiques et remonter les valeurs vers la GTC/telegestion."
        ),
        mots_cles=["metrologie", "comptage", "instrumentation"],
    ),
    FormulationType(
        code="maintenance_insuffisante",
        titre="Maintenance insuffisante",
        theme="Exploitation",
        constat=(
            "Aucun contrat de maintenance specifique au solaire thermique n'est en "
            "place ; les visites se limitent a un controle visuel sans releve exploitable."
        ),
        impact=(
            "Defauts non detectes en exploitation, productible non garanti, perte de "
            "tracabilite en cas de litige fournisseur."
        ),
        recommandation=(
            "Mettre en place un plan de maintenance solaire dedie, incluant releves "
            "periodiques, controle de la qualite du fluide et entretien des capteurs."
        ),
        mots_cles=["maintenance", "exploitation", "contrat"],
    ),
    FormulationType(
        code="capteurs_integres_fabricant_disparu",
        titre="Capteurs integres / fabricant disparu",
        theme="Capteurs",
        constat=(
            "Les capteurs sont d'un modele integre en toiture dont le fabricant n'est "
            "plus actif sur le marche : aucune piece detachee ni equivalent disponible."
        ),
        impact=(
            "Toute defaillance d'un capteur engendre une depose partielle de toiture et "
            "un remplacement non standard, a cout et delai eleves."
        ),
        recommandation=(
            "Anticiper une strategie de remplacement coordonnee avec la refection de la "
            "couverture ; prevoir un budget de remplacement a moyen terme."
        ),
        mots_cles=["capteurs", "integres", "fabricant", "obsolescence"],
    ),
    FormulationType(
        code="autovidangeable_recuperable",
        titre="Installation autovidangeable recuperable",
        theme="Conception",
        constat=(
            "L'installation est de type autovidangeable (drain-back) et presente des "
            "defauts ponctuels mais reste fonctionnellement recuperable."
        ),
        impact=(
            "Le principe drain-back limite le risque de stagnation et reste pertinent ; "
            "les defauts observes relevent de la conception fine et de la mise en oeuvre."
        ),
        recommandation=(
            "Conserver le principe drain-back, corriger les pentes, le dimensionnement "
            "du reservoir et l'etancheite aux points bas avant relance complete."
        ),
        mots_cles=["autovidangeable", "drain-back", "recuperable"],
    ),
    FormulationType(
        code="sportive_peu_utilisee_ete",
        titre="Installation sportive peu utilisee l'ete",
        theme="Usage",
        constat=(
            "Le batiment est a dominante sportive avec une frequentation tres reduite "
            "en periode estivale, alors que le productible solaire est maximal."
        ),
        impact=(
            "Decalage structurel entre production solaire et besoin ECS : surchauffes "
            "estivales et productible valorise faible."
        ),
        recommandation=(
            "Adapter le dimensionnement a l'usage reel hors ete ; etudier une "
            "valorisation alternative (prechauffage piscine, ECS mutualisee)."
        ),
        mots_cles=["sport", "usage", "saisonnalite"],
    ),
    FormulationType(
        code="diagnostic_multi_batiments",
        titre="Diagnostic multi-batiments",
        theme="Portefeuille",
        constat=(
            "Le maitre d'ouvrage exploite plusieurs installations comparables sans "
            "vision consolidee de leur etat ni strategie de hierarchisation."
        ),
        impact=(
            "Allocation budgetaire non optimale, retours d'experience non capitalises, "
            "risque d'investir sur des sites moins prioritaires."
        ),
        recommandation=(
            "Mettre en place un diagnostic comparatif sur le portefeuille, hierarchiser "
            "les interventions P1/P2/P3 et mutualiser les marches de maintenance."
        ),
        mots_cles=["portefeuille", "multi-sites", "hierarchisation"],
    ),
    FormulationType(
        code="corrosion_liaison_equipotentielle",
        titre="Corrosion / liaison equipotentielle",
        theme="Securite",
        constat=(
            "Presence de corrosion sur les organes hydrauliques associee a une liaison "
            "equipotentielle absente ou non conforme sur le champ capteurs."
        ),
        impact=(
            "Risque electrique et risque de fuite a moyen terme ; non-conformite "
            "potentielle vis-a-vis des regles de l'art et des assurances."
        ),
        recommandation=(
            "Retablir la liaison equipotentielle conformement aux regles en vigueur, "
            "traiter la corrosion et remplacer les organes les plus degrades."
        ),
        mots_cles=["corrosion", "equipotentielle", "securite"],
    ),
    FormulationType(
        code="traceur_electrique",
        titre="Traceur electrique sur boucle solaire",
        theme="Hors-gel",
        constat=(
            "La protection hors-gel du primaire solaire est assuree par un traceur "
            "electrique, dispositif non conforme a l'esprit d'une installation solaire "
            "thermique econome en energie."
        ),
        impact=(
            "Consommation electrique parasite, perte de coherence energetique du projet, "
            "risque en cas de defaut d'alimentation du traceur."
        ),
        recommandation=(
            "Supprimer le traceur, basculer vers une protection hors-gel par fluide "
            "caloporteur adapte ou vers un schema drain-back si possible."
        ),
        mots_cles=["traceur", "hors-gel", "antigel"],
    ),
]


FORMULATIONS_BY_CODE: dict[str, FormulationType] = {f.code: f for f in FORMULATIONS_CATALOG}


def get_formulation(code: str) -> Optional[FormulationType]:
    return FORMULATIONS_BY_CODE.get(code)


def list_formulation_codes() -> list[str]:
    return [f.code for f in FORMULATIONS_CATALOG]


def search_formulations(query: str) -> list[FormulationType]:
    """Recherche simple sur titre, theme, mots-cles et corps de la formulation."""

    if not query:
        return list(FORMULATIONS_CATALOG)

    needle = query.strip().lower()
    if not needle:
        return list(FORMULATIONS_CATALOG)

    matches: list[FormulationType] = []
    for formulation in FORMULATIONS_CATALOG:
        haystack_parts = [
            formulation.titre,
            formulation.theme,
            formulation.constat,
            formulation.impact,
            formulation.recommandation,
            " ".join(formulation.mots_cles),
        ]
        haystack = " ".join(haystack_parts).lower()
        if needle in haystack:
            matches.append(formulation)
    return matches


# ---------------------------------------------------------------------------
# Selections persistees dans l'audit
# ---------------------------------------------------------------------------


class ScenarioSelection(BaseModel):
    """Scenario retenu dans le cadre de l'audit, avec justification libre."""

    code: str
    retenu: bool = False
    commentaire: str = ""


class FormulationSelection(BaseModel):
    """Formulation OPT'HELIOS appliquee a l'audit en cours."""

    code: str
    section: str = ""
    controle_id: Optional[str] = None
    constat_personnalise: Optional[str] = None
    impact_personnalise: Optional[str] = None
    recommandation_personnalisee: Optional[str] = None


class AuditStudioBlock(BaseModel):
    """Conteneur agrege pour les briques Audit Studio dans le modele Audit."""

    mode_rapport: ModeRapport = ModeRapport.audit_complet
    scenarios: list[ScenarioSelection] = Field(default_factory=list)
    formulations: list[FormulationSelection] = Field(default_factory=list)
    note_strategique: str = ""

    def get_scenario_selection(self, code: str) -> Optional[ScenarioSelection]:
        for sel in self.scenarios:
            if sel.code == code:
                return sel
        return None

    def upsert_scenario(
        self,
        code: str,
        retenu: bool,
        commentaire: str = "",
    ) -> ScenarioSelection:
        existing = self.get_scenario_selection(code)
        if existing is None:
            existing = ScenarioSelection(code=code, retenu=retenu, commentaire=commentaire)
            self.scenarios.append(existing)
        else:
            existing.retenu = retenu
            existing.commentaire = commentaire
        return existing

    def add_formulation(
        self,
        code: str,
        section: str = "",
        controle_id: Optional[str] = None,
        constat_personnalise: Optional[str] = None,
        impact_personnalise: Optional[str] = None,
        recommandation_personnalisee: Optional[str] = None,
    ) -> FormulationSelection:
        selection = FormulationSelection(
            code=code,
            section=section,
            controle_id=controle_id,
            constat_personnalise=constat_personnalise,
            impact_personnalise=impact_personnalise,
            recommandation_personnalisee=recommandation_personnalisee,
        )
        self.formulations.append(selection)
        return selection

    def remove_formulation(self, index: int) -> None:
        if 0 <= index < len(self.formulations):
            self.formulations.pop(index)

    def selected_scenarios(self) -> list[ScenarioSelection]:
        return [sel for sel in self.scenarios if sel.retenu]


def _lookup_audit(session_state) -> object:
    """Recupere l'audit courant depuis differents types de container.

    Supporte :
    - ``st.session_state`` (objet avec ``.get`` style dict) ;
    - mapping/dict simple ;
    - objet exposant ``audit`` ou ``current_audit`` en attribut (compat ancien
      code qui n'utilisait pas encore ``st.session_state``).
    """

    if session_state is None:
        return None

    get = getattr(session_state, "get", None)
    if callable(get):
        audit = get("audit")
        if audit is None:
            audit = get("current_audit")
        if audit is not None:
            return audit

    for attr in ("audit", "current_audit"):
        candidate = getattr(session_state, attr, None)
        if candidate is not None:
            return candidate

    return None


def render_studio_markdown_lines(studio: Optional["AuditStudioBlock"]) -> list[str]:
    """Construit la section Markdown « Studio OPT'HELIOS » d'un rapport.

    Renvoie une liste de lignes prete a etre concatenee au reste du document.
    Retourne une liste vide si le bloc studio est absent (retrocompatibilite).
    """

    if studio is None:
        return []

    lines: list[str] = ["", "## Studio OPT'HELIOS"]
    lines.append(
        "Mode de rapport : "
        + MODE_RAPPORT_LABELS.get(studio.mode_rapport.value, studio.mode_rapport.value)
    )

    selected = studio.selected_scenarios()
    if selected:
        lines.append("")
        lines.append("### Scenarios retenus")
        for sel in selected:
            scenario = SCENARIOS_BY_CODE.get(sel.code)
            title = scenario.libelle if scenario else sel.code
            horizon = f" ({scenario.horizon})" if scenario and scenario.horizon else ""
            lines.append(f"- **{title}**{horizon}")
            if sel.commentaire:
                lines.append(f"  - {sel.commentaire}")

    if studio.formulations:
        lines.append("")
        lines.append("### Formulations OPT'HELIOS appliquees")
        for applied in studio.formulations:
            template = FORMULATIONS_BY_CODE.get(applied.code)
            title = template.titre if template else applied.code
            section = applied.section or (template.theme if template else "")
            lines.append(f"- **{title}** — {section}")
            constat = applied.constat_personnalise or (template.constat if template else "")
            if constat:
                lines.append(f"  - Constat : {constat}")

    if studio.note_strategique:
        lines.append("")
        lines.append("### Note strategique")
        lines.append(studio.note_strategique)

    return lines


def extract_studio_from_session(session_state) -> Optional[AuditStudioBlock]:
    """Recupere proprement le bloc Studio depuis le ``st.session_state``.

    Retourne ``None`` si aucun audit n'est en session ou si l'audit charge est
    issu d'un ancien JSON sans bloc studio (compatibilite ascendante).
    """

    audit = _lookup_audit(session_state)
    if audit is None:
        return None

    studio = getattr(audit, "studio", None)
    if isinstance(studio, AuditStudioBlock):
        return studio
    return None
