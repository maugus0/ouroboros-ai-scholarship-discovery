#!/usr/bin/env python3
"""
Link scholarships to programs based on field matching and eligibility criteria.

This script:
1. Fetches all programs from the Program Discovery database
2. Fetches all scholarships from the Scholarship Discovery database
3. Creates links based on:
   - Field of study match
   - Degree level match
   - Country/provider match
   - Eligibility criteria compatibility

Usage:
    python scripts/link_scholarships_to_programs.py
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings

load_dotenv(ROOT_DIR / ".env")


FIELD_MAPPINGS = {
    "Computer Science": ["Computer Science", "Artificial Intelligence", "Data Science", "Cybersecurity", "Software Engineering"],
    "Data Science": ["Data Science", "Computer Science", "Artificial Intelligence", "Analytics", "Machine Learning"],
    "Artificial Intelligence": ["Artificial Intelligence", "Computer Science", "Data Science", "Machine Learning", "Deep Learning"],
    "Cybersecurity": ["Cybersecurity", "Computer Science", "Information Security", "Network Security"],
    "Software Engineering": ["Software Engineering", "Computer Science"],
    "Information Systems": ["Information Systems", "Computer Science", "Data Science"],
}

SINGAPORE_PROVIDERS = [
    "National University of Singapore",
    "Nanyang Technological University",
    "Singapore Management University",
    "Singapore University of Technology and Design",
    "A*STAR Singapore",
]


def get_scholarship_connection():
    """Connect to scholarship discovery database."""
    return mysql.connector.connect(
        host=settings.get_db_host(),
        port=settings.get_db_port(),
        database=settings.get_db_name(),
        user=settings.get_db_user(),
        password=settings.get_db_password(),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


def get_program_connection():
    """Connect to program discovery database.
    
    Note: We need to read from program discovery's database.
    By default, this uses the same DB server but different database name.
    Adjust connection parameters if needed.
    """
    db_host = os.getenv("PROGRAM_DB_HOST", settings.get_db_host())
    db_port = int(os.getenv("PROGRAM_DB_PORT", settings.get_db_port()))
    db_name = os.getenv("PROGRAM_DB_NAME", "ouroboros_program_db")
    db_user = os.getenv("PROGRAM_DB_USER", settings.get_db_user())
    db_password = os.getenv("PROGRAM_DB_PASSWORD", settings.get_db_password())
    
    return mysql.connector.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


def fetch_singapore_programs():
    """Fetch all programs in Singapore from program discovery database."""
    try:
        conn = get_program_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.id, p.program_name, p.degree_type, p.field, p.field_category,
                   i.name as institution_name, i.country
            FROM programs p
            JOIN institutions i ON p.institution_id = i.id
            WHERE i.country = 'Singapore' AND p.is_active = 1
        """)
        
        programs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"Found {len(programs)} programs in Singapore")
        return programs
        
    except Exception as e:
        print(f"Error fetching programs: {e}")
        print("Make sure the program discovery database is accessible.")
        return []


