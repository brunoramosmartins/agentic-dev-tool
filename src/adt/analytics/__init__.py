"""Learning analytics: structured logging of supervised sessions.

The analytics layer builds on Phase 8 tracing but writes to a dedicated
rotating log at ``~/.adt/logs/learning.jsonl``. This keeps learning signal
separate from general request traces so stats aggregation stays cheap and
the main log can be rotated independently.
"""

from adt.analytics.events import LearningEvent, categorize_issue
from adt.analytics.logger import log_learning_event, setup_learning_logger
from adt.analytics.reader import read_learning_events
from adt.analytics.stats import LearningStats, compute_stats

__all__ = [
    "LearningEvent",
    "LearningStats",
    "categorize_issue",
    "compute_stats",
    "log_learning_event",
    "read_learning_events",
    "setup_learning_logger",
]
