"""System utilities and computational helper tools."""
import datetime
import math
from typing import Any
from orchestrator.tools.base import register_tool


@register_tool(
    name="get_current_time",
    description="Mendapatkan informasi waktu, tanggal, dan timezone saat ini.",
    sensitive=False,
)
def get_current_time(timezone_offset_hours: int = 7) -> dict[str, Any]:
    """
    Mengembalikan waktu saat ini sesuai offset jam dari UTC (default UTC+7 WIB).
    """
    tz = datetime.timezone(datetime.timedelta(hours=timezone_offset_hours))
    now = datetime.datetime.now(tz)
    return {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone_offset": f"UTC+{timezone_offset_hours}",
        "day_of_week": now.strftime("%A"),
    }


@register_tool(
    name="evaluate_math_expression",
    description="Melakukan kalkulasi ekspresi matematika yang kompleks dan presisi secara aman.",
    sensitive=False,
)
def evaluate_math_expression(expression: str) -> dict[str, Any]:
    """
    Mengevaluasi ekspresi aritmatika dengan lingkungan terbatas yang aman.
    """
    allowed_names = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "math": math,
        "sqrt": math.sqrt,
        "pi": math.pi,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
    }

    try:
        # Batasi hanya karakter matematika umum
        sanitized = expression.strip()
        if any(bad_word in sanitized for bad_word in ["import", "exec", "eval", "__", "os", "sys"]):
            return {"error": "Ekspresi mengandung kata kunci terlarang."}

        # Evaluasi dengan builtins dinonaktifkan
        result = eval(sanitized, {"__builtins__": {}}, allowed_names)
        return {
            "expression": expression,
            "result": result,
        }
    except Exception as exc:
        return {
            "error": f"Kalkulasi gagal: {str(exc)}",
            "expression": expression,
        }

