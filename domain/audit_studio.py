"""OPT'HELIOS Audit Studio — modules métier additionnels.

Ce module apporte deux briques inspirées du prototype Audit Solaire Builder V2 :

- un catalogue de **scénarios de décision** d'audit solaire thermique (conserver,
  réhabiliter, redimensionner, remplacer, abandonner, portefeuille multi-bâtiments) ;
- une **bibliothèque de formulations types OPT'HELIOS** capitalisée sur les rapports
  réels (schémas incohérents, surdimensionnement, capteurs intégrés, etc.).

Ces structures sont volontairement décrites comme des données simples (Pydantic +
constantes) afin de pouvoir être :

* exposées dans l'interface Streamlit (sélecteurs, expanders) ;
* sérialisées dans le JSON d'audit sans casser les audits existants ;
* exploitées par l'export DOCX/Markdown pour enrichir le rapport final.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Mode de rapport
# ---------------------------------------------------------------------------


class ModeRapport(str, Enum):
    """Profil éditorial du livrable produit par l'auditeur."""

    audit_complet = "audit_complet"
    diagnostic_court = "diagnostic_court"


MODE_RAPPORT_LABELS: dict[str, str] = {
    ModeRapport.audit_complet.value: "Audit complet (rapport détaillé)",
    ModeRapport.diagnostic_court.value: "Diagnostic court (note de synthèse)",
}


MODE_RAPPORT_DESCRIPTIONS: dict[str, str] = {
    ModeRapport.audit_complet.value: (
        "Rapport long format avec contexte, méthodologie détaillée, constats par "
        "section, plan d'actions priorisé et annexes documentaires complètes."
    ),
    ModeRapport.diagnostic_court.value: (
        "Note de synthèse resserrée : appréciation globale, principaux constats, "
        "scénarios envisagés et recommandations prioritaires uniquement."
    ),
}


# ---------------------------------------------------------------------------
# Scénarios d'audit
# ---------------------------------------------------------------------------


