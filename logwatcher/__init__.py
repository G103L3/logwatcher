"""LogWatcher: A lightweight log monitoring and analysis tool."""

__version__ = "0.2.1"
__author__ = "LogWatcher Team"
__email__ = "support@logwatcher.dev"
__description__ = "A lightweight, extensible log monitoring and analysis tool."

# Import core classes and functions for convenient access
from logwatcher.core import LogWatcher, LogEntry
from logwatcher.filters import RegexFilter, LevelFilter, TimeRangeFilter
from logwatcher.formatters import JSONFormatter, PlainTextFormatter, ColoredFormatter
from logwatcher.handlers import FileHandler, StdoutHandler, WebhookHandler

# Package-level convenience aliases
Watcher = LogWatcher
Entry = LogEntry

# Optional: expose common filter and formatter instances
default_formatter = PlainTextFormatter()
default_filter = RegexFilter(pattern=r".*")  # matches all lines

# Define public API
__all__ = [
    "LogWatcher",
    "Watcher",
    "LogEntry",
    "Entry",
    "RegexFilter",
    "LevelFilter",
    "TimeRangeFilter",
    "JSONFormatter",
    "PlainTextFormatter",
    "ColoredFormatter",
    "FileHandler",
    "StdoutHandler",
    "WebhookHandler",
    "default_formatter",
    "default_filter",
]