"""Tests pour upload_audit_evidences (OneDrive) en mode mock."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.models import Audit, Preuve, TypePreuve
from repositories import onedrive_repository


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class TestUploadAuditEvidences(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        photo_path = self.tmp_path / "site_chaufferie.jpg"
        photo_path.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
        doc_path = self.tmp_path / "schema.pdf"
        doc_path.write_bytes(b"%PDF-1.4 fake")

        self.audit = Audit()
        self.audit.meta.numero_audit = "AUD-TEST"
        self.audit.preuves.append(
            Preuve(
                preuve_id="PRV-1",
                type_preuve=TypePreuve.photo,
                nom_fichier="site_chaufferie.jpg",
                chemin_fichier=str(photo_path),
                section="Chaufferie",
                legende="Vue d'ensemble chaufferie",
                rubrique="ambiance",
            )
        )
        self.audit.preuves.append(
            Preuve(
                preuve_id="PRV-2",
                type_preuve=TypePreuve.document,
                nom_fichier="schema.pdf",
                chemin_fichier=str(doc_path),
                section="Hydraulique",
                legende="Schéma hydraulique fourni par l'exploitant",
            )
        )
        self.audit.preuves.append(
            Preuve(
                preuve_id="PRV-3",
                type_preuve=TypePreuve.photo,
                nom_fichier="absent.jpg",
                chemin_fichier=str(self.tmp_path / "introuvable.jpg"),
                legende="Photo manquante",
            )
        )
        self.audit.preuves.append(
            Preuve(
                preuve_id="PRV-4",
                type_preuve=TypePreuve.photo,
                legende="Aucun chemin local",
            )
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_uploads_existing_files_and_skips_missing(self) -> None:
        with patch.object(onedrive_repository.requests, "put", return_value=_FakeResponse(200)) as mock_put:
            results = onedrive_repository.upload_audit_evidences(
                self.audit,
                token="fake-token",
            )

        statuses = {r["preuve_id"]: r["status"] for r in results}
        self.assertEqual(statuses["PRV-1"], "uploaded")
        self.assertEqual(statuses["PRV-2"], "uploaded")
        self.assertEqual(statuses["PRV-3"], "skipped")
        self.assertEqual(statuses["PRV-4"], "skipped")
        self.assertEqual(mock_put.call_count, 2)

        # The onedrive_path is set on successful uploads only.
        prv1 = next(p for p in self.audit.preuves if p.preuve_id == "PRV-1")
        prv3 = next(p for p in self.audit.preuves if p.preuve_id == "PRV-3")
        self.assertIsNotNone(prv1.onedrive_path)
        assert prv1.onedrive_path is not None
        self.assertIn("audits/AUD-TEST/evidences/photo/", prv1.onedrive_path)
        self.assertIsNone(prv3.onedrive_path)

    def test_progress_callback_invoked_for_each_preuve(self) -> None:
        calls: list[int] = []

        def _progress(index: int, total: int, preuve) -> None:
            calls.append(index)

        with patch.object(onedrive_repository.requests, "put", return_value=_FakeResponse(200)):
            onedrive_repository.upload_audit_evidences(
                self.audit,
                token="fake-token",
                on_progress=_progress,
            )
        # Two uploaded preuves trigger the callback (skipped ones do not).
        self.assertEqual(calls, [1, 2])

    def test_http_error_reported_per_preuve(self) -> None:
        def _put(url, **kwargs):
            if "schema.pdf" in url:
                return _FakeResponse(500)
            return _FakeResponse(200)

        with patch.object(onedrive_repository.requests, "put", side_effect=_put):
            results = onedrive_repository.upload_audit_evidences(
                self.audit,
                token="fake-token",
            )
        statuses = {r["preuve_id"]: r["status"] for r in results}
        self.assertEqual(statuses["PRV-1"], "uploaded")
        self.assertEqual(statuses["PRV-2"], "error")
        # Successful one still has onedrive_path; failed one does not.
        prv2 = next(p for p in self.audit.preuves if p.preuve_id == "PRV-2")
        self.assertIsNone(prv2.onedrive_path)

    def test_preserves_local_storage(self) -> None:
        # Local files should remain on disk after upload.
        with patch.object(onedrive_repository.requests, "put", return_value=_FakeResponse(200)):
            onedrive_repository.upload_audit_evidences(self.audit, token="fake-token")
        self.assertTrue((self.tmp_path / "site_chaufferie.jpg").exists())
        self.assertTrue((self.tmp_path / "schema.pdf").exists())

    def test_collision_basenames_yield_unique_remote_paths(self) -> None:
        # Two preuves sharing the same local basename must not overwrite each other.
        sub_a = self.tmp_path / "a"
        sub_b = self.tmp_path / "b"
        sub_a.mkdir()
        sub_b.mkdir()
        (sub_a / "photo.jpg").write_bytes(b"a-bytes")
        (sub_b / "photo.jpg").write_bytes(b"b-bytes")

        audit = Audit()
        audit.meta.numero_audit = "AUD-COLLIDE"
        audit.preuves.append(
            Preuve(
                preuve_id="PRV-A",
                type_preuve=TypePreuve.photo,
                nom_fichier="photo.jpg",
                chemin_fichier=str(sub_a / "photo.jpg"),
                ordre=1,
            )
        )
        audit.preuves.append(
            Preuve(
                preuve_id="PRV-B",
                type_preuve=TypePreuve.photo,
                nom_fichier="photo.jpg",
                chemin_fichier=str(sub_b / "photo.jpg"),
                ordre=2,
            )
        )

        urls: list[str] = []

        def _put(url, **kwargs):
            urls.append(url)
            return _FakeResponse(200)

        with patch.object(onedrive_repository.requests, "put", side_effect=_put):
            onedrive_repository.upload_audit_evidences(audit, token="fake-token")

        paths = [p.onedrive_path for p in audit.preuves]
        self.assertEqual(len(set(paths)), 2)
        self.assertEqual(len(set(urls)), 2)
        for path in paths:
            assert path is not None
            self.assertTrue(path.endswith("photo.jpg"))
            self.assertIn("PRV-", path)

    def test_audit_id_sanitization_blocks_path_traversal(self) -> None:
        audit = Audit()
        audit.meta.numero_audit = "../../etc/passwd"
        photo = self.tmp_path / "x.jpg"
        photo.write_bytes(b"x")
        audit.preuves.append(
            Preuve(
                preuve_id="PRV-X",
                type_preuve=TypePreuve.photo,
                chemin_fichier=str(photo),
            )
        )

        with patch.object(onedrive_repository.requests, "put", return_value=_FakeResponse(200)):
            onedrive_repository.upload_audit_evidences(audit, token="fake-token")

        path = audit.preuves[0].onedrive_path
        assert path is not None
        # No upward traversal should remain in the remote path.
        self.assertNotIn("..", path)
        self.assertNotIn("/etc/", path)
        self.assertTrue(path.startswith("audits/"))


class TestPreuveModelExtensions(unittest.TestCase):
    def test_extra_fields_persist_in_roundtrip(self) -> None:
        audit = Audit()
        audit.preuves.append(
            Preuve(
                type_preuve=TypePreuve.photo,
                legende="Compteur d'énergie solaire",
                rubrique="metrologie",
                ordre=2,
                onedrive_path="audits/X/evidences/photo/compteur.jpg",
            )
        )
        dumped = audit.model_dump(mode="json")
        rebuilt = Audit.model_validate(dumped)
        self.assertEqual(rebuilt.preuves[0].rubrique, "metrologie")
        self.assertEqual(rebuilt.preuves[0].ordre, 2)
        self.assertEqual(rebuilt.preuves[0].legende, "Compteur d'énergie solaire")
        self.assertEqual(
            rebuilt.preuves[0].onedrive_path,
            "audits/X/evidences/photo/compteur.jpg",
        )

    def test_legacy_preuve_without_new_fields(self) -> None:
        legacy_dump = {
            "preuve_id": "PRV-OLD",
            "type_preuve": "photo",
            "chemin_fichier": "/tmp/x.jpg",
            "legende": "Ancien",
        }
        preuve = Preuve.model_validate(legacy_dump)
        self.assertIsNone(preuve.onedrive_path)
        self.assertEqual(preuve.ordre, 0)
        self.assertIsNone(preuve.rubrique)


if __name__ == "__main__":
    unittest.main()
