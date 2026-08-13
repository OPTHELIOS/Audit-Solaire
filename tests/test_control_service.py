"""Tests de domain/control_service.py : cycle de vie d'un point de controle
(creation, mise a jour, reinitialisation) et gestion des preuves uploadees."""

from domain.control_catalog import CONTROL_CATALOG
from domain.control_service import (
    append_uploaded_evidences,
    get_applicable_controls,
    get_or_create_constat,
    reset_response,
    update_response,
)
from domain.models import Audit


def test_get_or_create_constat_creates_once():
    audit = Audit()
    item = CONTROL_CATALOG[0]

    constat1 = get_or_create_constat(audit, item)
    constat2 = get_or_create_constat(audit, item)

    assert constat1 is constat2
    assert len(audit.constats) == 1


def test_update_response_and_reset_response_roundtrip():
    audit = Audit()
    session_state = {"audit": audit}

    # On prend un point garanti applicable a un audit vide (pas de condition
    # d'applicabilite non satisfaite), plutot que le premier du catalogue au
    # hasard, pour ne pas dependre de l'ordre/contenu exact du catalogue.
    controle_id = get_applicable_controls(audit)[0].controle_id

    update_response(
        session_state,
        controle_id,
        verdict="non_conforme",
        observation="Fuite visible au niveau du groupe de sécurité",
        criticite_finale="critique",
    )
    constat = next(c for c in audit.constats if c.controle_id == controle_id)
    assert constat.verdict.value == "non_conforme"
    assert constat.observation == "Fuite visible au niveau du groupe de sécurité"
    assert constat.criticite_finale.value == "critique"

    reset_response(session_state, controle_id)
    constat = next(c for c in audit.constats if c.controle_id == controle_id)
    assert constat.verdict is None
    assert constat.observation is None


class _FakeUploadedFile:
    def __init__(self, name: str, content: bytes = b"data"):
        self.name = name
        self._content = content

    def getbuffer(self):
        return self._content


def test_append_uploaded_evidences_returns_all_and_new_paths(tmp_path):
    base_dir = tmp_path / "evidences"

    all_paths, new_paths = append_uploaded_evidences(
        [_FakeUploadedFile("a.jpg")],
        controle_id="CTRL-1",
        session_state={},
        existing_paths=["/already/there.jpg"],
        base_dir=str(base_dir),
    )

    assert all_paths[0] == "/already/there.jpg"
    assert len(all_paths) == 2
    assert len(new_paths) == 1
    assert new_paths[0].endswith("a.jpg")
    assert (base_dir / "CTRL-1" / "a.jpg").exists()


def test_append_uploaded_evidences_no_new_files_keeps_existing(tmp_path):
    base_dir = tmp_path / "evidences"

    all_paths, new_paths = append_uploaded_evidences(
        [],
        controle_id="CTRL-1",
        session_state={},
        existing_paths=["/already/there.jpg"],
        base_dir=str(base_dir),
    )

    assert all_paths == ["/already/there.jpg"]
    assert new_paths == []
