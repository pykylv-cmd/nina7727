"""ONE NINA Executive Brain public boundary.

The repository predates this package with a small ``brain.py`` topic helper.
Load that file under a private name and re-export its public helpers so the V1
package does not break established callers while the single Brain evolves.
"""

import importlib.util
from pathlib import Path

from .brain_core import Brain, BrainContext
from .decision import Decision

_legacy_path = Path(__file__).resolve().parent.parent / "brain.py"
_legacy_spec = importlib.util.spec_from_file_location("_nina_legacy_brain", _legacy_path)
_legacy = importlib.util.module_from_spec(_legacy_spec)
if _legacy_spec.loader is None:  # pragma: no cover - import machinery contract
    raise ImportError("legacy_brain_loader_unavailable")
_legacy_spec.loader.exec_module(_legacy)

detect_topics = _legacy.detect_topics
analyze_memories = _legacy.analyze_memories
most_important_topic = _legacy.most_important_topic
build_brain_summary = _legacy.build_brain_summary

__all__ = [
    "Brain", "BrainContext", "Decision", "detect_topics", "analyze_memories",
    "most_important_topic", "build_brain_summary",
]
