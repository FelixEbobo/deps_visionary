import logging
from colorama import init, Fore

init(autoreset=True)


class ColorFormatter(logging.Formatter):
    # Change this dictionary to suit your coloring needs!
    COLORS = {
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "CRITICAL": Fore.RED,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)


def setup_logging():
    console = logging.StreamHandler()
    console.setFormatter(
        ColorFormatter(
            "%(asctime)-3s %(levelname)-5s %(name)-10s (%(filename)s).%(funcName)s %(message)s",
            datefmt="%Y-%m-%d %I:%M:%S",
        )
    )
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            console,
        ],
    )
