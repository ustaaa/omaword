#!/usr/bin/env python3
"""Compare pinned upstream and fork CLIs on contributor-original synthetic files.

Stdlib only. No office applications, user documents, network, or repo mutations.
Both programs must run on the same host with the same font inputs.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_warnings(value):
    """Do not normalize warnings away, even when both programs lose the same data."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"warning", "warnings", "lostslides", "damagedmedia", "no_oracle", "nooracle"}:
                require(item in (None, False, "", [], {}), f"nonempty {key}: {item}")
            check_warnings(item)
    elif isinstance(value, list):
        for item in value:
            check_warnings(item)


def parse_results(stdout, commands, app):
    lines = stdout.splitlines()
    require(len(lines) == len(commands), f"expected {len(commands)} command responses, got {len(lines)}")
    results = []
    for line, (command, _) in zip(lines, commands):
        prefix = command + (": " if app == "word" else " → ")
        require(line.startswith(prefix), f"unexpected command output: {line[:160]}")
        value = json.loads(line[len(prefix):])
        check_warnings(value)
        if command == "file.open" and app == "deck":
            for key in ("lostSlides", "damagedMedia", "missingFonts"):
                require(key in value and isinstance(value[key], list), f"missing damage/font field: {key}")
        if command == "file.saveAs":
            if app == "word":
                require(value.get("saved") is True, "save did not report saved=true")
            else:
                require(value.get("bytes", 0) > 0, "save did not report nonempty bytes")
        results.append(value)
    return results


def normalize(value, app):
    value = copy.deepcopy(value)
    if not isinstance(value, dict):
        return value
    if isinstance(value.get("path"), str):
        value["path"] = Path(value["path"]).name
    if app == "word":
        # Only wall-clock save stamps differ between sequential runs. Keep authors,
        # revision, text, styles, layout, selection and undo state observable.
        for key in ("created", "modified"):
            value.get("properties", {}).pop(key, None)
    return value


class Runner:
    def __init__(self, output, app):
        self.output = output
        self.app = app
        self.sequence = 0
        self.env = dict(os.environ, WORDCRAFT_REGION="en-US", OMAWORD_REGION="en-US", TZ="UTC")

    def call(self, binary, args, label):
        self.sequence += 1
        stem = self.output / f"{self.sequence:03}-{label}"
        command = [str(binary), *args]
        result = subprocess.run(command, capture_output=True, text=True, env=self.env, timeout=180)
        stem.with_suffix(".stdout").write_text(result.stdout)
        stem.with_suffix(".stderr").write_text(result.stderr)
        stem.with_suffix(".command.json").write_text(json.dumps(command, ensure_ascii=False, indent=2) + "\n")
        require(result.returncode == 0, f"{label}: exit {result.returncode}; see {stem}.stderr")
        require(not re.search(r"\bwarn(?:ing)?\b", result.stderr, re.I), f"{label}: warning on stderr")
        return result.stdout

    def commands(self, binary, commands, label):
        args = ["run", "--print"]
        for name, params in commands:
            args += ["--cmd", name + "=" + json.dumps(params, ensure_ascii=False, separators=(",", ":"))]
        return parse_results(self.call(binary, args, label), commands, self.app)


