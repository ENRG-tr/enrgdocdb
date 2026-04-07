"""
Centralized logging configuration for ENRG DocDB.

Provides consistent logging across the application with:
- Structured logging with contextual information
- Environment-based log levels
- File and console handlers
- Request context logging for web requests
"""

import logging as log_module
import sys
import os
import json
from datetime import datetime, timezone
from typing import Any, Optional
from flask import g, request
from flask_login import current_user


# Environment-based log level configuration
def get_log_level() -> int:
    """Get log level based on environment."""
    env = os.getenv("FLASK_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    if env == "production":
        return getattr(log_module, log_level.upper(), log_module.WARNING)
    else:
        return getattr(log_module, log_level.upper(), log_module.DEBUG)


# Custom log record factory for adding request context
def create_log_record(name: str, level: int, pathname: str, lineno: int,
                      msg: Any, args: tuple, exc_info: Any | None = None, func: str | None = None,
                      sinfo: Any = None):
    """Create a log record with request context if available."""
    record = log_module.LogRecord(name, level, pathname, lineno, msg, args, exc_info, func, sinfo)
    
    # Add request context
    if request is not None:
        record.request_id = getattr(g, 'request_id', None)
        record.client_ip = request.remote_addr
        record.path = request.path
        record.method = request.method
        record.user_id = current_user.id if current_user.is_authenticated else None
        record.user_email = current_user.email if current_user.is_authenticated else None
    
    return record


class RequestIdFilter(log_module.Filter):
    """Filter to add request ID to log records."""
    
    def filter(self, record):
        if hasattr(record, 'request_id'):
            record.request_id = record.request_id or "-"
        else:
            record.request_id = "-"
        return True


class StructuredFormatter(log_module.Formatter):
    """JSON formatter for structured logging (for production)."""
    
    def format(self, record):
        # Get the formatted message
        message = super().format(record)
        
        # Create structured log entry
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'client_ip'):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, 'path'):
            log_data["path"] = record.path
        if hasattr(record, 'method'):
            log_data["method"] = record.method
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'user_email'):
            log_data["user_email"] = record.user_email
        
        if hasattr(record, 'exc_info') and record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(log_module.Formatter):
    """Colored formatter for console output in development."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # Add request info
        if hasattr(record, 'request_id'):
            req_info = f"[{record.request_id}]"
        else:
            req_info = ""
        
        # Format with user info if available
        if hasattr(record, 'user_email') and record.user_email:
            user_info = f" [user: {record.user_email}]"
        else:
            user_info = ""
        
        # Format the message
        formatted = super().format(record)
        return f"{req_info}{formatted}{user_info}"


def setup_logging(app) -> log_module.Logger:
    """
    Configure logging for the application.
    
    Sets up:
    - Console handler with colored output for development
    - File handler for application logs
    - Optional JSON formatter for production
    - Request ID middleware for tracing
    """
    log_level = get_log_level()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logger
    logger = log_module.getLogger('enrgdocdb')
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler (all levels)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(app.root_path)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    file_handler = log_module.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_module.Formatter(log_format))
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = log_module.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if app.config.get('FLASK_ENV', 'development') != 'production':
        console_handler.setFormatter(ColoredFormatter(log_format))
    else:
        console_handler.setFormatter(StructuredFormatter())
    
    logger.addHandler(console_handler)
    
    # Request ID generation for tracing
    @app.before_request
    def before_request():
        import uuid
        g.request_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    
    # Request logging middleware
    @app.after_request
    def after_request(response):
        logger.log(
            log_module.INFO if response.status_code < 400 else log_module.WARNING,
            f"{request.method} {request.path} - {response.status_code} - {g.request_id}",
            extra={
                'request_id': getattr(g, 'request_id', None),
                'client_ip': request.remote_addr,
                'path': request.path,
                'method': request.method,
                'user_id': current_user.id if current_user.is_authenticated else None,
                'user_email': current_user.email if current_user.is_authenticated else None,
            }
        )
        return response
    
    # Error logging middleware
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}", exc_info=True, extra={
            'request_id': getattr(g, 'request_id', None),
            'client_ip': request.remote_addr if request else None,
            'path': request.path if request else None,
            'method': request.method if request else None,
        })
        return "An error occurred", 500
    
    # SQL query logging (debug mode only)
    if log_level <= log_module.DEBUG:
        log_module.getLogger('sqlalchemy.engine').setLevel(log_module.INFO)
        log_module.getLogger('sqlalchemy.engine').addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> log_module.Logger:
    """
    Get a logger instance for a module.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Operation started")
        logger.error("Operation failed", exc_info=True)
        logger.warning("Something might be wrong", extra={'field': 'value'})
    
    Args:
        name: The name of the logger (typically __name__)
    
    Returns:
        A configured logger instance
    """
    return log_module.getLogger(name)


# Convenience classes for common patterns
class AuthLogger:
    """Logger context for authentication events."""
    
    def __init__(self, logger: log_module.Logger):
        self.logger = logger
    
    def login_success(self, user_email: str, method: str = "password"):
        self.logger.info(
            f"User logged in: {user_email} via {method}",
            extra={
                'user_email': user_email,
                'auth_method': method,
            }
        )
    
    def login_failure(self, email: str, reason: str = "unknown"):
        self.logger.warning(
            f"Login failed: {email} - {reason}",
            extra={
                'user_email': email,
                'reason': reason,
            }
        )
    
    def logout(self, user_email: str):
        self.logger.info(f"User logged out: {user_email}")
    
    def registration_success(self, user_email: str):
        self.logger.info(f"User registered: {user_email}")
    
    def password_reset_requested(self, user_email: str):
        self.logger.info(f"Password reset requested: {user_email}")
    
    def two_factor_enabled(self, user_email: str, method: str):
        self.logger.info(
            f"2FA enabled for {user_email} via {method}",
            extra={'user_email': user_email, '2fa_method': method}
        )


class AuditLogger:
    """Logger for audit trail (who did what)."""
    
    def __init__(self, logger: log_module.Logger):
        self.logger = logger
    
    def create(self, resource_type: str, resource_id: int, user_email: str):
        self.logger.info(
            f"CREATE {resource_type} #{resource_id}",
            extra={
                'action': 'create',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_email': user_email,
            }
        )
    
    def update(self, resource_type: str, resource_id: int, user_email: str):
        self.logger.info(
            f"UPDATE {resource_type} #{resource_id}",
            extra={
                'action': 'update',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_email': user_email,
            }
        )
    
    def delete(self, resource_type: str, resource_id: int, user_email: str):
        self.logger.warning(
            f"DELETE {resource_type} #{resource_id}",
            extra={
                'action': 'delete',
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_email': user_email,
            }
        )
    
    def permission_denied(self, user_email: str, resource_type: str, resource_id: int, action: str):
        self.logger.warning(
            f"Permission denied: {user_email} tried to {action} {resource_type} #{resource_id}",
            extra={
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user_email': user_email,
            }
        )
