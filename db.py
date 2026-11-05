import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
from config import DB_PATH

DANGEROUS_KEYWORDS = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REINDEX|VACUUM|TRUNCATE)\b',
    re.IGNORECASE
)

def py_like(pattern: Any, text: Any) -> bool:
    if pattern is None or text is None:
        return False
    pattern_str = str(pattern).lower()
    text_str = str(text).lower()
    # Fast-path for common '%keyword%' pattern
    if pattern_str.startswith('%') and pattern_str.endswith('%') and '%' not in pattern_str[1:-1] and '_' not in pattern_str:
        return pattern_str[1:-1] in text_str
    regex = '^' + re.escape(pattern_str).replace(r'\%', '.*').replace(r'\_', '.') + '$'
    return bool(re.search(regex, text_str, re.DOTALL))

class DBClient:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Case-insensitive Unicode LIKE and LOWER for Uzbek/Russian Cyrillic support
        conn.create_function("like", 2, py_like)
        conn.create_function("lower", 1, lambda s: s.lower() if s is not None else None)
        return conn

    def execute_query(self, sql: str, max_rows: int = 50) -> Dict[str, Any]:
        """
        Executes a SELECT query safely and returns columns, rows, execution time, and error.
        """
        sql_clean = sql.strip().rstrip(';')
        
        # Security validation
        if not re.match(r'^\s*SELECT\b', sql_clean, re.IGNORECASE):
            return {
                "success": False,
                "error": "Security check failed: Only SELECT statements are permitted.",
                "columns": [],
                "rows": [],
                "elapsed_ms": 0
            }

        if DANGEROUS_KEYWORDS.search(sql_clean):
            return {
                "success": False,
                "error": "Security check failed: Query contains unauthorized keywords.",
                "columns": [],
                "rows": [],
                "elapsed_ms": 0
            }

        start = time.time()
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(sql_clean)
            
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = []
            for row in cur.fetchmany(max_rows):
                rows.append([row[col] for col in columns])
                
            elapsed_ms = (time.time() - start) * 1000
            return {
                "success": True,
                "error": None,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "elapsed_ms": round(elapsed_ms, 2)
            }
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return {
                "success": False,
                "error": str(e),
                "columns": [],
                "rows": [],
                "row_count": 0,
                "elapsed_ms": round(elapsed_ms, 2)
            }
        finally:
            if conn:
                conn.close()

db_client = DBClient()