def observe(runner, binary, path, folder, manifest):
    commands = [["file.open", {"path": str(path)}], ["document.inspect", {}]]
    if runner.app == "deck":
        commands += [["slide.inspect", {"index": 0}], ["slide.inspect", {"index": 1}]]
    results = runner.commands(binary, commands, folder.name + "-reopen")
    observations = [normalize(value, runner.app) for value in results[1:]]
    text = json.dumps(observations, ensure_ascii=False)
    for marker in manifest["expected_text"]:
        require(marker in text, f"{folder.name}: expected content absent: {marker}")
    if runner.app == "word":
        require(any(b.get("type") == "table" for b in observations[0]["blocks"]), "table lost")
        require(any(run.get("props", {}).get("bold") is True for b in observations[0]["blocks"] for run in b.get("runs", [])), "bold run lost")
        count = observations[0]["pages"]
    else:
        require(len(observations[0]["slides"]) == 2, "slide count changed")
        require(any(s.get("kind") == "table" for s in observations[2]["shapes"]), "table lost")
        # Include the full shape, not only the inspection summary's text and box.
        detailed = [["file.open", {"path": str(path)}]]
        for slide in observations[1:]:
            detailed.append(["slide.go", {"index": slide["index"]}])
            detailed.extend([["shape.inspect", {"id": shape["id"]}] for shape in slide["shapes"]])
        full = runner.commands(binary, detailed, folder.name + "-shapes")
        observations.extend(result for (command, _), result in zip(detailed, full) if command == "shape.inspect")
        count = len(observations[0]["slides"])
    require(0 < count <= 6, f"unexpected render count: {count}")
    renders = []
    for index in range(count):
        png = folder / f"page-{index}.png"
        options = ["--page", str(index + 1)] if runner.app == "word" else ["--slide", str(index)]
        runner.call(binary, ["render", str(path), str(png), *options, "--scale", "1"], folder.name + f"-render-{index}")
        require(png.is_file() and png.stat().st_size > 0, "render missing")
        renders.append(digest(png))
    # missingFonts is retained as evidence and compared, but shared upstream fallback
    # is not presented as proof that those fonts are installed.
    out = {"observations": observations, "render_sha256": renders, "open_response": results[0]}
    (folder / "observations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


def compare(left, right, app):
    require(left["observations"] == right["observations"], "semantic observations differ; inspect observations.json")
    require(left["render_sha256"] == right["render_sha256"], "render hashes differ")
    require(left["edit_results"] == right["edit_results"], "edit/undo/redo/save command responses differ")
    if app == "deck":
        require(left["open_response"]["missingFonts"] == right["open_response"]["missingFonts"], "font fallback differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--fork", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new evidence directory; refuses overwrite")
    args = parser.parse_args()
    manifest_path = Path(__file__).with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text())
    args.upstream, args.fork, args.output = args.upstream.resolve(), args.fork.resolve(), args.output.resolve()
    require(args.upstream != args.fork, "upstream and fork must be distinct binaries")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"status": "failed", "platform": platform.platform(), "manifest": manifest,
              "manifest_sha256": digest(manifest_path), "binaries": {}, "cases": []}
    try:
        runner = Runner(args.output, manifest["app"])
        for label, binary in (("upstream", args.upstream), ("fork", args.fork)):
            report["binaries"][label] = {"path": str(binary), "sha256": digest(binary), "version": runner.call(binary, ["--version"], label + "-version").strip()}
        for case in manifest["cases"]:
            case_dir = args.output / case["name"]
            case_dir.mkdir()
            source = case_dir / ("source." + case["extension"])
            create = manifest["create"] + [["file.saveAs", {"path": str(source)}]]
            runner.commands(args.upstream, create, case["name"] + "-create")
            require(source.is_file() and source.stat().st_size > 0, "fixture creation did not save a file")
            source_hash = digest(source)
            source.chmod(0o444)
            values = []
            for label, binary in (("upstream", args.upstream), ("fork", args.fork)):
                folder = case_dir / label
                folder.mkdir()
                saved = folder / ("edited." + case["extension"])
                commands = [["file.open", {"path": str(source)}]] + manifest["edit"] + [["file.saveAs", {"path": str(saved)}]]
                edit_results = runner.commands(binary, commands, case["name"] + "-" + label + "-edit")
                states = [r for (c, _), r in zip(commands, edit_results) if c == "document.inspect"]
                require(len(states) == 2, "expected undo and redo observations")
                marker = manifest["undo_marker"]
                require(marker not in json.dumps(states[0], ensure_ascii=False), "undo retained edited content")
                require(marker in json.dumps(states[1], ensure_ascii=False), "redo did not restore edited content")
                value = observe(runner, binary, saved, folder, manifest)
                value["edit_results"] = [normalize(r, manifest["app"]) for r in edit_results]
                values.append(value)
                require(digest(source) == source_hash, f"{label} modified the shared input")
            compare(*values, manifest["app"])
            report["cases"].append({"name": case["name"], "status": "passed", "source_sha256_before": source_hash, "source_sha256_after": digest(source), "render_sha256": values[0]["render_sha256"], "missingFonts": values[0]["open_response"].get("missingFonts", "not exposed by Word API")})
        for label, binary in (("upstream", args.upstream), ("fork", args.fork)):
            require(digest(binary) == report["binaries"][label]["sha256"], f"{label} binary changed during validation")
        report["status"] = "passed"
    except Exception as error:
        # Unexpected validator failures must leave evidence and fail, never look like a pass.
        report["error"] = f"{type(error).__name__}: {error}"
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]), "report": str(args.output / "report.json"), "error": report.get("error")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
