"""
conftest.py — pytest 共享夹具与配置

提供总线实例夹具，根据环境变量 BUS_BACKEND 自动切换后端。
"""

import os
import pytest
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBC_PATH = PROJECT_ROOT / "fixtures" / "vehicle_ivi.dbc"


def pytest_addoption(parser):
    parser.addoption(
        "--bus-backend",
        action="store",
        default=os.environ.get("BUS_BACKEND", "virtual"),
        choices=["virtual", "socketcan", "canoe"],
        help="选择总线后端: virtual(默认), socketcan(Linux), canoe(Windows+CANoe)",
    )


@pytest.fixture(scope="session")
def bus_backend(request):
    """获取总线后端类型。"""
    return request.config.getoption("--bus-backend")


@pytest.fixture(scope="function")
def bus(bus_backend):
    """
    创建总线实例。
    
    根据 bus_backend 参数自动选择：
    - virtual: python-can virtual 接口（默认，无需硬件）
    - socketcan: Linux SocketCAN vcan0
    - canoe: CANoe COM 接口（需 Windows + 授权）
    """
    from ivi_bus_capl.virtual_bus import VirtualBus
    
    if bus_backend == "canoe":
        try:
            from ivi_bus_capl.canoe_bridge import CanoeBridge
            # 这里假设有一个测试专用的 CANoe 配置
            cfg_path = PROJECT_ROOT / "fixtures" / "test_config.cfg"
            bridge = CanoeBridge()
            bridge.open(str(cfg_path))
            bridge.start_measurement()
            yield bridge
            bridge.close()
        except Exception as e:
            pytest.skip(f"CANoe 不可用: {e}")
    else:
        b = VirtualBus(bustype=bus_backend, channel="vcan0")
        b.load_dbc(str(DBC_PATH))
        yield b
        b.close()


@pytest.fixture(scope="session")
def dbc_loader():
    """共享 DBC 加载器实例。"""
    from ivi_bus_capl.dbc_loader import DbcLoader
    return DbcLoader(str(DBC_PATH))


@pytest.fixture
def sample_ivi_status_signals():
    """标准的 IVI_Status 信号值。"""
    return {
        "ScreenState": 1,    # Home 界面
        "AudioVolume": 35,   # 35%
        "OverspeedWarning": 0,
    }


@pytest.fixture
def sample_vehicle_speed_signals():
    """标准的 VehicleSpeed 信号值。"""
    return {
        "Speed": 60.0,  # 60 km/h
    }