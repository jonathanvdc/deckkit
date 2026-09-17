"""Font requests and deterministic discovery of installed font faces."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Protocol

from PIL import ImageFont


@dataclass(frozen=True)
class Font:
    family: str
    weight: Literal["regular", "bold"] = "regular"
    italic: bool = False

    def __post_init__(self) -> None:
        if not self.family.strip():
            raise ValueError("Font family must not be empty")
        if self.weight not in ("regular", "bold"):
            raise ValueError("Supported font weights are regular and bold")


@dataclass(frozen=True)
class FontFile:
    path: str
    index: int = 0

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("Font face index must be nonnegative")


@dataclass(frozen=True)
class ResolvedFont:
    path: str
    index: int
    family: str
    style: str
    bold: bool
    italic: bool


class FontNotFoundError(ValueError):
    pass


class FontResolver(Protocol):
    def resolve(self, source: Font) -> ResolvedFont: ...


@lru_cache(maxsize=2048)
def _face(path: str, index: int) -> ResolvedFont:
    face = ImageFont.truetype(path, 16, index=index)
    family, style = face.getname()
    if not family or not style:
        raise ValueError(f"Font lacks family/style metadata: {path}")
    normalized = style.casefold()
    return ResolvedFont(
        path,
        index,
        family,
        style,
        "bold" in normalized,
        "italic" in normalized or "oblique" in normalized,
    )


def _system_directories() -> tuple[Path, ...]:
    home = Path.home()
    if sys.platform == "darwin":
        return (
            home / "Library/Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
        )
    if sys.platform == "win32":
        return (
            Path(os.environ.get("LOCALAPPDATA", str(home))) / "Microsoft/Windows/Fonts",
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        )
    return (
        home / ".fonts",
        Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))) / "fonts",
        *(
            Path(p) / "fonts"
            for p in os.environ.get(
                "XDG_DATA_DIRS", "/usr/local/share:/usr/share"
            ).split(":")
        ),
    )


class SystemFontResolver:
    """Search standard font directories, or an explicitly supplied directory set.

    Exact family and regular/bold/italic face matching only; no substitution,
    synthetic styles or variable-axis instancing. First directory wins ties.
    """

    def __init__(self, directories: tuple[Path, ...] | None = None) -> None:
        self.directories = (
            directories if directories is not None else _system_directories()
        )
        self._faces: tuple[ResolvedFont, ...] | None = None
        self._cache: dict[Font, ResolvedFont] = {}

    def _discover(self) -> tuple[ResolvedFont, ...]:
        if self._faces is None:
            faces = []
            for directory in self.directories:
                for path in sorted(directory.rglob("*")):
                    if path.suffix.lower() not in (".ttf", ".otf", ".ttc", ".otc"):
                        continue
                    count = 256 if path.suffix.lower() in (".ttc", ".otc") else 1
                    for index in range(count):
                        try:
                            faces.append(_face(str(path.resolve()), index))
                        except (OSError, ValueError):
                            break
            self._faces = tuple(faces)
        return self._faces

    def resolve(self, source: Font) -> ResolvedFont:
        if source in self._cache:
            return self._cache[source]
        if isinstance(source, Font):
            matches = [
                face
                for face in self._discover()
                if face.family.casefold() == source.family.casefold()
                and face.bold == (source.weight == "bold")
                and face.italic == source.italic
                and face.style.casefold()
                in (
                    "regular",
                    "normal",
                    "roman",
                    "book",
                    "bold",
                    "italic",
                    "oblique",
                    "bold italic",
                    "bold oblique",
                )
            ]
            if not matches:
                raise FontNotFoundError(
                    f"Font {source.family!r} ({source.weight}, italic={source.italic}) "
                    "is not installed in the searched directories. Install it, configure FileFontResolver, "
                    "or supply a FontResolver. No font was substituted."
                )
            result = matches[0]
        else:
            raise TypeError('Expected Font("Family")')
        self._cache[source] = result
        return result


class FileFontResolver:
    """Resolve named requests using pinned files, without searching system fonts.

    Mapping keys may be logical aliases. Exports use the loaded face's actual
    family/style metadata, matching the face used for measurement.
    """

    def __init__(self, files: Mapping[Font, FontFile | str]) -> None:
        self.files = MappingProxyType(
            {
                key: FontFile(value) if isinstance(value, str) else value
                for key, value in files.items()
            }
        )

    def resolve(self, source: Font) -> ResolvedFont:
        try:
            location = self.files[source]
        except KeyError:
            raise FontNotFoundError(
                f"No file mapping for {source!r}; add it to FileFontResolver"
            ) from None
        try:
            return _face(
                str(Path(location.path).expanduser().resolve()), location.index
            )
        except (OSError, ValueError) as error:
            raise FontNotFoundError(
                f"Cannot load {location.path!r}, face {location.index}"
            ) from error
