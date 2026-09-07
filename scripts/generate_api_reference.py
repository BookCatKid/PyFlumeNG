#!/usr/bin/env python3
"""Generate the public API reference directly from source annotations."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "api-reference.md"

PUBLIC_CLASSES = (
    ("pyflumeng/auth.py", ("FlumeAuth", "FlumePortalAuth")),
    ("pyflumeng/client.py", ("FlumeClient",)),
    ("pyflumeng/data.py", ("FlumeData",)),
    ("pyflumeng/devices.py", ("FlumeDeviceList",)),
    ("pyflumeng/leak.py", ("FlumeLeakList",)),
    ("pyflumeng/notifications.py", ("FlumeNotificationList",)),
    ("pyflumeng/usage.py", ("FlumeUsageAlertList",)),
    ("pyflumeng/rate_limit.py", ("RateLimitState",)),
)


def _expr(node: Optional[ast.expr]) -> str:
    return ast.unparse(node) if node is not None else ""


def _arg(arg: ast.arg, default: Optional[ast.expr] = None) -> str:
    text = arg.arg
    if arg.annotation is not None:
        text += ": " + _expr(arg.annotation)
    if default is not None:
        text += " = " + _expr(default)
    return text


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    pairs = [
        (arg, default)
        for arg, default in zip(positional, defaults)
        if arg.arg not in {"self", "cls"}
    ]

    parts: list[str] = []
    posonly_count = sum(1 for arg, _ in pairs if arg in args.posonlyargs)
    for index, (arg, default) in enumerate(pairs, start=1):
        parts.append(_arg(arg, default))
        if posonly_count and index == posonly_count:
            parts.append("/")

    if args.vararg is not None:
        value = "*" + args.vararg.arg
        if args.vararg.annotation is not None:
            value += ": " + _expr(args.vararg.annotation)
        parts.append(value)
    elif args.kwonlyargs:
        parts.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(_arg(arg, default))

    if args.kwarg is not None:
        value = "**" + args.kwarg.arg
        if args.kwarg.annotation is not None:
            value += ": " + _expr(args.kwarg.annotation)
        parts.append(value)

    returns = ""
    if node.returns is not None:
        returns = " -> " + _expr(node.returns)
    return "(" + ", ".join(parts) + ")" + returns


def _class_nodes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _first_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node, clean=True) or ""
    return doc.splitlines()[0] if doc else ""


def _public_methods(
    node: ast.ClassDef,
) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    methods = [
        item
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (item.name == "__init__" or not item.name.startswith("_"))
    ]
    overloaded = {
        item.name
        for item in methods
        if any(_expr(decorator) == "overload" for decorator in item.decorator_list)
    }
    for item in methods:
        if item.name in overloaded and not any(
            _expr(decorator) == "overload" for decorator in item.decorator_list
        ):
            continue
        yield item


def _render_class(name: str, node: ast.ClassDef) -> list[str]:
    lines = [f"### `{name}`", ""]
    if _first_line(node):
        lines.extend([_first_line(node), ""])
    methods = list(_public_methods(node))
    if not methods:
        lines.extend(["No public methods are declared on this class.", ""])
        return lines
    for method in methods:
        if any(_expr(decorator) == "property" for decorator in method.decorator_list):
            annotation = _expr(method.returns) or "Any"
            lines.append(f"- `{method.name}: {annotation}` (property)")
            if _first_line(method):
                lines.append(f"  {_first_line(method)}")
            continue
        display_name = name if method.name == "__init__" else method.name
        lines.extend([f"- `{display_name}{_signature(method)}`"])
        if _first_line(method):
            lines.append(f"  {_first_line(method)}")
    lines.append("")
    return lines


def _model_fields(node: ast.ClassDef) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            fields.append((item.target.id, _expr(item.annotation)))
    return fields


def generate() -> str:
    lines = [
        "# API reference",
        "",
        "This file is generated from the public signatures and model annotations in the source tree.",
        "Run `python scripts/generate_api_reference.py` after changing public APIs, or use `--check` to verify it is current.",
        "",
        "## Public classes",
        "",
    ]

    for relative_path, names in PUBLIC_CLASSES:
        classes = _class_nodes(ROOT / relative_path)
        for name in names:
            lines.extend(_render_class(name, classes[name]))

    lines.extend(
        [
            "## Resource models",
            "",
            "All resource models inherit `FlumeModel`. Known fields are typed below. Unknown fields returned by Flume are also retained, available through attribute or mapping access, and included by `to_dict()`.",
            "",
        ]
    )
    model_classes = _class_nodes(ROOT / "pyflumeng" / "models.py")
    for name, node in model_classes.items():
        if name == "FlumeModel":
            continue
        bases = {_expr(base).split("[")[0] for base in node.bases}
        if "FlumeModel" not in bases and name != "FlumeResponse":
            continue
        lines.extend([f"### `{name}`", ""])
        if _first_line(node):
            lines.extend([_first_line(node), ""])
        fields = _model_fields(node)
        if fields:
            lines.extend(["| Field | Type |", "| --- | --- |"])
            for field, annotation in fields:
                lines.append(f"| `{field}` | `{annotation}` |")
            lines.append("")
        else:
            lines.extend(
                [
                    "Flume does not publish a stable field schema for this resource. The model intentionally remains open and preserves every key returned by the API.",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"{OUTPUT.relative_to(ROOT)} is out of date", file=sys.stderr)
            return 1
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
