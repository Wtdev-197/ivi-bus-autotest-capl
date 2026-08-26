"""
canoe_bridge.py — CANoe COM 接口封装桥接层

通过 Vector CANoe COM 接口，将 pytest 测试框架与 CANoe 运行时打通。
仅在 Windows + CANoe 授权环境下可用。

使用方式：
    from ivi_bus_capl.canoe_bridge import CanoeBridge
    
    bridge = CanoeBridge()
    bridge.open("path/to/cfg.cfg")
    bridge.start_measurement()
    result = bridge.call_capl_function("MyFunction", 42)
    bridge.stop_measurement()
    bridge.close()
"""

import os
import sys
import time
from typing import Optional, Any, Callable


class CanoeBridgeError(Exception):
    """CANoe 桥接层异常基类。"""
    pass


class CanoeNotAvailableError(CanoeBridgeError):
    """CANoe 不可用时抛出。"""
    pass


class CanoeBridge:
    """CANoe COM 接口桥接层。"""

    def __init__(self):
        self._app = None
        self._measurement = None
        self._is_open = False
        self._is_running = False

    def open(self, cfg_path: str) -> None:
        """
        打开 CANoe 配置文件。
        
        :param cfg_path: .cfg 配置文件路径
        """
        if sys.platform != "win32":
            raise CanoeNotAvailableError("CANoe COM 接口仅支持 Windows")

        try:
            import win32com.client
            self._app = win32com.client.Dispatch("CANoe.Application")
        except ImportError:
            raise CanoeNotAvailableError("需要 pywin32 库: pip install pywin32")
        except Exception as e:
            raise CanoeNotAvailableError(f"CANoe COM 初始化失败: {e}")

        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"配置文件不存在: {cfg_path}")

        try:
            self._app.Open(cfg_path)
            self._is_open = True
        except Exception as e:
            raise CanoeBridgeError(f"打开配置文件失败: {e}")

    def start_measurement(self) -> None:
        """启动 CANoe Measurement。"""
        self._check_open()
        try:
            self._app.Measurement.Start()
            self._is_running = True
            # 等待测量启动
            time.sleep(1)
        except Exception as e:
            raise CanoeBridgeError(f"启动 Measurement 失败: {e}")

    def stop_measurement(self) -> None:
        """停止 CANoe Measurement。"""
        if self._is_running:
            try:
                self._app.Measurement.Stop()
                self._is_running = False
            except Exception as e:
                raise CanoeBridgeError(f"停止 Measurement 失败: {e}")

    def call_capl_function(self, func_name: str, *args) -> Any:
        """
        调用 CAPL 函数（需在 CAPL 中用 export 声明）。
        
        :param func_name: CAPL 函数名
        :param args: 参数列表
        :return: 函数返回值
        """
        self._check_running()
        try:
            capl = self._app.CAPL.Functions(func_name)
            return capl.Call(*args)
        except Exception as e:
            raise CanoeBridgeError(f"调用 CAPL 函数 '{func_name}' 失败: {e}")

    def get_signal(self, channel: int, message_name: str, signal_name: str) -> Any:
        """
        读取总线信号值。
        
        :param channel: CAN 通道号
        :param message_name: 报文名称
        :param signal_name: 信号名称
        :return: 信号值
        """
        self._check_running()
        try:
            sig = self._app.Bus.GetSignal(channel, message_name, signal_name)
            return sig.Value
        except Exception as e:
            raise CanoeBridgeError(f"读取信号失败: {e}")

    def set_signal(self, channel: int, message_name: str,
                   signal_name: str, value: Any) -> None:
        """
        设置总线信号值（需 CAPL 中对应变量可写）。
        """
        self._check_running()
        try:
            sig = self._app.Bus.GetSignal(channel, message_name, signal_name)
            sig.Value = value
        except Exception as e:
            raise CanoeBridgeError(f"设置信号失败: {e}")

    def get_env_var(self, var_name: str) -> Any:
        """读取 CANoe 环境变量。"""
        self._check_running()
        try:
            env = self._app.Environment.GetVariable(var_name)
            return env.Value
        except Exception as e:
            raise CanoeBridgeError(f"读取环境变量失败: {e}")

    def set_env_var(self, var_name: str, value: Any) -> None:
        """设置 CANoe 环境变量。"""
        self._check_running()
        try:
            env = self._app.Environment.GetVariable(var_name)
            env.Value = value
        except Exception as e:
            raise CanoeBridgeError(f"设置环境变量失败: {e}")

    def wait_for_condition(self, condition_func: Callable[[], bool],
                           timeout: float = 10.0, interval: float = 0.1) -> bool:
        """
        等待条件成立（轮询模式）。
        
        :param condition_func: 条件判断函数
        :param timeout: 超时秒数
        :param interval: 轮询间隔
        :return: 条件是否在超时前成立
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition_func():
                return True
            time.sleep(interval)
        return False

    def close(self) -> None:
        """关闭 CANoe 连接。"""
        self.stop_measurement()
        if self._app and self._is_open:
            try:
                self._app.Quit()
            except Exception:
                pass
        self._app = None
        self._is_open = False

    def _check_open(self) -> None:
        """检查 CANoe 是否已打开。"""
        if not self._is_open or self._app is None:
            raise CanoeBridgeError("CANoe 未打开，请先调用 open()")

    def _check_running(self) -> None:
        """检查 Measurement 是否在运行。"""
        if not self._is_running:
            raise CanoeBridgeError("Measurement 未运行，请先调用 start_measurement()")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()