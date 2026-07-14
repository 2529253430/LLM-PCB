from pathlib import Path
import sqlite3

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据库文件
DB_PATH = BASE_DIR / "data" / "pcb.db"


def get_connection():
    """
    获取SQLite数据库连接
    """
    return sqlite3.connect(DB_PATH)