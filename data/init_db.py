"""
Initialize jobs database dengan schema yang dibutuhkan
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

def init_database():
    """Buat database dan tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Jobs table - daftar pekerjaan yang akan di-apply
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            url TEXT NOT NULL UNIQUE,
            platform TEXT DEFAULT 'unknown',
            location TEXT,
            salary TEXT,
            description TEXT,
            score REAL DEFAULT 0.0,
            applied INTEGER DEFAULT 0,
            applied_at TEXT,
            status TEXT DEFAULT 'pending',
            source TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Applications table - log setiap pengiriman lamaran
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            url TEXT NOT NULL,
            platform TEXT,
            status TEXT DEFAULT 'pending',
            fields_filled INTEGER DEFAULT 0,
            fields_skipped INTEGER DEFAULT 0,
            custom_questions INTEGER DEFAULT 0,
            captcha_detected INTEGER DEFAULT 0,
            error_message TEXT,
            dry_run INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    
    # Settings table - konfigurasi bot
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default settings
    default_settings = [
        ("max_applications_per_day", "20"),
        ("min_delay_minutes", "5"),
        ("max_delay_minutes", "15"),
        ("active_hours_start", "15"),
        ("active_hours_end", "5"),
        ("preferred_platforms", "greenhouse,lever,ashby,smartrecruiters,bamboohr"),
        ("skip_platforms", "workday"),
        ("headless", "false"),
        ("daily_notifications", "true"),
    ]
    
    for key, value in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized at: {DB_PATH}")
    return DB_PATH


def get_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)


if __name__ == "__main__":
    init_database()
