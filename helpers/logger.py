import datetime
import logging
import os
import sys
import zoneinfo

from .colorize import AnsiColors


class LoggerHandler(AnsiColors):
    def __init__(self, **options):
        super().__init__()
        self.tz = zoneinfo.ZoneInfo(options.get("tz", "Asia/Jakarta"))
        self.fmt = options.get(
            "fmt",
            "{asctime} {levelname} {module}:{funcName}:{lineno} {message}",
        )
        self.datefmt = options.get("datefmt", "%Y-%m-%d %H:%M:%S %Z")
        self.colors = {
            "INFO": self.GREEN,
            "DEBUG": self.BLUE,
            "WARNING": self.YELLOW,
            "ERROR": self.RED,
            "CRITICAL": self.MAGENTA,
            "TIME": self.WHITE,
            "MODULE": self.CYAN,
            "PIPE": self.PURPLE,
            "RESET": self.RESET,
        }

    def formatTime(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now.astimezone(self.tz).strftime(self.datefmt)

    def format(self, record):
        level_color = self.colors.get(record["levelname"], self.RESET)
        pipe = self.colors["PIPE"]
        level = f"{pipe}│ {level_color}{record['levelname']:<8}"
        message = f"{pipe}│ {level_color}{record['message']}{self.RESET}"
        module = f"{pipe}│ {self.colors['MODULE']}{os.path.basename(record.get('module', '<unknown>'))}"
        return self.fmt.format(
            asctime=f"{self.colors['TIME']}[ {self.formatTime()} ]",
            levelname=level,
            module=module,
            funcName=record.get("funcName", "<unknown>"),
            lineno=record.get("lineno", 0),
            message=message,
        )

    def print(self, message, isPrint=True):
        head = f"{self.CYAN}[ {self.WHITE}{self.formatTime()} {self.CYAN}] {self.WHITE}│ {message}{self.RESET}"
        if isPrint:
            print(f"\033[2K{head}")
        else:
            return head

    def log(self, level, message):
        frame = sys._getframe(2)
        record = {
            "levelname": level,
            "module": os.path.basename(frame.f_globals.get("__file__", "<unknown>")),
            "funcName": frame.f_code.co_name,
            "lineno": frame.f_lineno,
            "message": message,
        }
        print(f"\033[2K{self.format(record)}")

    def debug(self, message):
        self.log("DEBUG", message)

    def info(self, message):
        self.log("INFO", message)

    def warning(self, message):
        self.log("WARNING", message)

    def error(self, message):
        self.log("ERROR", message)

    def critical(self, message):
        self.log("CRITICAL", message)


class CustomLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.formatter_util = LoggerHandler()

    def emit(self, record):
        custom_record = {
            "levelname": record.levelname,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }
        try:
            print(f"\033[2K{self.formatter_util.format(custom_record)}")
        except Exception:
            self.handleError(record)