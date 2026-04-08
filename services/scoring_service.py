from domain.enums import Verdict
from domain.models import Audit, SyntheseAudit


def compute_synthese(audit: Audit) -> SyntheseAudit:
    constats = audit.constats
    total = len(constats)

    nb_conformes = len([c for c in constats if c.verdict == Verdict.CONFORME])
    nb_defauts = len([c for c in constats if c.verdict == Verdict.DEFAUT])
    nb_non_controlables = len([c for c in constats if c.verdict == Verdict.NON_CONTROLABLE])
    nb_sans_objet = len([c for c in constats if c.verdict == Verdict.SANS_OBJET])
    nb_non_renseignes = len([c for c in constats if c.verdict == Verdict.NON_RENSEIGNE])
    nb_preuves = len(audit.preuves)

    total_evaluables = total - nb_sans_objet
    total_renseignes = total - nb_non_renseignes

    if total > 0:
        score_completude = round((total_renseignes / total) * 100, 1)
    else:
        score_completude = 0.0

    if total_evaluables > 0:
        score_global = round((nb_conformes / total_evaluables) * 100, 1)
    else:
        score_global = 0.0

    if nb_defauts >= 3:
        niveau_risque = "élevé"
    elif nb_defauts >= 1:
        niveau_risque = "modéré"
    else:
        niveau_risque = "faible"

    resume_executif = (
        f"L'audit comporte {total} contrôles, dont {nb_conformes} conformes, "
        f"{nb_defauts} défauts, {nb_non_controlables} non contrôlables, "
        f"{nb_sans_objet} sans objet et {nb_non_renseignes} non renseignés."
    )

    return SyntheseAudit(
        nb_controles_total=total,
        nb_conformes=nb_conformes,
        nb_defauts=nb_defauts,
        nb_non_controlables=nb_non_controlables,
        nb_sans_objet=nb_sans_objet,
        nb_non_renseignes=nb_non_renseignes,
        nb_preuves=nb_preuves,
        score_global_sur_100=score_global,
        score_completude_sur_100=score_completude,
        niveau_risque=niveau_risque,
        resume_executif=resume_executif,
    )