import pandas as pd
from loguru import logger
import os

import socket

hostname = socket.gethostname()
logger.info(f"系统hostname: {hostname}")

import platform

system_name = platform.system()
if system_name.lower().startswith('win'):
    logger.info("当前操作系统为 Windows")
    db_info = {
        "database":"db_for_portfolio",
        "db_user":"root",
        "db_password":"385538",
        "db_url":"localhost",
        "db_port":3306

    }
else:
    logger.info(f"当前操作系统为 {system_name}")
    db_info = {"database": "db_for_portfolio",
               "db_user": "root",
               "db_password": "385538",
               "db_url": "localhost",
               "db_port": 3306}
