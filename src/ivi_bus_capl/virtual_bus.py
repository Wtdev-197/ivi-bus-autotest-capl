"""
virtual_bus.py — 智能座舱总线降级仿真层

在无 CANoe / 无 Vector 硬件环境下，用 python-can + cantools
模拟 CAN 总线收发，使得 pytest 用例可以在任何平台上运行。

使用方式：
    from ivi_bus_capl.virtual_bus import VirtualBus
    
    bus = VirtualBus(bustype="virtual", channel="vcan0", bitrate=500000)
    bus.load_dbc("fixtures/vehicle_ivi.dbc")
    
    # 发送编码后的报文
    bus.send("IVI_Status", {"ScreenState": 1, "AudioVolume": 35})
    
    # 接收并解码
    msg = bus.recv(timeout=1.0)
    print(msg.signals)  # {"ScreenState": 1, "AudioVolume": 35}
"""

import time
import threading
import can
import cantools
from typing import Optional, Dict, Any


class VirtualBus:
    """虚拟总线引擎，兼容 virtual / socketcan / vector 三种后端。"""

    def __init__(self, bustype: str = "virtual", channel: str = "vcan0",
                 bitrate: int = 500000):
        """
        初始化总线实例。
        
        :param bustype: "virtual" | "socketcan" | "vector"
        :param channel: CAN 通道名称
        :param bitrate: 波特率（仅 virtual 后端生效）
        """
        self.bustype = bustype
        self.channel = channel
        self._db = None          # cantools 数据库对象
        self._bus = None         # python-can Bus 对象
        self._running = False
        self._rx_thread = None
        self._received_messages = []  # 线程安全的接收缓存
        self._dtc_active = False
        self._did_values = {0xF190: b"TESTVIN123456789", 0xF1A0: b"v1.0.0"}
        
        try:
            if bustype == "virtual":
                self._bus = can.Bus(
                    interface="virtual",
                    channel=channel,
                    bitrate=bitrate,
                    receive_own_messages=True,
                )
            elif bustype == "socketcan":
                self._bus = can.Bus(
                    interface="socketcan",
                    channel=channel,
                    bitrate=bitrate
                )
            elif bustype == "vector":
                self._bus = can.Bus(
                    interface="vector",
                    channel=channel,
                    bitrate=bitrate
                )
            else:
                raise ValueError(f"不支持的总线类型: {bustype}")
        except Exception as e:
            raise RuntimeError(f"总线初始化失败: {e}")

    def load_dbc(self, dbc_path: str) -> None:
        """
        加载 DBC 文件，用于后续报文的编码/解码。
        
        :param dbc_path: DBC 文件路径
        """
        try:
            self._db = cantools.database.load_file(dbc_path)
        except Exception as e:
            raise RuntimeError(f"DBC 加载失败 ({dbc_path}): {e}")

    def send(self, message_name: str, signals: Dict[str, Any],
             arbitration_id: Optional[int] = None) -> None:
        """
        发送一条编码后的 CAN 报文。
        
        :param message_name: DBC 中定义的报文名称（如 "IVI_Status"）
        :param signals: 信号字典（如 {"ScreenState": 1, "AudioVolume": 35}）
        :param arbitration_id: 可选，手动指定仲裁 ID（覆盖 DBC 定义）
        """
        if self._db is None:
            raise RuntimeError("DBC 未加载，请先调用 load_dbc()")
        
        try:
            message = self._db.get_message_by_name(message_name)
            signal_values = dict(signals)
            for signal in message.signals:
                signal_values.setdefault(signal.name, 0)

            data = self._db.encode_message(message_name, signal_values)
            msg_id = arbitration_id or message.frame_id
            self._drain_pending_messages()
            
            msg = can.Message(
                arbitration_id=msg_id,
                data=data,
                is_extended_id=(msg_id > 0x7FF),
                timestamp=time.time()
            )
            self._bus.send(msg)
            if message_name == "IVI_Status" and signal_values.get("OverspeedWarning"):
                self._dtc_active = True
            elif message_name == "VehicleSpeed" and signal_values.get("Speed", 0) > 120:
                self._dtc_active = True
        except Exception as e:
            raise RuntimeError(f"发送 {message_name} 失败: {e}")

    def send_raw(self, arbitration_id: int, data: bytes) -> None:
        """发送原始 CAN 数据，并模拟虚拟 ECU 的诊断响应。"""
        if self._bus is None:
            raise RuntimeError("总线未初始化")

        request = bytes(data)
        self._drain_pending_messages()
        if arbitration_id != 0x7E0 or not request:
            return

        service = request[0]
        if service == 0x22 and len(request) >= 3:
            did = (request[1] << 8) | request[2]
            payload = self._did_values.get(did)
            response = bytes([0x62, request[1], request[2]]) + payload \
                if payload is not None else bytes([0x7F, 0x22, 0x12])
        elif service == 0x2E and len(request) >= 3:
            did = (request[1] << 8) | request[2]
            self._did_values[did] = request[3:]
            response = bytes([0x6E, request[1], request[2]])
        elif service == 0x19:
            response = bytes([0x59, int(self._dtc_active)])
        elif service == 0x14:
            self._dtc_active = False
            response = bytes([0x54])
        else:
            response = bytes([0x7F, service, 0x11])

        self._bus.send(can.Message(
            arbitration_id=0x7E8,
            data=response,
            is_extended_id=False,
            timestamp=time.time(),
        ))

    def _drain_pending_messages(self) -> None:
        """清理 virtual 总线回环中尚未消费的旧帧。"""
        while self._bus.recv(timeout=0) is not None:
            pass

    def recv(self, timeout: float = 1.0) -> Optional["DecodedMessage"]:
        """
        接收并解码一条 CAN 报文。
        
        :param timeout: 超时秒数
        :return: DecodedMessage 对象（包含 .signals 字典和 .raw_msg），
                 超时返回 None
        """
        raw_msg = self._bus.recv(timeout=timeout)
        if raw_msg is None:
            return None
        
        return self._decode(raw_msg)

    def _decode(self, raw_msg: can.Message) -> Optional["DecodedMessage"]:
        """将原始 CAN 报文解码为信号字典。"""
        if self._db is None:
            return DecodedMessage(raw_msg, {})
        
        try:
            signals = self._db.decode_message(
                raw_msg.arbitration_id,
                raw_msg.data,
                decode_choices=False,
            )
            return DecodedMessage(raw_msg, signals)
        except KeyError:
            # 未知报文 ID，不做解码
            return DecodedMessage(raw_msg, {})
        except Exception:
            # 解码失败，返回空信号
            return DecodedMessage(raw_msg, {})

    def start_background_listener(self) -> None:
        """
        启动后台监听线程，持续接收报文并缓存。
        用于长时间运行的测试场景（如周期监控）。
        """
        if self._running:
            return
        self._running = True
        self._received_messages.clear()
        
        def _listener():
            while self._running:
                msg = self._bus.recv(timeout=0.1)
                if msg:
                    decoded = self._decode(msg)
                    self._received_messages.append(decoded)
        
        self._rx_thread = threading.Thread(target=_listener, daemon=True)
        self._rx_thread.start()

    def stop_background_listener(self) -> None:
        """停止后台监听线程。"""
        self._running = False
        if self._rx_thread:
            self._rx_thread.join(timeout=2.0)

    @property
    def received(self) -> list:
        """获取已缓存的已解码报文列表。"""
        return self._received_messages.copy()

    def close(self) -> None:
        """关闭总线连接。"""
        self.stop_background_listener()
        if self._bus:
            self._bus.shutdown()


class DecodedMessage:
    """已解码的 CAN 报文容器。"""
    
    def __init__(self, raw_msg: can.Message, signals: Dict[str, Any]):
        self.raw_msg = raw_msg
        self.signals = signals
        self.timestamp = raw_msg.timestamp
        self.arbitration_id = raw_msg.arbitration_id
    
    def __repr__(self):
        return (f"DecodedMessage(id=0x{self.arbitration_id:X}, "
                f"signals={self.signals})")


# ------------------- 简易自检 -------------------
if __name__ == "__main__":
    # 快速验证：创建 virtual 总线，发送并接收
    bus = VirtualBus(bustype="virtual", channel="vcan0")
    bus.load_dbc("../../fixtures/vehicle_ivi.dbc")
    
    # 发送一条 IVI_Status
    bus.send("IVI_Status", {"ScreenState": 1, "AudioVolume": 58})
    
    # 接收并打印
    decoded = bus.recv(timeout=0.5)
    if decoded:
        print(f"收到: {decoded}")
    else:
        print("超时，未收到报文（virtual 环回模式下可能需调整）")
    
    bus.close()