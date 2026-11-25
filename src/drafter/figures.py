"""Render figures; output names belong to each source file."""

from __future__ import annotations

import base64
import re
import subprocess
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import unquote

import click


def output_path(source: Path, name: str, figures: Path) -> Path:
    output = (source.parent / name).resolve()
    if not output.is_relative_to(figures) or output.suffix.lower() not in {".svg", ".png", ".pdf"}:
        raise click.ClickException("output must be an SVG, PNG or PDF path under figures/.")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def render(mode: str | None, path: Path, root: Path) -> None:
    source = path.resolve()
    figures = (root / "figures").resolve()
    if not source.is_file() or not source.is_relative_to(figures):
        raise click.ClickException("Specify an existing source file under figures/.")
    expected = {
        "drawio": {".drawio"},
        "mermaid": {".mmd", ".mermaid"},
        "plantuml": {".puml", ".plantuml"},
        "python": {".py"},
    }
    if mode is None:
        mode = next(
            (name for name, suffixes in expected.items() if source.suffix.lower() in suffixes), None
        )
    if mode is None:
        raise click.ClickException("Cannot detect figure type from the file extension.")
    if source.suffix.lower() not in expected[mode]:
        raise click.ClickException(f"Source extension does not match mode {mode}.")
    commands: list[list[str]] = []
    if mode == "python":
        commands.append(["uv", "run", "--script", str(source)])
    elif mode in {"mermaid", "plantuml"}:
        marker = "%%" if mode == "mermaid" else "'"
        names = re.findall(
            rf"^\s*{marker}\s*output:\s*(.+?)\s*$", source.read_text(encoding="utf-8"), re.M
        )
        if len(names) != 1:
            raise click.ClickException(f"Set exactly one '{marker} output: filename.svg' comment.")
        output = output_path(source, names[0], figures)
        if mode == "mermaid":
            commands.append(["mmdc", "-i", str(source), "-o", str(output)])
        else:
            try:
                with output.open("wb") as stream:
                    result = subprocess.run(
                        ["plantuml", "-pipe", f"-t{output.suffix[1:]}", "-charset", "UTF-8"],
                        input=source.read_bytes(),
                        stdout=stream,
                        cwd=source.parent,
                        check=False,
                    )
            except OSError as exc:
                raise click.ClickException(str(exc)) from exc
            if result.returncode:
                raise click.exceptions.Exit(result.returncode)
            return
    else:
        try:
            document = ET.parse(source).getroot()
            pages = document.findall("diagram") if document.tag == "mxfile" else [document]
            outputs: set[Path] = set()
            for index, page in enumerate(pages):
                model = page.find("mxGraphModel") if page.tag == "diagram" else page
                if model is None:
                    model = ET.fromstring(
                        unquote(
                            zlib.decompress(
                                base64.b64decode(page.text or ""),
                                -15,
                            ).decode("utf-8")
                        )
                    )
                names = [cell.get("output") for cell in model.iter() if cell.get("id") == "0"]
                if not names or not names[0]:
                    raise click.ClickException(
                        "Set the draw.io page's global data property 'output'."
                    )
                output = output_path(source, names[0], figures)
                if output in outputs:
                    raise click.ClickException(
                        "Each draw.io page must have a distinct output path."
                    )
                outputs.add(output)
                command = [
                    "drawio",
                    "--export",
                    "--format",
                    output.suffix[1:],
                    "--page-index",
                    str(index),
                    "--output",
                    str(output),
                    str(source),
                ]
                if output.suffix.lower() == ".svg":
                    command.extend(["--svg-theme", "light", "--embed-svg-fonts", "false"])
                commands.append(command)
            if not pages:
                raise click.ClickException("No diagram pages found.")
        except (ET.ParseError, ValueError, zlib.error) as exc:
            raise click.ClickException(f"Invalid draw.io source: {exc}") from exc
    for command in commands:
        try:
            result = subprocess.run(command, cwd=source.parent, check=False)
        except OSError as exc:
            raise click.ClickException(str(exc)) from exc
        if result.returncode:
            raise click.exceptions.Exit(result.returncode)
