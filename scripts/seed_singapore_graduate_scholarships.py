#!/usr/bin/env python3
"""
Seed Singapore graduate scholarships and link them to programs.

Includes scholarships from:
- NUS Research Scholarship
- NTU Graduate Scholarships
- SMU Graduate Scholarships
- SUTD Fellowships
- Singapore Government Scholarships (SINGA, A*STAR)

Usage:
    python scripts/seed_singapore_graduate_scholarships.py
"""

import sys
import uuid
from datetime import datetime
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


SINGAPORE_GRADUATE_SCHOLARSHIPS = [
    # ─────────────────────────────────────────────────────────────────────────────
    # GOVERNMENT SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "name": "Singapore International Graduate Award (SINGA)",
        "provider": "A*STAR Singapore",
        "amount": 48000.00,
        "currency": "SGD",
        "deadline": "2026-12-01",
        "description": (
            "Fully funded PhD scholarship for international students in science and engineering. "
            "Covers full tuition, monthly stipend of S$2,700-3,200, settling-in allowance of S$1,000, "
            "and airfare grant up to S$1,500. Tenable at NUS, NTU, SUTD, or SMU with A*STAR research."
        ),
        "source_url": "https://www.a-star.edu.sg/Scholarships/for-graduate-studies/singapore-international-graduate-award-singa",
        "eligibility": [
            {"type": "nationality", "value": "International (non-Singaporean)", "mandatory": True},
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "field_of_study", "value": "Science,Engineering,Computer Science,Data Science,Artificial Intelligence", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence", "Cybersecurity"],
    },
    {
        "name": "A*STAR Graduate Scholarship",
        "provider": "A*STAR Singapore",
        "amount": 60000.00,
        "currency": "SGD",
        "deadline": "2026-06-30",
        "description": (
            "Prestigious scholarship for PhD studies at top overseas universities followed by "
            "research at A*STAR. Covers full tuition, monthly stipend of S$3,500, and research funding. "
            "Requires service commitment to A*STAR after graduation."
        ),
        "source_url": "https://www.a-star.edu.sg/Scholarships/for-graduate-studies",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence"],
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # NUS GRADUATE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS Research Scholarship",
        "provider": "National University of Singapore",
        "amount": 36000.00,
        "currency": "SGD",
        "deadline": "2026-11-15",
        "description": (
            "Scholarship for full-time research Master's and PhD students at NUS. "
            "Covers full tuition fees and provides monthly stipend of S$2,200-2,700. "
            "Available to both local and international students with strong research potential."
        ),
        "source_url": "https://www.nus.edu.sg/registrar/graduate/scholarships",
        "eligibility": [
            {"type": "degree_level", "value": "masters,phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "field_of_study", "value": "Computer Science,Data Science,Artificial Intelligence,Cybersecurity", "mandatory": False},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence", "Cybersecurity"],
    },
    {
        "name": "NUS Graduate School Scholarship",
        "provider": "National University of Singapore",
        "amount": 42000.00,
        "currency": "SGD",
        "deadline": "2026-11-15",
        "description": (
            "Enhanced scholarship for outstanding PhD candidates at NUS. Covers full tuition, "
            "increased stipend, conference support, and research grants. For students with "
            "exceptional academic records and research potential."
        ),
        "source_url": "https://www.nus.edu.sg/registrar/graduate/scholarships",
        "eligibility": [
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence"],
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # NTU GRADUATE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "name": "Nanyang President's Graduate Scholarship",
        "provider": "Nanyang Technological University",
        "amount": 65000.00,
        "currency": "SGD",
        "deadline": "2026-12-31",
        "description": (
            "NTU's most prestigious PhD scholarship recognizing exceptional academic, research "
            "and leadership qualities. Covers full tuition, monthly stipend of S$4,300-5,300, "
            "overseas conference allowance (S$5,000/year), book and IT allowances."
        ),
        "source_url": "https://www.ntu.edu.sg/admissions/graduate/financialmatters/scholarships/npgs",
        "eligibility": [
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "other", "value": "Honours (Highest Distinction) or equivalent", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence", "Cybersecurity"],
    },
    {
        "name": "NTU Research Scholarship",
        "provider": "Nanyang Technological University",
        "amount": 36000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Scholarship for full-time research students pursuing Master's or PhD at NTU. "
            "Covers tuition fees and provides monthly stipend. Open to all nationalities "
            "with strong academic records and research aptitude."
        ),
        "source_url": "https://www.ntu.edu.sg/admissions/graduate/financialmatters/scholarships",
        "eligibility": [
            {"type": "degree_level", "value": "masters,phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence", "Cybersecurity"],
    },
    {
        "name": "NTU-CCDS Graduate Scholarship",
        "provider": "Nanyang Technological University",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Scholarship specifically for Master's students in the College of Computing and Data Science. "
            "Covers partial tuition and provides study grant. For students pursuing MSDS, MSAI, "
            "MCAAI, or MSCS programmes."
        ),
        "source_url": "https://www.ntu.edu.sg/computing/admissions/graduate-programmes",
        "eligibility": [
            {"type": "degree_level", "value": "masters", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "field_of_study", "value": "Computer Science,Data Science,Artificial Intelligence,Cybersecurity", "mandatory": True},
        ],
        "target_programs": ["Data Science", "Artificial Intelligence", "Computer Science", "Cybersecurity"],
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # SMU GRADUATE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "name": "SMU Graduate Scholarship",
        "provider": "Singapore Management University",
        "amount": 25000.00,
        "currency": "SGD",
        "deadline": "2026-04-30",
        "description": (
            "Merit-based scholarship for outstanding Master's students at SMU. "
            "Covers partial tuition and provides academic support. Available for "
            "MSc Computing, MITB, and other graduate programmes."
        ),
        "source_url": "https://computing.smu.edu.sg/programmes/scholarships",
        "eligibility": [
            {"type": "degree_level", "value": "masters", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science"],
    },
    {
        "name": "Lee Kong Chian Graduate Scholarship",
        "provider": "Singapore Management University",
        "amount": 50000.00,
        "currency": "SGD",
        "deadline": "2026-04-30",
        "description": (
            "Prestigious scholarship for exceptional PhD candidates at SMU. "
            "Covers full tuition, monthly stipend, and research support. "
            "Named after the philanthropist Lee Kong Chian."
        ),
        "source_url": "https://computing.smu.edu.sg/programmes/scholarships",
        "eligibility": [
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
        ],
        "target_programs": ["Computer Science", "Data Science", "Artificial Intelligence"],
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # SUTD GRADUATE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "name": "SUTD PhD President's Graduate Fellowship",
        "provider": "Singapore University of Technology and Design",
        "amount": 55000.00,
        "currency": "SGD",
        "deadline": "2026-04-15",
        "description": (
            "SUTD's top PhD fellowship covering full tuition for up to 4 years and monthly "
            "stipend of S$4,300-5,300 depending on nationality. Open to all nationalities "
            "pursuing research in technology and design."
        ),
        "source_url": "https://www.sutd.edu.sg/admissions/graduate/scholarship/",
        "eligibility": [
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
        ],
        "target_programs": ["Artificial Intelligence", "Cybersecurity", "Computer Science"],
    },
    {
        "name": "SUTD PhD Fellowship",
        "provider": "Singapore University of Technology and Design",
        "amount": 42000.00,
        "currency": "SGD",
        "deadline": "2026-04-15",
        "description": (
            "Fellowship for PhD students at SUTD covering full tuition for up to 4 years "
            "and monthly stipend of S$3,100-3,800. Additional S$500/month after passing "
            "qualifying examination."
        ),
        "source_url": "https://www.sutd.edu.sg/admissions/graduate/scholarship/",
        "eligibility": [
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
        ],
        "target_programs": ["Artificial Intelligence", "Cybersecurity", "Computer Science"],
    },
    {
        "name": "SUTD MEng Research Fellowship",
        "provider": "Singapore University of Technology and Design",
        "amount": 35000.00,
        "currency": "SGD",
        "deadline": "2026-04-15",
        "description": (
            "Fellowship for Master of Engineering (Research) students at SUTD. "
            "Covers full tuition for up to 18 months and monthly stipend of S$2,900-3,800. "
            "For students pursuing research-based Master's degrees."
        ),
        "source_url": "https://www.sutd.edu.sg/admissions/graduate/scholarship/",
        "eligibility": [
            {"type": "degree_level", "value": "masters", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
        ],
        "target_programs": ["Artificial Intelligence", "Cybersecurity", "Computer Science"],
    },
]


def seed_scholarships():
    """Seed Singapore graduate scholarships."""
    conn = get_connection()
    cursor = conn.cursor()

    scholarships_created = 0
    eligibility_created = 0

    for scholarship in SINGAPORE_GRADUATE_SCHOLARSHIPS:
        scholarship_id = str(uuid.uuid4())
        target_programs = scholarship.pop("target_programs", [])
        eligibility_criteria = scholarship.pop("eligibility", [])

        try:
            cursor.execute(
                """
                INSERT INTO scholarships (
                    id, name, provider, funding_amount, currency,
                    deadline, description, source_url, is_active, crawled_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    funding_amount = VALUES(funding_amount),
                    deadline = VALUES(deadline),
                    description = VALUES(description),
                    source_url = VALUES(source_url)
                """,
                (
                    scholarship_id,
                    scholarship["name"],
                    scholarship["provider"],
                    scholarship["amount"],
                    scholarship["currency"],
                    scholarship["deadline"],
                    scholarship["description"],
                    scholarship["source_url"],
                    True,
                    datetime.utcnow(),
                ),
            )

            if cursor.rowcount > 0:
                scholarships_created += 1
                print(f"  + Seeded: {scholarship['name']}")

                for criteria in eligibility_criteria:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO eligibility_criteria (
                                id, scholarship_id, criteria_type, criteria_value, is_mandatory
                            ) VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                str(uuid.uuid4()),
                                scholarship_id,
                                criteria["type"],
                                criteria["value"],
                                criteria.get("mandatory", True),
                            ),
                        )
                        eligibility_created += 1
                    except Exception as e:
                        print(f"    ! Eligibility error: {e}")
            else:
                print(f"  ~ Exists: {scholarship['name']}")

        except Exception as e:
            print(f"  ! Error seeding {scholarship['name']}: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n✓ Seeded {scholarships_created} scholarships with {eligibility_created} eligibility criteria")


if __name__ == "__main__":
    print("Seeding Singapore Graduate Scholarships...")
    seed_scholarships()
