import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def get_logger(service_name):
    base_dir = Path(__file__).resolve().parent.parent / "SharedData/logs"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = base_dir / f"{service_name}.log"

    logger = logging.getLogger(service_name)
    
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        
        handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
    return logger