class ScenarioAudit(BaseModel):
    """Décrit un scénario de décision proposé à l'issue de l'audit."""

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
            "Installation fonctionnellement satisfaisante. Privilégier le maintien en "
            "état et l'optimisation fine (régulation, équilibrage, métrologie)."
        ),
        conditions=[
            "Productible solaire mesuré ou estimé acceptable.",
            "Champ capteurs en bon état général, vieillissement maîtrisé.",
            "Schéma hydraulique cohérent et exploitable.",
        ],
        actions_types=[
            "Réglages fins de régulation et équilibrage hydraulique.",
            "Mise en place ou consolidation de la métrologie.",
            "Plan de maintenance préventive renforcé.",
        ],
        risques=[
            "Dérive de performance non détectée sans monitoring.",
        ],
    ),
    ScenarioAudit(
        code="rehabiliter_court_terme",
        libelle="Réhabiliter à court terme",
        horizon="6 à 18 mois",
        description=(
            "Installation présentant des défauts ciblés mais récupérables sans dépose "
            "lourde : intervention rapide pour restaurer la performance."
        ),
        conditions=[
            "Défauts hydrauliques ou de régulation localisés.",
            "Composants encore disponibles auprès des fabricants.",
            "Pas de corrosion structurelle des capteurs ou des ballons.",
        ],
        actions_types=[
            "Reprise du schéma hydraulique et du purgeage.",
            "Remplacement ciblé de circulateur, régulateur, vannes 3 voies.",
            "Mise à niveau de la métrologie et de la télégestion.",
        ],
        risques=[
            "Glissement de coûts si défauts sous-estimés lors du diagnostic.",
        ],
    ),
    ScenarioAudit(
        code="rehabiliter_lourdement",
        libelle="Réhabiliter lourdement",
        horizon="12 à 36 mois",
        description=(
            "Réfection lourde nécessaire : reprise importante du champ, du stockage "
            "ou de la salle des machines, avec dépose partielle puis réinstallation."
        ),
        conditions=[
            "Défauts multiples touchant plusieurs lots techniques.",
            "Vieillissement avancé mais valeur résiduelle exploitable.",
            "Besoin couvert toujours pertinent à long terme.",
        ],
        actions_types=[
            "Reprise complète du champ capteurs et de la fixation.",
            "Remplacement du stockage solaire, des échangeurs et des vases.",
            "Réécriture de l'analyse fonctionnelle et reprise de la régulation.",
        ],
        risques=[
            "Indisponibilité prolongée pendant les travaux.",
            "Surcoûts si interférence avec le réseau ECS existant.",
        ],
    ),
    ScenarioAudit(
        code="redimensionner",
        libelle="Redimensionner l'installation",
        horizon="12 à 24 mois",
        description=(
            "Installation surdimensionnée ou sous-dimensionnée par rapport au besoin "
            "réel : adapter le champ ou le stockage pour caler le productible."
        ),
        conditions=[
            "Surdimensionnement avéré (taux de couverture solaire excessif).",
            "Usage modifié depuis la mise en service (saisonnalité, occupation).",
            "Risque de surchauffe estivale récurrent.",
        ],
        actions_types=[
            "Réduction du nombre de capteurs ou bridage de rangées.",
            "Ajustement du volume de stockage solaire.",
            "Réétude du schéma de couplage à l'appoint.",
        ],
        risques=[
            "Mauvaise estimation du besoin futur (rénovation thermique, usage).",
        ],
    ),
    ScenarioAudit(
        code="remplacer",
        libelle="Remplacer l'installation",
        horizon="12 à 36 mois",
        description=(
            "Installation en fin de vie technique ou économique : remplacement par "
            "une nouvelle installation solaire thermique ou par un autre vecteur."
        ),
        conditions=[
            "Fabricant disparu, pièces détachées indisponibles.",
            "Corrosion généralisée, fuites récurrentes.",
            "Coût d'exploitation supérieur au gain énergétique.",
        ],
        actions_types=[
            "Étude de faisabilité d'une nouvelle installation solaire.",
            "Comparaison multi-vecteurs (solaire, PAC, biomasse, récupération).",
            "Programmation de la dépose et du recyclage.",
        ],
        risques=[
            "Délai de décision long si arbitrage budgétaire complexe.",
        ],
    ),
    ScenarioAudit(
        code="abandonner",
        libelle="Abandonner l'installation",
        horizon="Court terme",
        description=(
            "Installation non récupérable ou sans valeur d'usage : déposer sans "
            "remplacement solaire, sécuriser le réseau ECS résiduel."
        ),
        conditions=[
            "Usage du bâtiment supprimé ou très fortement réduit.",
            "Installation hors service, dangereuse ou non réparable.",
            "Aucun ROI envisageable même après réhabilitation.",
        ],
        actions_types=[
            "Dépose du champ et neutralisation hydraulique.",
            "Reprise des appoints pour assurer la continuité ECS.",
            "Communication aux exploitants et au gestionnaire.",
        ],
        risques=[
            "Perte d'image / objectifs énergie-climat non tenus.",
        ],
    ),
    ScenarioAudit(
        code="portefeuille_multi_batiments",
        libelle="Stratégie portefeuille multi-bâtiments",
        horizon="24 à 60 mois",
        description=(
            "Plusieurs installations comparables : hiérarchiser les interventions, "
            "mutualiser les marchés et capitaliser sur un retour d'expérience commun."
        ),
        conditions=[
            "Au moins trois installations du même maître d'ouvrage.",
            "Données d'exploitation comparables disponibles.",
            "Volonté de pilotage de parc à moyen terme.",
        ],
        actions_types=[
            "Hiérarchisation P1/P2/P3 sur le portefeuille.",
            "Marché-cadre maintenance / instrumentation mutualisé.",
            "Tableau de bord de suivi consolidé (productible, disponibilité).",
        ],
        risques=[
            "Disparité technique entre sites mal prise en compte.",
        ],
    ),
]


SCENARIOS_BY_CODE: dict[str, ScenarioAudit] = {sc.code: sc for sc in SCENARIOS_CATALOG}


def get_scenario(code: str) -> Optional[ScenarioAudit]:
    return SCENARIOS_BY_CODE.get(code)


def list_scenario_codes() -> list[str]:
    return [sc.code for sc in SCENARIOS_CATALOG]


# ---------------------------------------------------------------------------
# Bibliothèque de formulations OPT'HELIOS
# ---------------------------------------------------------------------------


