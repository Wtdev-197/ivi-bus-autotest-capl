"""ivi-bus-autotest-capl — 智能座舱总线自动化测试工具包。"""

__version__ = "0.1.0"

from .virtual_bus import VirtualBus, DecodedMessage
from .dbc_loader import DbcLoader

__all__ = ["VirtualBus", "DecodedMessage", "DbcLoader"]