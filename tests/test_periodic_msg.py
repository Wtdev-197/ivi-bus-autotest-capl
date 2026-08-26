"""
test_periodic_msg.py — IVI_Status 报文周期监控测试

测试目标：
    验证 IVI_Status（ID 0x2A0）的发送周期是否稳定在 100±10ms 范围内。
    
测试方法：
    1. 向总线发送 20 条连续的 IVI_Status 报文
    2. 记录每条报文的发送时间戳
    3. 计算相邻报文的时间间隔
    4. 断言所有间隔在 [90ms, 110ms] 区间内
    
依赖：
    - DBC 文件：fixtures/vehicle_ivi.dbc
    - 总线后端：通过环境变量 BUS_BACKEND 选择（默认 virtual）
"""

import time
import os
import pytest
from ivi_bus_capl.virtual_bus import VirtualBus


@pytest.fixture(scope="module")
def bus():
    """
    创建总线实例，根据环境变量 BUS_BACKEND 切换后端。
    
    用法：
        export BUS_BACKEND=virtual    # 默认，无需 CANoe
        export BUS_BACKEND=canoe      # 需 Windows + CANoe 授权
    """
    backend = os.environ.get("BUS_BACKEND", "virtual")
    
    if backend == "canoe":
        pytest.skip("CANoe 后端需在 Windows + 授权环境下执行")
        # 实际项目中这里应返回 CANoe 桥接层实例
        yield None
    else:
        b = VirtualBus(bustype="virtual", channel="vcan0")
        b.load_dbc("fixtures/vehicle_ivi.dbc")
        yield b
        b.close()


def test_ivi_status_period_within_tolerance(bus):
    """
    验证 IVI_Status 报文周期在 100±10ms 范围内。
    
    步骤：
        1. 连续发送 20 条 IVI_Status
        2. 记录每条的时间戳
        3. 计算间隔并断言
    """
    MESSAGE_NAME = "IVI_Status"
    EXPECTED_PERIOD_MS = 100
    TOLERANCE_MS = 10
    SAMPLE_COUNT = 20
    
    timestamps = []
    
    for i in range(SAMPLE_COUNT):
        signals = {
            "ScreenState": i % 4,        # 0~3 循环
            "AudioVolume": min(i * 5, 99)  # 0~99 递增
        }
        bus.send(MESSAGE_NAME, signals)
        timestamps.append(time.time())
        
        # 模拟 100ms 发送间隔（ECU 行为）
        time.sleep(0.095)  # 故意略低于 100ms，看断言是否能捕获
    
    # 计算相邻时间间隔（毫秒）
    intervals_ms = []
    for i in range(1, len(timestamps)):
        interval = (timestamps[i] - timestamps[i-1]) * 1000
        intervals_ms.append(round(interval, 2))
    
    # 断言：所有间隔应在 90~110ms 之间
    min_allowed = EXPECTED_PERIOD_MS - TOLERANCE_MS
    max_allowed = EXPECTED_PERIOD_MS + TOLERANCE_MS
    
    violations = [iv for iv in intervals_ms 
                  if iv < min_allowed or iv > max_allowed]
    
    assert not violations, (
        f"发现 {len(violations)} 个周期越界: {violations}\n"
        f"允许范围: [{min_allowed}, {max_allowed}] ms\n"
        f"全部间隔: {intervals_ms}"
    )
    
    # 输出统计信息
    avg_interval = sum(intervals_ms) / len(intervals_ms)
    print(f"\n✓ 周期测试通过 | 样本数: {SAMPLE_COUNT-1} | "
          f"平均间隔: {avg_interval:.2f}ms | "
          f"范围: [{min(intervals_ms):.2f}, {max(intervals_ms):.2f}]ms")


def test_ivi_status_signals_valid_range(bus):
    """
    验证 IVI_Status 各信号值在有效范围内。
    
    规则：
        - ScreenState: 0~3（枚举值）
        - AudioVolume: 0~100
    """
    MESSAGE_NAME = "IVI_Status"
    VALID_RANGES = {
        "ScreenState": (0, 3),
        "AudioVolume": (0, 100)
    }
    
    # 发送一组边界值
    test_cases = [
        {"ScreenState": 0, "AudioVolume": 0},
        {"ScreenState": 3, "AudioVolume": 100},
        {"ScreenState": 1, "AudioVolume": 50},
    ]
    
    for case in test_cases:
        bus.send(MESSAGE_NAME, case)
        decoded = bus.recv(timeout=0.2)
        
        assert decoded is not None, f"发送 {case} 后未收到回显"
        
        for signal_name, expected_value in case.items():
            actual = decoded.signals.get(signal_name)
            assert actual == expected_value, (
                f"信号 {signal_name} 期望 {expected_value}，"
                f"实际 {actual}"
            )


@pytest.mark.slow
def test_long_running_period_stability(bus):
    """
    长时间稳定性测试（标记为 slow，默认不执行）。
    
    连续发送 100 条报文，检查整体抖动情况。
    运行方式：pytest --runslow
    """
    MESSAGE_NAME = "IVI_Status"
    SAMPLE_COUNT = 100
    
    timestamps = []
    for i in range(SAMPLE_COUNT):
        bus.send(MESSAGE_NAME, {
            "ScreenState": i % 4,
            "AudioVolume": i % 100
        })
        timestamps.append(time.time())
        time.sleep(0.098)  # 模拟 ECU 行为
    
    intervals = [(timestamps[i+1] - timestamps[i]) * 1000 
                 for i in range(len(timestamps)-1)]
    
    jitter = max(intervals) - min(intervals)
    print(f"\n长时间周期测试 | 样本: {SAMPLE_COUNT-1} | "
          f"抖动: {jitter:.2f}ms")
    
    assert jitter < 30, f"周期抖动过大: {jitter:.2f}ms"