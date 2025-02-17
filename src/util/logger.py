from util import Paths

import logging

def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s:%(name)s:%(levelname)s> %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(Paths.log_path)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger
