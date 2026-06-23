from __future__ import annotations
import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from platformdirs import user_data_dir

APP_NAME = "COAConverter"
DATA_DIR = user_data_dir(APP_NAME, appauthor=False)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


@dataclass
class CompanyConfig:
    company_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    logo_path: str = ""
    header_path: str = ""
    qc_release_statement: str = (
        "This material has been tested and meets all specified requirements "
        "and is hereby released for use."
    )
    signatory_name: str = ""
    signatory_title: str = "Quality Control Manager"
    cert_prefix: str = "COA"
    cert_counter: int = 1
    custom_aliases: dict = field(default_factory=dict)
    supplier_templates: dict = field(default_factory=dict)

    def is_configured(self) -> bool:
        return bool(self.company_name.strip())


def load_config() -> CompanyConfig:
    if not os.path.exists(CONFIG_PATH):
        return CompanyConfig()
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cfg = CompanyConfig()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg
    except Exception:
        return CompanyConfig()


def save_config(cfg: CompanyConfig) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


def next_cert_number(cfg: CompanyConfig) -> str:
    """Generate next certificate number and persist incremented counter."""
    number = f"{cfg.cert_prefix}-{cfg.cert_counter:05d}"
    cfg.cert_counter += 1
    save_config(cfg)
    return number


def save_logo(source_path: str) -> str:
    """Copy user-chosen logo to stable app data location. Returns new path."""
    os.makedirs(DATA_DIR, exist_ok=True)
    _, ext = os.path.splitext(source_path)
    dest = os.path.join(DATA_DIR, f"user_logo{ext}")
    shutil.copy2(source_path, dest)
    return dest


def save_header(source_path: str) -> str:
    """Copy user-chosen header image to stable app data location. Returns new path."""
    os.makedirs(DATA_DIR, exist_ok=True)
    _, ext = os.path.splitext(source_path)
    dest = os.path.join(DATA_DIR, f"user_header{ext}")
    shutil.copy2(source_path, dest)
    return dest


def save_supplier_template(cfg: CompanyConfig, supplier: str, template: dict) -> None:
    cfg.supplier_templates[supplier] = template
    save_config(cfg)


def get_data_dir() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return DATA_DIR