def fetch_scholarships():
    """Fetch all scholarships from scholarship discovery database."""
    conn = get_scholarship_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT s.id, s.name, s.provider, s.funding_amount, s.currency, s.deadline
        FROM scholarships s
        WHERE s.is_active = 1
    """)
    
    scholarships = cursor.fetchall()
    
    cursor.execute("""
        SELECT e.scholarship_id, e.criterion_type, e.criterion_value, e.is_mandatory
        FROM eligibility_criteria e
    """)
    
    eligibility = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    scholarship_eligibility = {}
    for e in eligibility:
        sid = e["scholarship_id"]
        if sid not in scholarship_eligibility:
            scholarship_eligibility[sid] = []
        scholarship_eligibility[sid].append({
            "scholarship_id": e["scholarship_id"],
            "criteria_type": e["criterion_type"],
            "criteria_value": e["criterion_value"],
            "is_mandatory": e["is_mandatory"],
        })
    
    for s in scholarships:
        s["eligibility"] = scholarship_eligibility.get(s["id"], [])
    
    print(f"Found {len(scholarships)} scholarships")
    return scholarships


def calculate_match_score(program, scholarship):
    """Calculate match score between a program and scholarship.
    
    Returns:
        tuple: (score, match_reasons) where score is 0.0-1.0
    """
    score = 0.0
    max_score = 0.0
    reasons = []
    
    provider_is_singapore = any(
        provider.lower() in scholarship["provider"].lower() 
        for provider in SINGAPORE_PROVIDERS
    )
    max_score += 30
    if provider_is_singapore:
        score += 30
        reasons.append("Singapore-based scholarship")
    
    program_field = program.get("field", "").lower()
    scholarship_eligibility = scholarship.get("eligibility", [])
    
    field_criteria = [
        e for e in scholarship_eligibility 
        if e["criteria_type"] == "field_of_study"
    ]
    
    max_score += 40
    if field_criteria:
        for fc in field_criteria:
            eligible_fields = [f.strip().lower() for f in fc["criteria_value"].split(",")]
            if program_field in eligible_fields:
                score += 40
                reasons.append(f"Field match: {program['field']}")
                break
            related_fields = FIELD_MAPPINGS.get(program.get("field", ""), [])
            for rf in related_fields:
                if rf.lower() in eligible_fields:
                    score += 30
                    reasons.append(f"Related field match: {rf}")
                    break
    else:
        if provider_is_singapore:
            score += 25
            reasons.append("General Singapore scholarship")
    
    degree_criteria = [
        e for e in scholarship_eligibility 
        if e["criteria_type"] == "degree_level"
    ]
    
    max_score += 30
    if degree_criteria:
        program_degree = program.get("degree_type", "").lower()
        for dc in degree_criteria:
            eligible_degrees = [d.strip().lower() for d in dc["criteria_value"].split(",")]
            if program_degree in eligible_degrees:
                score += 30
                reasons.append(f"Degree level match: {program_degree}")
                break
    else:
        score += 15
        reasons.append("No degree restriction")
    
    if max_score > 0:
        normalized_score = score / max_score
    else:
        normalized_score = 0.0
    
    return min(normalized_score, 1.0), reasons


def link_scholarships_to_programs():
    """Create links between scholarships and programs."""
    programs = fetch_singapore_programs()
    scholarships = fetch_scholarships()
    
    if not programs:
        print("\n⚠ No programs found. Make sure to seed programs first:")
        print("  cd ../ouroboros-ai-program-discovery")
        print("  python scripts/seed_singapore_cs_programs.py")
        return
    
    if not scholarships:
        print("\n⚠ No scholarships found. Make sure to seed scholarships first:")
        print("  python scripts/seed_singapore_graduate_scholarships.py")
        return
    
    conn = get_scholarship_connection()
    cursor = conn.cursor()
    
    links_created = 0
    links_updated = 0
    
    print("\nCreating scholarship-program links...")
    print("-" * 60)
    
    for program in programs:
        program_links = 0
        
        for scholarship in scholarships:
            score, reasons = calculate_match_score(program, scholarship)
            
            if score >= 0.5:
                link_id = str(uuid.uuid4())
                
                match_metadata = {
                    "match_reasons": reasons,
                    "program_field": program.get("field"),
                    "program_degree": program.get("degree_type"),
                    "scholarship_provider": scholarship.get("provider"),
                    "matched_at": datetime.now(timezone.utc).isoformat(),
                }
                
                try:
                    cursor.execute(
                        """
                        INSERT INTO scholarship_program_links (
                            id, scholarship_id, program_id, link_type, 
                            confidence_score, match_metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            confidence_score = VALUES(confidence_score),
                            match_metadata = VALUES(match_metadata),
                            updated_at = NOW()
                        """,
                        (
                            link_id,
                            scholarship["id"],
                            program["id"],
                            "field",
                            score,
                            json.dumps(match_metadata),
                        ),
                    )
                    
                    if cursor.rowcount == 1:
                        links_created += 1
                    elif cursor.rowcount == 2:
                        links_updated += 1
                    
                    program_links += 1
                    
                except Exception as e:
                    print(f"  ! Error linking: {e}")
        
        if program_links > 0:
            print(f"  {program['program_name'][:50]:<50} -> {program_links} scholarships")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("-" * 60)
    print(f"\n✓ Created {links_created} new links")
    print(f"✓ Updated {links_updated} existing links")
    print(f"✓ Total: {links_created + links_updated} scholarship-program links")


def show_link_summary():
    """Show summary of existing links."""
    conn = get_scholarship_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT scholarship_id) as scholarships,
               COUNT(DISTINCT program_id) as programs,
               AVG(confidence_score) as avg_score
        FROM scholarship_program_links
    """)
    
    stats = cursor.fetchone()
    
    cursor.execute("""
        SELECT s.name as scholarship_name, 
               COUNT(spl.id) as program_count,
               AVG(spl.confidence_score) as avg_score
        FROM scholarships s
        LEFT JOIN scholarship_program_links spl ON s.id = spl.scholarship_id
        GROUP BY s.id, s.name
        ORDER BY program_count DESC
        LIMIT 10
    """)
    
    top_scholarships = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    print("\n=== Link Summary ===")
    print(f"Total links: {stats['total']}")
    print(f"Unique scholarships linked: {stats['scholarships']}")
    print(f"Unique programs linked: {stats['programs']}")
    print(f"Average confidence score: {stats['avg_score']:.2f}" if stats['avg_score'] else "N/A")
    
    print("\nTop scholarships by program count:")
    for s in top_scholarships:
        print(f"  {s['scholarship_name'][:50]:<50} - {s['program_count']} programs")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Link scholarships to programs")
    parser.add_argument("--summary", action="store_true", help="Show link summary only")
    args = parser.parse_args()
    
    if args.summary:
        show_link_summary()
    else:
        link_scholarships_to_programs()
        show_link_summary()
