"""
dbc_loader.py — DBC 文件加载与查询工具

提供 DBC 文件的统一加载接口，支持报文/信号元数据查询。
与 virtual_bus.py 解耦，便于单独使用。
"""

import os
import cantools
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class SignalInfo:
    """单个信号的元数据。"""
    name: str
    start_bit: int
    length: int
    is_signed: bool
    factor: float
    offset: float
    minimum: float
    maximum: float
    unit: str
    choices: Optional[Dict[int, str]] = None


@dataclass
class MessageInfo:
    """单个报文的元数据。"""
    name: str
    frame_id: int
    dlc: int
    cycle_time: int
    signals: List[SignalInfo]


class DbcLoader:
    """DBC 文件加载器，提供缓存与查询功能。"""

    _instances: Dict[str, "DbcLoader"] = {}

    def __new__(cls, dbc_path: str):
        """相同路径复用同一实例（享元模式）。"""
        abs_path = os.path.abspath(dbc_path)
        if abs_path not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[abs_path] = instance
        return cls._instances[abs_path]

    def __init__(self, dbc_path: str):
        if self._initialized:
            return
        self._initialized = True

        self.path = os.path.abspath(dbc_path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"DBC 文件不存在: {self.path}")

        try:
            self._db = cantools.database.load_file(self.path)
        except Exception as e:
            raise RuntimeError(f"DBC 加载失败: {e}")

    def get_message_info(self, name_or_id: str | int) -> Optional[MessageInfo]:
        """根据报文名称或 ID 获取元数据。"""
        try:
            if isinstance(name_or_id, int):
                msg = self._db.get_message_by_frame_id(name_or_id)
            else:
                msg = self._db.get_message_by_name(name_or_id)
        except KeyError:
            return None

        signals = []
        for sg in msg.signals:
            signals.append(SignalInfo(
                name=sg.name,
                start_bit=sg.start,
                length=sg.length,
                is_signed=sg.is_signed,
                factor=sg.scale,
                offset=sg.offset,
                minimum=sg.minimum or 0,
                maximum=sg.maximum or 0,
                unit=sg.unit or "",
                choices=sg.choices,
            ))

        return MessageInfo(
            name=msg.name,
            frame_id=msg.frame_id,
            dlc=msg.length,
            cycle_time=getattr(msg, "cycle_time", 0),
            signals=signals,
        )

    def list_messages(self) -> List[str]:
        """列出所有报文名称。"""
        return [msg.name for msg in self._db.messages]

    def encode(self, message_name: str, signals: Dict[str, Any]) -> bytes:
        """编码信号字典为 CAN 数据字节。"""
        return self._db.encode_message(message_name, signals)

    def decode(self, frame_id: int, data: bytes) -> Dict[str, Any]:
        """解码 CAN 数据字节为信号字典。"""
        return self._db.decode_message(frame_id, data)

    @property
    def database(self):
        """返回底层 cantools 数据库对象（高级操作）。"""
        return self._db