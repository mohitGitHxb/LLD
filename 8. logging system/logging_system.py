import json
import sys
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Any, Optional

# ==========================================
# 1. Enums and Data Structures
# ==========================================

class LogLevel(Enum):
    """Explicitly assigned values to allow severity comparison."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    FATAL = 50

@dataclass(slots=True, kw_only=True)
class LogRecord:
    """Represents a single log event."""
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    context: dict[str, Any] = field(default_factory=dict)

# ==========================================
# 2. Strategies (Formatters)
# ==========================================

class Formatter(Protocol):
    """Strategy interface for formatting LogRecords."""
    def format(self, record: LogRecord) -> str:
        ...

class TextFormatter:
    """Standard plain-text formatting."""
    def format(self, record: LogRecord) -> str:
        time_str = record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ctx_str = f" | {record.context}" if record.context else ""
        return f"[{time_str}] [{record.level.name}] {record.logger_name}: {record.message}{ctx_str}"

class JSONFormatter:
    """Structured formatting for log aggregators (e.g., ELK, Splunk)."""
    def format(self, record: LogRecord) -> str:
        log_dict = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "logger": record.logger_name,
            "message": record.message,
            "context": record.context
        }
        return json.dumps(log_dict)

# ==========================================
# 3. Handlers (Destinations)
# ==========================================

class Handler(ABC):
    """Base class for all log destinations."""
    
    def __init__(self, level: LogLevel = LogLevel.INFO, formatter: Optional[Formatter] = None):
        self.level = level
        self.formatter = formatter or TextFormatter()

    def set_formatter(self, formatter: Formatter) -> None:
        self.formatter = formatter

    def set_level(self, level: LogLevel) -> None:
        self.level = level

    def handle(self, record: LogRecord) -> None:
        """Determines if this specific handler should process the record."""
        if record.level.value >= self.level.value:
            formatted_msg = self.formatter.format(record)
            self.emit(formatted_msg)

    @abstractmethod
    def emit(self, formatted_message: str) -> None:
        """Actually writes the log to the destination."""
        pass

class ConsoleHandler(Handler):
    """Outputs logs to standard output/error."""
    def emit(self, formatted_message: str) -> None:
        print(formatted_message)

class FileHandler(Handler):
    """Outputs logs to a specified file."""
    def __init__(self, filepath: str, level: LogLevel = LogLevel.INFO, formatter: Optional[Formatter] = None):
        super().__init__(level, formatter)
        self.filepath = filepath

    def emit(self, formatted_message: str) -> None:
        # In a production system, this would handle file rotation and asynchronous writing.
        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(formatted_message + '\n')

# ==========================================
# 4. Core Logger (The Publisher)
# ==========================================

class Logger:
    """The main interface for application code to emit logs."""
    
    def __init__(self, name: str, min_level: LogLevel = LogLevel.DEBUG):
        self.name = name
        self.min_level = min_level
        self._handlers: list[Handler] = []

    def add_handler(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def set_level(self, level: LogLevel) -> None:
        """Sets the global minimum logging level for this logger."""
        self.min_level = level

    def _log(self, level: LogLevel, message: str, context: Optional[dict[str, Any]] = None) -> None:
        # 1. Global Filter check
        if level.value < self.min_level.value:
            return

        # 2. Create the Log Record
        record = LogRecord(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            logger_name=self.name,
            context=context or {}
        )

        # 3. Dispatch to Handlers
        for handler in self._handlers:
            handler.handle(record)

    # Convenience Methods
    def debug(self, message: str, context: Optional[dict] = None) -> None:
        self._log(LogLevel.DEBUG, message, context)

    def info(self, message: str, context: Optional[dict] = None) -> None:
        self._log(LogLevel.INFO, message, context)

    def warning(self, message: str, context: Optional[dict] = None) -> None:
        self._log(LogLevel.WARNING, message, context)

    def error(self, message: str, context: Optional[dict] = None) -> None:
        self._log(LogLevel.ERROR, message, context)

    def fatal(self, message: str, context: Optional[dict] = None) -> None:
        self._log(LogLevel.FATAL, message, context)

# ==========================================
# 5. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. Initialize the Logger
    app_logger = Logger(name="PaymentService", min_level=LogLevel.DEBUG)

    # 2. Setup Handlers with different configurations
    
    # Console Handler: Only wants INFO and above, uses standard text
    console_handler = ConsoleHandler(level=LogLevel.INFO)
    console_handler.set_formatter(TextFormatter())
    
    # File Handler: Wants all details (DEBUG and above), formatted as JSON for ingestion
    file_handler = FileHandler(filepath="payment_service.log", level=LogLevel.DEBUG)
    file_handler.set_formatter(JSONFormatter())

    # 3. Register Handlers
    app_logger.add_handler(console_handler)
    app_logger.add_handler(file_handler)

    # 4. Generate Logs
    print("--- Simulating Application Events ---")
    
    # Will go to File (JSON), but NOT Console (Console needs INFO+)
    app_logger.debug("Parsing incoming payment payload", context={"payload_size": "2kb"})
    
    # Will go to both
    app_logger.info("Payment processed successfully", context={"transaction_id": "TXN-9912", "user_id": 441})
    
    # Will go to both
    app_logger.warning("API response time degraded", context={"latency_ms": 850, "endpoint": "/charge"})
    
    # Will go to both
    app_logger.error("Database connection failed during commit", context={"db_host": "db.prod.internal", "error_code": "E_CONN"})