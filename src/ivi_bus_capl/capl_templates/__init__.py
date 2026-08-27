"""
CAPL 模板管理模块

本模块为智能座舱总线测试提供 CAPL 脚本的模板化生成能力。
当前版本包含 8 个参考脚本（位于项目根目录 capl/ 下），
本目录预留用于未来基于 Jinja2 的动态模板生成。

使用示例（未来扩展）:

    from ivi_bus_capl.capl_templates import CaplTemplateEngine

    engine = CaplTemplateEngine()
    script = engine.render("periodic_check", can_id="0x123")
    engine.write_to_file(script, "output.can")

设计思路:
    - 保持模板与静态脚本分离，避免混淆
    - 模板使用 Jinja2 语法，支持变量替换和条件判断
    - 每个模板对应一个特定的测试场景（周期、UDS、DTC 等）

参考脚本列表:
    详见项目根目录 capl/ 下的 .can 文件，或查阅项目 README 中的 CAPL 脚本索引。
"""

from typing import Optional

__all__ = []  # 暂不导出任何符号，后续扩展时添加


def list_templates() -> list[str]:
    """返回当前可用的模板名称列表（预留接口）。"""
    return []


def render_template(name: str, **kwargs) -> Optional[str]:
    """
    渲染指定名称的 CAPL 模板（预留接口）。

    Args:
        name: 模板名称，如 "periodic_check", "uds_22_read_did"
        **kwargs: 模板变量，如 can_id="0x123", interval_ms=100

    Returns:
        渲染后的 CAPL 脚本字符串，若模板不存在则返回 None
    """
    return None