import logging
import sys

def setup_logger():
    """
    Configures and returns a root logger that prints to the console.
    """
    logger = logging.getLogger("auto_deployer")
    logger.setLevel(logging.INFO)

    # Prevent propagation to avoid duplicate logs if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] - [%(levelname)s] - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Initialize a global logger instance for easy import
log = setup_logger()