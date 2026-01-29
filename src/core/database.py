"""Database schema and management."""
import sqlite3
from pathlib import Path
from typing import Optional
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager."""
    
    def __init__(self, db_path: str = './receipts.db'):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure database file and schema exist."""
        db_existed = Path(self.db_path).exists()
        
        if not db_existed:
            logger.info(f"Creating new database at {self.db_path}")
        
        self._create_tables()
        
        if not db_existed:
            logger.info("Database schema initialized")
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection context manager.
        
        Yields:
            sqlite3.Connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Receipts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    original_filename TEXT,
                    receipt_type TEXT,
                    date TEXT,
                    amount TEXT,
                    description TEXT DEFAULT '',
                    extracted_data TEXT,
                    processing_successful INTEGER DEFAULT 1,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add description column if it doesn't exist (migration)
            try:
                cursor.execute("SELECT description FROM receipts LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding description column to receipts table")
                cursor.execute("ALTER TABLE receipts ADD COLUMN description TEXT DEFAULT ''")
            
            # Bank transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bank_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    amount TEXT,
                    description TEXT,
                    reference TEXT,
                    receipt_type TEXT,
                    matched_receipt_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (matched_receipt_id) REFERENCES receipts(id)
                )
            ''')

            # Migration: add receipt_type to bank_transactions if missing
            try:
                cursor.execute("SELECT receipt_type FROM bank_transactions LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding receipt_type column to bank_transactions table")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN receipt_type TEXT")
            
            # Migration: add csv_row_number to bank_transactions if missing
            try:
                cursor.execute("SELECT csv_row_number FROM bank_transactions LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding csv_row_number column to bank_transactions table")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN csv_row_number INTEGER")
            
            # Matches table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id INTEGER NOT NULL,
                    transaction_id INTEGER,
                    match_type TEXT,
                    confidence REAL DEFAULT 0.0,
                    is_conflict INTEGER DEFAULT 0,
                    conflict_accepted INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (receipt_id) REFERENCES receipts(id) ON DELETE CASCADE,
                    FOREIGN KEY (transaction_id) REFERENCES bank_transactions(id) ON DELETE SET NULL
                )
            ''')
            
            # Ignored receipts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ignored_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id INTEGER NOT NULL UNIQUE,
                    ignored_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    FOREIGN KEY (receipt_id) REFERENCES receipts(id) ON DELETE CASCADE
                )
            ''')
            
            # Processing queue table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    processed_at TEXT
                )
            ''')
            
            # Processor state table (singleton)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processor_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_running INTEGER DEFAULT 0,
                    is_paused INTEGER DEFAULT 0,
                    paused_at TEXT,
                    last_processed_file TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Initialize processor state if not exists
            cursor.execute('''
                INSERT OR IGNORE INTO processor_state (id, is_running, is_paused)
                VALUES (1, 0, 0)
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_receipts_date 
                ON receipts(date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_receipts_type 
                ON receipts(receipt_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_bank_date 
                ON bank_transactions(date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_matches_receipt 
                ON matches(receipt_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_matches_transaction 
                ON matches(transaction_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_queue_status 
                ON processing_queue(status)
            ''')
            
            # ===== ROC SKINCARE: Multi-worker tables =====
            
            # Workers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    activo INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_workers_nombre_lower 
                ON workers(LOWER(nombre))
            ''')
            
            # Periods table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    month_year TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    is_processing_active INTEGER DEFAULT 0,
                    csv_last_upload TEXT,
                    csv_file_path TEXT,
                    closed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE,
                    UNIQUE(worker_id, month_year)
                )
            ''')
            
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_periods_processing_active 
                ON periods(is_processing_active) 
                WHERE is_processing_active = 1
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_periods_worker ON periods(worker_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_periods_status ON periods(status)
            ''')
            
            # Period closures table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS period_closures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_id INTEGER NOT NULL,
                    closure_date TEXT NOT NULL,
                    export_path TEXT NOT NULL,
                    reopened_at TEXT,
                    reopen_reason TEXT,
                    stats_snapshot TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (period_id) REFERENCES periods(id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_closures_period ON period_closures(period_id)
            ''')
            
            # User roles table (for future)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    worker_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers(id)
                )
            ''')
            
            # ===== Migrations: Add worker_id and period_id to existing tables =====
            
            # Add to receipts
            try:
                cursor.execute("SELECT worker_id FROM receipts LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding worker_id and period_id to receipts table")
                cursor.execute("ALTER TABLE receipts ADD COLUMN worker_id INTEGER REFERENCES workers(id)")
                cursor.execute("ALTER TABLE receipts ADD COLUMN period_id INTEGER REFERENCES periods(id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_worker ON receipts(worker_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_period ON receipts(period_id)")
            
            # Add to bank_transactions
            try:
                cursor.execute("SELECT worker_id FROM bank_transactions LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding worker_id and period_id to bank_transactions table")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN worker_id INTEGER REFERENCES workers(id)")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN period_id INTEGER REFERENCES periods(id)")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN csv_upload_date TEXT")
                cursor.execute("ALTER TABLE bank_transactions ADD COLUMN csv_file_path TEXT")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_worker ON bank_transactions(worker_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_period ON bank_transactions(period_id)")
            
            # Add to processing_queue
            try:
                cursor.execute("SELECT period_id FROM processing_queue LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("Adding period_id to processing_queue table")
                cursor.execute("ALTER TABLE processing_queue ADD COLUMN period_id INTEGER REFERENCES periods(id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_period ON processing_queue(period_id)")
            
            conn.commit()
    
    def execute_script(self, script: str):
        """
        Execute SQL script.
        
        Args:
            script: SQL script to execute
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(script)
    
    def vacuum(self):
        """Vacuum database to reclaim space and optimize."""
        with self.get_connection() as conn:
            conn.execute('VACUUM')
        logger.info("Database vacuumed")


# Global database instance
_database: Optional[Database] = None


def get_database(db_path: str = './receipts.db') -> Database:
    """
    Get global database instance.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database instance
    """
    global _database
    if _database is None:
        _database = Database(db_path)
    return _database
