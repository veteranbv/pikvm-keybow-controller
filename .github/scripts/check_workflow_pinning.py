# Vendored copy of the shared workflow pinning check. Do not edit here;
# change it at its source and re-vendor.
"""Fail on unpinned workflow `uses:` references or untrusted `pull_request_target`.

Only the trusted review gate may run on `pull_request_target`; this is the
fallback where GitHub offers no Actions event policy for the repository.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

FULL_SHA_REF: Final = re.compile(r"^[0-9a-fA-F]{40}$")
LOCAL_USES_PREFIXES: Final = ("./", "../")
NON_GITHUB_ACTION_PREFIXES: Final = ("docker://",)
NON_SCALAR_USES_VALUE: Final = "<non-scalar uses value>"
YAML_PARSE_VALUE: Final = "<workflow yaml>"
TRUSTED_GATE_WORKFLOW: Final = "review-gate-trusted.yml"
GATED_EVENT: Final = "pull_request_target"


@dataclass(frozen=True)
class UsesRef:
    path: Path
    line: int
    value: str | None


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    value: str
    reason: str


def workflow_files(workflows_dir: Path) -> list[Path]:
    return sorted([*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")])


def scan_workflows(workflows_dir: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in workflow_files(workflows_dir):
        violations.extend(scan_workflow(path))
    return violations


def scan_workflow(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        uses_refs = collect_uses_refs(path)
    except yaml.YAMLError as exc:
        return [
            Violation(
                path=path,
                line=yaml_error_line(exc),
                value=YAML_PARSE_VALUE,
                reason=f"invalid workflow YAML: {yaml_error_message(exc)}",
            )
        ]

    if path.name != TRUSTED_GATE_WORKFLOW:
        violations.extend(
            Violation(
                path=path,
                line=line,
                value=GATED_EVENT,
                reason=f"only {TRUSTED_GATE_WORKFLOW} may run on {GATED_EVENT}",
            )
            for line in gated_event_lines(path)
        )

    for uses_ref in uses_refs:
        if uses_ref.value is None:
            violations.append(
                Violation(
                    path=uses_ref.path,
                    line=uses_ref.line,
                    value=NON_SCALAR_USES_VALUE,
                    reason="uses value is not a scalar string",
                )
            )
            continue

        value = uses_ref.value.strip()
        if not value or is_exempt_uses_ref(value):
            continue

        if "@" not in value:
            violations.append(
                Violation(
                    path=uses_ref.path,
                    line=uses_ref.line,
                    value=value,
                    reason="missing @<commit-sha> ref",
                )
            )
            continue

        ref = value.rsplit("@", 1)[1]
        if not FULL_SHA_REF.fullmatch(ref):
            violations.append(
                Violation(
                    path=uses_ref.path,
                    line=uses_ref.line,
                    value=value,
                    reason="ref is not a 40-character commit SHA",
                )
            )
    return violations


def collect_uses_refs(path: Path) -> list[UsesRef]:
    document = yaml.compose(path.read_text(encoding="utf-8"))
    if document is None:
        return []

    refs: list[UsesRef] = []
    collect_uses_refs_from_node(path, document, refs)
    return refs


def gated_event_lines(path: Path) -> list[int]:
    """Lines where the top-level `on:` (string, list or mapping) names the gated event."""
    document = yaml.compose(path.read_text(encoding="utf-8"))
    if not isinstance(document, MappingNode):
        return []
    lines: list[int] = []
    for key_node, value_node in document.value:
        if not isinstance(key_node, ScalarNode) or key_node.value != "on":
            continue
        events: list[ScalarNode]
        if isinstance(value_node, ScalarNode):
            events = [value_node]
        elif isinstance(value_node, SequenceNode):
            events = [item for item in value_node.value if isinstance(item, ScalarNode)]
        elif isinstance(value_node, MappingNode):
            events = [key for key, _ in value_node.value if isinstance(key, ScalarNode)]
        else:
            events = []
        lines.extend(node.start_mark.line + 1 for node in events if node.value == GATED_EVENT)
    return lines


def collect_uses_refs_from_node(path: Path, node: Node, refs: list[UsesRef]) -> None:
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode) and key_node.value == "uses":
                refs.append(
                    UsesRef(
                        path=path,
                        line=key_node.start_mark.line + 1,
                        value=value_node.value if isinstance(value_node, ScalarNode) else None,
                    )
                )
            collect_uses_refs_from_node(path, value_node, refs)
        return

    if isinstance(node, SequenceNode):
        for item in node.value:
            collect_uses_refs_from_node(path, item, refs)


def yaml_error_line(exc: yaml.YAMLError) -> int:
    mark = getattr(exc, "problem_mark", None)
    if mark is None:
        return 1
    return int(mark.line) + 1


def yaml_error_message(exc: yaml.YAMLError) -> str:
    return str(exc).splitlines()[0]


def is_exempt_uses_ref(value: str) -> bool:
    return value.startswith(LOCAL_USES_PREFIXES) or value.startswith(NON_GITHUB_ACTION_PREFIXES)


def format_violations(violations: Sequence[Violation]) -> str:
    lines = ["GitHub Actions workflow policy violations found:"]
    for violation in violations:
        lines.append(f"- {violation.path}:{violation.line}: {violation.value} ({violation.reason})")
    lines.append("")
    lines.append("Use a full 40-character commit SHA for external GitHub Actions references.")
    lines.append(f"Only {TRUSTED_GATE_WORKFLOW} may be triggered by {GATED_EVENT}.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workflows_dir",
        nargs="?",
        default=".github/workflows",
        type=Path,
        help="Directory containing GitHub Actions workflow YAML files.",
    )
    args = parser.parse_args(argv)

    workflows_dir = args.workflows_dir
    if not workflows_dir.is_dir():
        print(f"workflow directory not found: {workflows_dir}", file=sys.stderr)
        return 2

    files = workflow_files(workflows_dir)
    if not files:
        print(f"no workflow files found in {workflows_dir}", file=sys.stderr)
        return 2

    violations = scan_workflows(workflows_dir)
    if violations:
        print(format_violations(violations), file=sys.stderr)
        return 1
    print(f"workflow action pinning and {GATED_EVENT} use OK: {len(files)} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
