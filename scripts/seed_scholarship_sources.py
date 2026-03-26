"""Seed the database with top scholarship sources for initial crawling."""

import sys
import uuid
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings

load_dotenv(ROOT_DIR / ".env")


def get_connection():
    return mysql.connector.connect(
        host=settings.get_db_host(),
        port=settings.get_db_port(),
        database=settings.get_db_name(),
        user=settings.get_db_user(),
        password=settings.get_db_password(),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


SCHOLARSHIPS = [
    ("China Scholarship Council (CSC) Full Scholarship", "CSC", 30000.00, "USD", "2026-03-31",
     "Full scholarship for international students studying in China.",
     "https://www.csc.edu.cn/laihua"),
    ("UK Chevening Scholarship", "UK Government", 18000.00, "GBP", "2026-11-07",
     "Fully funded master's scholarship for outstanding emerging leaders.",
     "https://www.chevening.org/scholarships/"),
    ("US Fulbright Program", "US Government", 40000.00, "USD", "2026-10-15",
     "Full grants for international students and scholars for study and research.",
     "https://foreign.fulbrightonline.org/"),
    ("German DAAD Scholarship", "DAAD", 25000.00, "EUR", "2026-10-31",
     "Scholarships for international students to study in Germany.",
     "https://www.daad.de/en/study-and-research-in-germany/scholarships/"),
    ("Australian Government Research Training Program", "Australian Government", 35000.00, "AUD", "2026-08-31",
     "Funding for domestic and international students undertaking research degrees.",
     "https://www.education.gov.au/research-training-program"),
    ("Swiss Government Excellence Scholarship", "Swiss Government", 22000.00, "CHF", "2026-12-15",
     "Scholarships for foreign scholars and artists in Switzerland.",
     "https://www.sbfi.admin.ch/sbfi/en/home/education/scholarships-and-grants.html"),
    ("Japanese MEXT Scholarship", "MEXT Japan", 28000.00, "USD", "2026-04-30",
     "Full scholarship for international students to study in Japan.",
     "https://www.mext.go.jp/en/policy/education/highered/title02/detail02/sdetail02/1373897.htm"),
    ("Gates Cambridge Scholarship", "Gates Cambridge Trust", 45000.00, "GBP", "2026-12-03",
     "Full-cost scholarship for outstanding applicants to pursue postgraduate study at Cambridge.",
     "https://www.gatescambridge.org/"),
    ("Rhodes Scholarship (Oxford)", "Rhodes Trust", 50000.00, "GBP", "2026-10-01",
     "Postgraduate scholarship at the University of Oxford.",
     "https://www.rhodeshouse.ox.ac.uk/scholarships/"),
    ("Erasmus Mundus Joint Master Degree", "European Commission", 25000.00, "EUR", "2026-01-15",
     "Funded master's programmes offered by consortia of higher education institutions.",
     "https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters"),
    ("MIT Presidential Fellowship", "MIT", 55000.00, "USD", "2026-12-15",
     "Full fellowship for outstanding incoming graduate students at MIT.",
     "https://oge.mit.edu/finances/fellowships/"),
    ("Stanford Knight-Hennessy Scholars", "Stanford University", 60000.00, "USD", "2026-10-12",
     "Full funding for graduate studies at Stanford University.",
     "https://knight-hennessy.stanford.edu/"),
    ("Oxford Clarendon Fund", "University of Oxford", 40000.00, "GBP", "2026-01-22",
     "Full scholarships for outstanding graduate applicants at Oxford.",
     "https://www.clarendon.ox.ac.uk/"),
    ("NUS ASEAN Undergraduate Scholarship", "NUS", 20000.00, "SGD", "2026-03-20",
     "Full scholarship for ASEAN nationals at NUS.",
     "https://www.nus.edu.sg/oam/scholarships/"),
    ("ETH Zurich Excellence Scholarship", "ETH Zurich", 30000.00, "CHF", "2026-12-15",
     "Master's scholarship for outstanding students at ETH Zurich.",
     "https://ethz.ch/students/en/studies/financial/scholarships.html"),
]


def seed():
    conn = get_connection()
    cursor = conn.cursor()

    for name, provider, amount, currency, deadline, description, source_url in SCHOLARSHIPS:
        sid = str(uuid.uuid4())
        try:
            cursor.execute(
                """
                INSERT INTO scholarships (id, name, provider, funding_amount, currency, deadline,
                                          description, source_url, crawled_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
                ON DUPLICATE KEY UPDATE funding_amount = VALUES(funding_amount), deadline = VALUES(deadline)
                """,
                (sid, name, provider, amount, currency, deadline, description, source_url),
            )
            print(f"  Seeded: {name} ({provider})")
        except Exception as exc:
            print(f"  Error seeding {name}: {exc}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n{len(SCHOLARSHIPS)} scholarship sources seeded successfully.")


if __name__ == "__main__":
    seed()
