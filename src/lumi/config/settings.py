"""Pydantic Settings — config.yaml + environment overrides."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from lumi.config.extensions import (
    DEFAULT_POSTER_EXTENSIONS,
    DEFAULT_POSTER_FILE_NAME,
    DEFAULT_VIDEO_EXTENSIONS,
)


class LibrarySettings(BaseModel):
    root_path: str = ""

    @field_validator("root_path", mode="before")
    @classmethod
    def _coerce_to_str(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)


class SmbSettings(BaseModel):
    hostname: str = ""
    share_name: str = ""
    domain: str = ""
    username: str = ""
    password: str = ""

    @field_validator("hostname", "share_name", "domain", "username", "password", mode="before")
    @classmethod
    def _coerce_to_str(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)


class CacheSettings(BaseModel):
    library_json: str = ""
    posters: str = ""

    @field_validator("library_json", "posters", mode="before")
    @classmethod
    def _coerce_to_str(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)


class PlayerSettings(BaseModel):
    command: list[str] = Field(default_factory=lambda: ["mpv", "{path}"])


class WindowSettings(BaseModel):
    fullscreen: bool = False
    screen_index: int = 0

    @field_validator("screen_index", mode="before")
    @classmethod
    def _coerce_screen_index(cls, value: object) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        return int(str(value))


class ExtensionSettings(BaseModel):
    video: list[str] = Field(default_factory=lambda: sorted(DEFAULT_VIDEO_EXTENSIONS))
    poster: list[str] = Field(default_factory=lambda: sorted(DEFAULT_POSTER_EXTENSIONS))
    poster_file_name: str = DEFAULT_POSTER_FILE_NAME

    @field_validator("video", "poster", mode="before")
    @classmethod
    def _ensure_dot_prefix(cls, value: list[str]) -> list[str]:
        return [ext if ext.startswith(".") else f".{ext}" for ext in value]

    @field_validator("poster_file_name", mode="before")
    @classmethod
    def _coerce_poster_file_name(cls, value: object) -> str:
        if value is None:
            return DEFAULT_POSTER_FILE_NAME
        return str(value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LUMI_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    mode: Literal["mock", "smb"] = "mock"
    config_path: Path = Field(default=Path("config.yaml"))
    library: LibrarySettings = Field(default_factory=LibrarySettings)
    smb: SmbSettings = Field(default_factory=SmbSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    player: PlayerSettings = Field(default_factory=PlayerSettings)
    window: WindowSettings = Field(default_factory=WindowSettings)
    extensions: ExtensionSettings = Field(default_factory=ExtensionSettings)

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_flat_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if "library_root" in normalized:
            normalized.setdefault("library", {})["root_path"] = normalized.pop("library_root")
        for legacy_key, nested_key in (
            ("smb_hostname", "hostname"),
            ("smb_share_name", "share_name"),
            ("smb_domain", "domain"),
            ("smb_username", "username"),
            ("smb_password", "password"),
        ):
            if legacy_key in normalized:
                normalized.setdefault("smb", {})[nested_key] = normalized.pop(legacy_key)
        if "cache_library_json" in normalized:
            normalized.setdefault("cache", {})["library_json"] = normalized.pop("cache_library_json")
        if "cache_posters" in normalized:
            normalized.setdefault("cache", {})["posters"] = normalized.pop("cache_posters")
        if "player_command" in normalized:
            normalized.setdefault("player", {})["command"] = normalized.pop("player_command")
        if "video_extensions" in normalized:
            normalized.setdefault("extensions", {})["video"] = normalized.pop("video_extensions")
        if "poster_extensions" in normalized:
            normalized.setdefault("extensions", {})["poster"] = normalized.pop("poster_extensions")
        if "poster_file_name" in normalized:
            normalized.setdefault("extensions", {})["poster_file_name"] = normalized.pop("poster_file_name")
        return normalized

    @property
    def library_root(self) -> str:
        return self.library.root_path

    @property
    def smb_hostname(self) -> str:
        return self.smb.hostname

    @property
    def smb_share_name(self) -> str:
        return self.smb.share_name

    @property
    def smb_domain(self) -> str:
        return self.smb.domain

    @property
    def smb_username(self) -> str:
        return self.smb.username

    @property
    def smb_password(self) -> str:
        return self.smb.password

    @property
    def cache_library_json(self) -> str:
        return self.cache.library_json

    @property
    def cache_posters(self) -> str:
        return self.cache.posters

    @property
    def player_command(self) -> list[str]:
        return self.player.command

    @property
    def video_extensions(self) -> list[str]:
        return self.extensions.video

    @property
    def poster_extensions(self) -> list[str]:
        return self.extensions.poster

    @property
    def poster_file_name(self) -> str:
        return self.extensions.poster_file_name


def _load_yaml_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


@lru_cache
def get_settings() -> Settings:
    import os

    config_path = Path(os.environ.get("LUMI_CONFIG", "config.yaml"))
    yaml_data: dict[str, object] = _load_yaml_config(config_path)
    if library_root := os.environ.get("LUMI_LIBRARY_ROOT"):
        library_section = yaml_data.setdefault("library", {})
        if isinstance(library_section, dict):
            library_section["root_path"] = library_root
    if smb_password := os.environ.get("LUMI_SMB_PASSWORD"):
        smb_section = yaml_data.setdefault("smb", {})
        if isinstance(smb_section, dict):
            smb_section["password"] = smb_password
    return Settings(config_path=config_path, **yaml_data)  # type: ignore[arg-type]
