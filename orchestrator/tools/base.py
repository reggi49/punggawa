"""Base infrastructure and registry for modular agent tools."""
import functools
import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, get_type_hints

logger = logging.getLogger("ToolRegistry")


@dataclass
class ToolDefinition:
    name: str
    description: str
    func: Callable[..., Any]
    sensitive: bool
    parameters_schema: dict[str, Any]

    def to_openai_schema(self) -> dict[str, Any]:
        """Konversi metadata tool ke format OpenAI Function/Tools Schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


class ToolRegistry:
    """Central registry yang menyimpan seluruh tool yang tersedia untuk LLM."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str | None = None,
        description: str | None = None,
        sensitive: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator untuk mendaftarkan fungsi Python biasa menjadi Agent Tool.
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            tool_desc = description or (inspect.getdoc(func) or f"Fungsi tool {tool_name}").strip()

            schema = self._generate_parameters_schema(func)
            tool_def = ToolDefinition(
                name=tool_name,
                description=tool_desc,
                func=func,
                sensitive=sensitive,
                parameters_schema=schema,
            )

            self._tools[tool_name] = tool_def
            logger.info(f"Tool terdaftar: '{tool_name}' (sensitive={sensitive})")

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
        """
        Mengeksekusi tool dengan input arguments yang aman dan error handling terisolasi.
        """
        tool_def = self.get(name)
        if not tool_def:
            return {
                "success": False,
                "error": f"Tool '{name}' tidak ditemukan di registry.",
                "output": None,
            }

        parsed_args = arguments
        if isinstance(arguments, str):
            try:
                parsed_args = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError as err:
                return {
                    "success": False,
                    "error": f"Format arguments JSON tidak valid: {err}",
                    "output": None,
                }

        try:
            result = tool_def.func(**parsed_args)
            return {
                "success": True,
                "error": None,
                "output": result,
            }
        except Exception as exc:
            logger.error(f"Error saat mengeksekusi tool '{name}': {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "output": None,
            }

    @staticmethod
    def _generate_parameters_schema(func: Callable[..., Any]) -> dict[str, Any]:
        """Menghasilkan JSON Schema dari signature dan type hints fungsi Python."""
        signature = inspect.signature(func)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}

        properties: dict[str, Any] = {}
        required: list[str] = []

        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in signature.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name, str)
            json_type = type_mapping.get(param_type, "string")

            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name}",
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


# Global registry singleton
registry = ToolRegistry()
register_tool = registry.register