class FormulationType(BaseModel):
    """Formulation type capitalisée à partir des rapports OPT'HELIOS."""

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
        titre="Schéma hydraulique incohérent",
        theme="Hydraulique",
        constat=(
            "Le schéma hydraulique en place ne correspond pas à l'analyse fonctionnelle "
            "attendue : raccordements croisés, sens d'écoulement non garanti, organes "
            "d'équilibrage absents ou mal positionnés."
        ),
        impact=(
            "Productible solaire dégradé, risque de stratification inversée du stockage, "
            "difficulté à diagnostiquer un défaut futur faute de schéma de référence."
        ),
        recommandation=(
            "Reprendre le schéma hydraulique sur la base des relevés terrain, le faire "
            "valider par le bureau d'études et l'afficher en chaufferie."
        ),
        mots_cles=["schéma", "hydraulique", "incohérent", "raccordement"],
    ),
    FormulationType(
        code="surdimensionnement",
        titre="Installation surdimensionnée",
        theme="Dimensionnement",
        constat=(
            "Le ratio surface capteurs / besoin ECS conduit à un taux de couverture "
            "solaire excessif au regard de l'usage réel observé sur site."
        ),
        impact=(
            "Surchauffes estivales récurrentes, sollicitation accrue des organes de "
            "sécurité, vieillissement prématuré du fluide caloporteur."
        ),
        recommandation=(
            "Étudier un bridage de rangées ou une réduction du champ, recaler le volume "
            "de stockage solaire et revoir la stratégie de dissipation thermique."
        ),
        mots_cles=["surdimensionnement", "surchauffe", "stagnation"],
    ),
    FormulationType(
        code="metrologie_insuffisante",
        titre="Métrologie insuffisante",
        theme="Métrologie",
        constat=(
            "Les points de mesure indispensables (température départ/retour capteurs, "
            "comptage d'énergie solaire, débit primaire) sont absents, hors service ou "
            "non raccordés à la télégestion."
        ),
        impact=(
            "Impossible de mesurer le productible réel, de détecter une dérive de "
            "performance ou de justifier les éventuelles aides à l'exploitation."
        ),
        recommandation=(
            "Mettre en place un comptage d'énergie solaire conforme, instrumenter les "
            "points critiques et remonter les valeurs vers la GTC/télégestion."
        ),
        mots_cles=["métrologie", "comptage", "instrumentation"],
    ),
    FormulationType(
        code="maintenance_insuffisante",
        titre="Maintenance insuffisante",
        theme="Exploitation",
        constat=(
            "Aucun contrat de maintenance spécifique au solaire thermique n'est en "
            "place ; les visites se limitent à un contrôle visuel sans relevé exploitable."
        ),
        impact=(
            "Défauts non détectés en exploitation, productible non garanti, perte de "
            "traçabilité en cas de litige fournisseur."
        ),
        recommandation=(
            "Mettre en place un plan de maintenance solaire dédié, incluant relevés "
            "périodiques, contrôle de la qualité du fluide et entretien des capteurs."
        ),
        mots_cles=["maintenance", "exploitation", "contrat"],
    ),
    FormulationType(
        code="capteurs_integres_fabricant_disparu",
        titre="Capteurs intégrés / fabricant disparu",
        theme="Capteurs",
        constat=(
            "Les capteurs sont d'un modèle intégré en toiture dont le fabricant n'est "
            "plus actif sur le marché : aucune pièce détachée ni équivalent disponible."
        ),
        impact=(
            "Toute défaillance d'un capteur engendre une dépose partielle de toiture et "
            "un remplacement non standard, à coût et délai élevés."
        ),
        recommandation=(
            "Anticiper une stratégie de remplacement coordonnée avec la réfection de la "
            "couverture ; prévoir un budget de remplacement à moyen terme."
        ),
        mots_cles=["capteurs", "intégrés", "fabricant", "obsolescence"],
    ),
    FormulationType(
        code="autovidangeable_recuperable",
        titre="Installation autovidangeable récupérable",
        theme="Conception",
        constat=(
            "L'installation est de type autovidangeable (drain-back) et présente des "
            "défauts ponctuels mais reste fonctionnellement récupérable."
        ),
        impact=(
            "Le principe drain-back limite le risque de stagnation et reste pertinent ; "
            "les défauts observés relèvent de la conception fine et de la mise en œuvre."
        ),
        recommandation=(
            "Conserver le principe drain-back, corriger les pentes, le dimensionnement "
            "du réservoir et l'étanchéité aux points bas avant relance complète."
        ),
        mots_cles=["autovidangeable", "drain-back", "récupérable"],
    ),
    FormulationType(
        code="sportive_peu_utilisee_ete",
        titre="Installation sportive peu utilisée l'été",
        theme="Usage",
        constat=(
            "Le bâtiment est à dominante sportive avec une fréquentation très réduite "
            "en période estivale, alors que le productible solaire est maximal."
        ),
        impact=(
            "Décalage structurel entre production solaire et besoin ECS : surchauffes "
            "estivales et productible valorisé faible."
        ),
        recommandation=(
            "Adapter le dimensionnement à l'usage réel hors été ; étudier une "
            "valorisation alternative (préchauffage piscine, ECS mutualisée)."
        ),
        mots_cles=["sport", "usage", "saisonnalité"],
    ),
    FormulationType(
        code="diagnostic_multi_batiments",
        titre="Diagnostic multi-bâtiments",
        theme="Portefeuille",
        constat=(
            "Le maître d'ouvrage exploite plusieurs installations comparables sans "
            "vision consolidée de leur état ni stratégie de hiérarchisation."
        ),
        impact=(
            "Allocation budgétaire non optimale, retours d'expérience non capitalisés, "
            "risque d'investir sur des sites moins prioritaires."
        ),
        recommandation=(
            "Mettre en place un diagnostic comparatif sur le portefeuille, hiérarchiser "
            "les interventions P1/P2/P3 et mutualiser les marchés de maintenance."
        ),
        mots_cles=["portefeuille", "multi-sites", "hiérarchisation"],
    ),
    FormulationType(
        code="corrosion_liaison_equipotentielle",
        titre="Corrosion / liaison équipotentielle",
        theme="Sécurité",
        constat=(
            "Présence de corrosion sur les organes hydrauliques associée à une liaison "
            "équipotentielle absente ou non conforme sur le champ capteurs."
        ),
        impact=(
            "Risque électrique et risque de fuite à moyen terme ; non-conformité "
            "potentielle vis-à-vis des règles de l'art et des assurances."
        ),
        recommandation=(
            "Rétablir la liaison équipotentielle conformément aux règles en vigueur, "
            "traiter la corrosion et remplacer les organes les plus dégradés."
        ),
        mots_cles=["corrosion", "équipotentielle", "sécurité"],
    ),
    FormulationType(
        code="traceur_electrique",
        titre="Traceur électrique sur boucle solaire",
        theme="Hors-gel",
        constat=(
            "La protection hors-gel du primaire solaire est assurée par un traceur "
            "électrique, dispositif non conforme à l'esprit d'une installation solaire "
            "thermique économe en énergie."
        ),
        impact=(
            "Consommation électrique parasite, perte de cohérence énergétique du projet, "
            "risque en cas de défaut d'alimentation du traceur."
        ),
        recommandation=(
            "Supprimer le traceur, basculer vers une protection hors-gel par fluide "
            "caloporteur adapté ou vers un schéma drain-back si possible."
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
    """Recherche simple sur titre, thème, mots-clés et corps de la formulation."""

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
# Sélections persistées dans l'audit
# ---------------------------------------------------------------------------


class ScenarioSelection(BaseModel):
    """Scénario retenu dans le cadre de l'audit, avec justification libre."""

    code: str
    retenu: bool = False
    commentaire: str = ""


class FormulationSelection(BaseModel):
    """Formulation OPT'HELIOS appliquée à l'audit en cours."""

    code: str
    section: str = ""
    controle_id: Optional[str] = None
    constat_personnalise: Optional[str] = None
    impact_personnalise: Optional[str] = None
    recommandation_personnalisee: Optional[str] = None


class AuditStudioBlock(BaseModel):
    """Conteneur agrégé pour les briques Audit Studio dans le modèle Audit."""

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


def extract_studio_from_session(session_state) -> Optional[AuditStudioBlock]:
    """Récupère proprement le bloc Studio depuis le ``st.session_state``.

    Retourne ``None`` si aucun audit n'est en session ou si l'audit chargé est
    issu d'un ancien JSON sans bloc studio (compatibilité ascendante).
    """

    audit = None
    try:
        audit = session_state.get("audit")
    except AttributeError:
        return None

    if audit is None:
        return None

    studio = getattr(audit, "studio", None)
    if isinstance(studio, AuditStudioBlock):
        return studio
    return None
