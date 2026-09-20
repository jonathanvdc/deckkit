from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image as PILImage

from ..context import Context
from ..expanded_views import ExpandedImage, ExpandedMetadata
from ..layouts import ImageLayout
from ..units import inch
from .primitive_view import PrimitiveView


@dataclass(frozen=True)
class Image(PrimitiveView):
    source: str
    fit: Literal["contain", "cover"] = "contain"
    dpi: float = 96

    def __post_init__(self) -> None:
        from math import isfinite

        if not isfinite(self.dpi) or self.dpi <= 0:
            raise ValueError("Image DPI must be finite and positive")
        if self.fit not in ("contain", "cover"):
            raise ValueError("Image fit must be contain or cover")

    def expand(self, context: Context, metadata: ExpandedMetadata) -> ExpandedImage:
        data = Path(self.source).read_bytes()
        with PILImage.open(BytesIO(data)) as image:
            width, height = image.size
            mime = PILImage.MIME[image.format or ""]
        return ExpandedImage(
            metadata,
            ImageLayout(inch(width / self.dpi), inch(height / self.dpi), self.fit),
            data,
            mime,
            (width, height),
            self.fit,
        )
