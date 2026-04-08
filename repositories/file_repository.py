from pathlib import Path

DATA_DIR = Path("data")
AUDITS_DIR = DATA_DIR / "audits"


def ensure_base_dirs() -> None:
    AUDITS_DIR.mkdir(parents=True, exist_ok=True)


def get_audit_dir(audit_id: str) -> Path:
    ensure_base_dirs()
    audit_dir = AUDITS_DIR / audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def get_audit_json_path(audit_id: str) -> Path:
    return get_audit_dir(audit_id) / "audit.json"


def get_metadata_json_path(audit_id: str) -> Path:
    return get_audit_dir(audit_id) / "metadata.json"


def get_exports_dir(audit_id: str) -> Path:
    path = get_audit_dir(audit_id) / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path