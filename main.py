from deps_visionary import create_app
from deps_visionary.log import setup_logging

setup_logging()
app = create_app()
