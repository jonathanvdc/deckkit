from dataclasses import dataclass

from ..units import Length, require_length


@dataclass(frozen=True)
class Bounds:
    x: Length
    y: Length
    width: Length
    height: Length

    def __post_init__(self) -> None:
        require_length(self.x)
        require_length(self.y)
        require_length(self.width)
        require_length(self.height)
