from __future__ import annotations

import os
import re
import shutil
import sys
import unicodedata

TOOL_RESULT_TAG = "📋[工具结果]"
DEFAULT_PANEL_WIDTH = 72
SECTION_DIVIDER = "─" * 60
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
RESET = "\033[0m"
STYLE_CODES = {
    "bold": "1",
    "dim": "2",
}
COLOR_CODES = {
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}


def supports_color() -> bool:
    """判断当前终端是否适合输出 ANSI 颜色。"""
    if os.getenv("NO_COLOR"):
        return False
    stream = getattr(sys, "stdout", None)
    return bool(stream and hasattr(stream, "isatty") and stream.isatty())


def style_text(
    text: str,
    *,
    color: str | None = None,
    bold: bool = False,
    dim: bool = False,
    prompt_safe: bool = False,
) -> str:
    """为终端文本添加 ANSI 样式。"""
    if not supports_color():
        return text

    codes: list[str] = []
    if bold:
        codes.append(STYLE_CODES["bold"])
    if dim:
        codes.append(STYLE_CODES["dim"])
    if color:
        codes.append(COLOR_CODES[color])

    if not codes:
        return text

    styled = f"\033[{';'.join(codes)}m{text}{RESET}"
    if prompt_safe:
        return ANSI_PATTERN.sub(lambda match: f"\001{match.group(0)}\002", styled)
    return styled


def panel_width() -> int:
    """返回适合当前终端的面板宽度。"""
    try:
        terminal_width = shutil.get_terminal_size((DEFAULT_PANEL_WIDTH, 24)).columns
    except OSError:
        terminal_width = DEFAULT_PANEL_WIDTH
    return max(48, min(DEFAULT_PANEL_WIDTH, terminal_width))


def _visible_len(text: str) -> int:
    """计算不含 ANSI 样式的终端显示宽度。"""
    return _display_width(ANSI_PATTERN.sub("", text))


def _char_width(char: str) -> int:
    if unicodedata.combining(char):
        return 0
    if unicodedata.east_asian_width(char) in {"W", "F"}:
        return 2
    return 1


def _display_width(text: str) -> int:
    return sum(_char_width(char) for char in text)


def _wrap_display_text(text: str, width: int) -> list[str]:
    """按终端显示宽度换行。"""
    if width <= 0:
        return [text]
    if not text:
        return [""]

    wrapped: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current: list[str] = []
        current_width = 0
        for char in paragraph:
            char_width = _char_width(char)
            if current and current_width + char_width > width:
                wrapped.append("".join(current))
                current = [char]
                current_width = char_width
            else:
                current.append(char)
                current_width += char_width
        wrapped.append("".join(current))
    return wrapped or [""]


def strip_json_blocks(text: str) -> str:
    """移除文本中的 ```json ... ``` 块，避免 JSON 作为普通文本输出。"""
    text = re.sub(r"```json\s*\{[^}]*\}\s*```", "", text, flags=re.DOTALL)
    text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
    return text.strip()


def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _extract_assistant_text(content) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if part.get("type") == "text":
                text = strip_json_blocks(part.get("text", ""))
                if text:
                    parts.append(text)
        return "\n".join(parts)

    return strip_json_blocks(_coerce_text(content))


def format_section(title: str, body: str) -> str:
    """将内容格式化为分区展示。"""
    normalized_body = body.strip() if body.strip() else "（空）"
    divider = style_text("─" * panel_width(), color="blue", dim=True)
    return f"{style_text(title, color='cyan', bold=True)}\n{divider}\n{normalized_body}"


def format_panel(title: str, lines: list[str], *, color: str = "blue") -> str:
    """渲染带边框的信息面板。"""
    width = panel_width()
    inner_width = width - 4
    plain_title = f" {title} "
    title_visible_len = _display_width(plain_title)
    left = max(1, (inner_width - title_visible_len) // 2)
    right = max(1, inner_width - title_visible_len - left)

    top = f"┌{'─' * left}{style_text(plain_title, color=color, bold=True)}{'─' * right}┐"
    bottom = f"└{'─' * inner_width}┘"
    rendered_lines = [top]

    for line in lines:
        for wrapped_line in _wrap_display_text(line, inner_width):
            visible = _visible_len(wrapped_line)
            padding = max(0, inner_width - visible)
            rendered_lines.append(f"│ {wrapped_line}{' ' * padding} │")

    rendered_lines.append(bottom)
    return "\n".join(style_text(part, color=color, dim=(part == bottom)) if part == bottom else part for part in rendered_lines)


def format_kv_rows(items: list[tuple[str, str]], *, key_color: str = "magenta") -> list[str]:
    """将键值对格式化为对齐文本行。"""
    label_width = max((_display_width(label) for label, _ in items), default=0)
    rows: list[str] = []
    for label, value in items:
        label_padding = max(0, label_width - _display_width(label))
        padded_label = f"{label}{' ' * label_padding}"
        rows.append(f"{padded_label}  {value}")
    return rows


def format_message_with_tags(message: dict) -> str:
    """格式化消息，根据类型添加标签。"""
    role = message.get("role", "")
    content = message.get("content", "")

    if role == "user":
        return format_section("👤 用户输入", _coerce_text(content))
    if role == "assistant":
        return format_section("🤖 AI 回复", _extract_assistant_text(content))
    if role == "tool":
        return format_section(TOOL_RESULT_TAG, _coerce_text(content))
    return format_section(f"[{role}]", _coerce_text(content))
