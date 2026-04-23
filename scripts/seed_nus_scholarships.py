#!/usr/bin/env python3
"""
Seed NUS scholarships into the database.

Comprehensive seeding of all NUS scholarship programs including:
- University-level scholarships (freshmen)
- International student scholarships
- Faculty-specific scholarships
- Government/external scholarships
- Current student scholarships

Usage:
    python scripts/seed_nus_scholarships.py
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


# ─────────────────────────────────────────────────────────────────────────────
# NUS SCHOLARSHIPS DATA
# ─────────────────────────────────────────────────────────────────────────────

NUS_SCHOLARSHIPS = [
    # ─────────────────────────────────────────────────────────────────────────
    # TOP NUS SCHOLARSHIPS (FRESHMEN - Singapore Citizens & PR)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS Global Merit Scholarship",
        "provider": "National University of Singapore",
        "amount": 50000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "NUS's most prestigious undergraduate scholarship covering full tuition, "
            "annual living allowance, accommodation, computer allowance, overseas "
            "enrichment allowance, and guaranteed overseas exchange/internship. "
            "For exceptional students with outstanding academic achievements and leadership."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-singapore-citizens/nus-global-merit-scholarship",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "NUS Merit Scholarship",
        "provider": "National University of Singapore",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Prestigious scholarship for academically excellent students covering "
            "full tuition, annual living allowance, and overseas enrichment support. "
            "Recognizes outstanding academic achievements and co-curricular excellence."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-singapore-citizens/nus-merit-scholarship",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "NUS Undergraduate Scholarship",
        "provider": "National University of Singapore",
        "amount": 20000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Scholarship for outstanding freshmen covering subsidized tuition fees "
            "and overseas enrichment opportunities. Awarded based on academic merit "
            "and all-round excellence."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-singapore-citizens/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # TALENT & SPECIAL SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS AI Talent Scholarship",
        "provider": "National University of Singapore",
        "amount": 25000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Scholarship for students with exceptional aptitude in AI and machine learning. "
            "Covers tuition, mentorship from AI researchers, and internship opportunities "
            "at leading AI companies and research labs."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "field_of_study", "value": "Computer Science,Artificial Intelligence,Data Science", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate,masters", "mandatory": True},
        ],
    },
    {
        "name": "NUS Sports Scholarship",
        "provider": "National University of Singapore",
        "amount": 15000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For outstanding student-athletes who have represented Singapore or achieved "
            "excellence at national/international level. Covers tuition, training support, "
            "and flexible academic arrangements for competitions."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "other", "value": "National/International athlete", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "NUS Performing and Visual Arts Scholarship",
        "provider": "National University of Singapore",
        "amount": 15000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For students with exceptional talent in performing or visual arts. "
            "Recipients must contribute to NUS arts and culture scene through "
            "performances, exhibitions, or arts leadership."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "other", "value": "Demonstrated arts excellence", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # LEADERSHIP & ENTREPRENEURSHIP SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "Stephen Riady Young Entrepreneur Scholarship",
        "provider": "National University of Singapore",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For aspiring entrepreneurs with demonstrated entrepreneurial achievements "
            "or potential. Includes mentorship, startup incubation support, and "
            "connection to NUS entrepreneurship ecosystem."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "other", "value": "Entrepreneurial track record or potential", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Wee Cho Yaw Future Leaders Award",
        "provider": "National University of Singapore",
        "amount": 35000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Prestigious leadership award for students with exceptional leadership "
            "qualities and commitment to community service. Includes leadership "
            "development programs and mentorship from industry leaders."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "other", "value": "Demonstrated leadership excellence", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # GOVERNMENT/NAMED AWARDS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "Lee Kuan Yew Scholarship (LKY-STEP)",
        "provider": "National University of Singapore",
        "amount": 40000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Named after Singapore's founding Prime Minister. For outstanding students "
            "committed to public service and nation-building. Includes overseas "
            "attachments to government agencies worldwide."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "other", "value": "Public service commitment", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Lee Hsien Loong Award",
        "provider": "National University of Singapore",
        "amount": 25000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Award recognizing students with exceptional academic achievement and "
            "significant contributions to community service. One of NUS's most "
            "distinguished student honors."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Temasek Foundation - Union Scholarship",
        "provider": "Temasek Foundation",
        "amount": 25000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Scholarship supporting students from ASEAN countries to study at NUS. "
            "Promotes regional ties and develops future leaders for Southeast Asia."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "region", "value": "ASEAN", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # ENGINEERING SCHOLARSHIP
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "University Engineering Scholarship",
        "provider": "National University of Singapore",
        "amount": 22000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For outstanding students pursuing engineering disciplines at NUS. "
            "Covers tuition fees and provides opportunities for industry internships "
            "and research attachments."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/",
        "eligibility": [
            {"type": "field_of_study", "value": "Engineering,Mechanical Engineering,Electrical Engineering,Civil Engineering,Chemical Engineering,Biomedical Engineering", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # INTERNATIONAL STUDENT SCHOLARSHIPS (KEY FOR FOREIGN APPLICANTS)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS ASEAN Undergraduate Scholarship",
        "provider": "National University of Singapore",
        "amount": 20000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Full scholarship for outstanding ASEAN nationals. Covers tuition fees, "
            "annual living allowance, airfare grant for one return trip, and "
            "hostel accommodation subsidy. One of the primary scholarships for ASEAN students."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-international-students/nus-asean-undergraduate-scholarship",
        "eligibility": [
            {"type": "nationality", "value": "ASEAN national (non-Singapore)", "mandatory": True},
            {"type": "region", "value": "ASEAN", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Science & Technology Undergraduate Scholarship",
        "provider": "National University of Singapore",
        "amount": 22000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For international students pursuing STEM programs at NUS. Covers full "
            "tuition fees and annual living allowance. Recipients commit to work in "
            "Singapore for 3 years after graduation (service bond)."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-international-students/",
        "eligibility": [
            {"type": "nationality", "value": "International (non-Singapore)", "mandatory": True},
            {"type": "field_of_study", "value": "Science,Engineering,Computing,Technology", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "3-year Singapore work bond required", "mandatory": True},
        ],
    },
    {
        "name": "NUS International Undergraduate Scholarship",
        "provider": "National University of Singapore",
        "amount": 25000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Comprehensive scholarship for exceptional international students across "
            "all disciplines. Covers full tuition, living allowance, and accommodation. "
            "Highly competitive with limited awards annually."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-international-students/",
        "eligibility": [
            {"type": "nationality", "value": "International (non-Singapore)", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Goh Keng Swee Scholarship",
        "provider": "National University of Singapore",
        "amount": 28000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "Named after Singapore's former Deputy Prime Minister. For outstanding "
            "ASEAN students showing exceptional academic ability and leadership. "
            "Covers full tuition and living expenses."
        ),
        "source_url": "https://www.nus.edu.sg/oam/scholarships/scholarships-for-freshmen-international-students/",
        "eligibility": [
            {"type": "region", "value": "ASEAN", "mandatory": True},
            {"type": "min_gpa", "value": "3.7", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # NUS COLLEGE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS College International Scholarship",
        "provider": "NUS College",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-20",
        "description": (
            "For exceptional international students admitted to NUS College, the "
            "honors program combining rigorous academics with residential experience. "
            "Covers tuition, accommodation, and enrichment programs."
        ),
        "source_url": "https://nuscollege.nus.edu.sg/admissions/scholarships-fees-aid/scholarships-and-financial-aid/",
        "eligibility": [
            {"type": "nationality", "value": "International", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "Admission to NUS College", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # NAMED SCHOLARSHIPS (CURRENT STUDENTS)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "Tan Lark Sye Scholarship",
        "provider": "National University of Singapore",
        "amount": 18000.00,
        "currency": "SGD",
        "deadline": "2026-05-31",
        "description": (
            "Named scholarship for current NUS students with excellent academic "
            "performance (GPA 4.0+) and demonstrated financial need. For students "
            "in any discipline showing dedication to learning."
        ),
        "source_url": "https://nus.edu.sg/oam/scholarships/scholarships-for-current-nus-undergraduates/list-of-named-scholarships",
        "eligibility": [
            {"type": "min_gpa", "value": "4.0", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "Current NUS student, financial need", "mandatory": True},
        ],
    },
    {
        "name": "John Anderson Scholarship",
        "provider": "National University of Singapore",
        "amount": 15000.00,
        "currency": "SGD",
        "deadline": "2026-05-31",
        "description": (
            "For current NUS students demonstrating academic excellence and "
            "contributions to university life. Named after a distinguished alumnus "
            "and supporter of education."
        ),
        "source_url": "https://nus.edu.sg/oam/scholarships/scholarships-for-current-nus-undergraduates/list-of-named-scholarships",
        "eligibility": [
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "Current NUS student", "mandatory": True},
        ],
    },
    {
        "name": "Feng & Family Scholarship",
        "provider": "National University of Singapore",
        "amount": 12000.00,
        "currency": "SGD",
        "deadline": "2026-05-31",
        "description": (
            "Scholarship for deserving current students showing academic promise "
            "and community involvement. Established by the Feng family to support "
            "education and student development."
        ),
        "source_url": "https://nus.edu.sg/oam/scholarships/scholarships-for-current-nus-undergraduates/list-of-named-scholarships",
        "eligibility": [
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "Current NUS student", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # EXTERNAL/GOVERNMENT SCHOLARSHIPS (BONDED)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "Public Service Commission (PSC) Scholarship",
        "provider": "Singapore Public Service Commission",
        "amount": 60000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Singapore's most prestigious government scholarship for future public "
            "service leaders. Covers full tuition at NUS or overseas, living allowance, "
            "and guaranteed position in Singapore government. 6-year bond required."
        ),
        "source_url": "https://www.psc.gov.sg/scholarships/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "6-year public service bond", "mandatory": True},
        ],
    },
    {
        "name": "Smart Nation Scholarship",
        "provider": "Government Technology Agency (GovTech)",
        "amount": 50000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "For students passionate about technology and digital transformation. "
            "Covers studies in tech-related fields with guaranteed position at "
            "GovTech or partner agencies after graduation."
        ),
        "source_url": "https://www.tech.gov.sg/careers/smart-nation-scholarship/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "field_of_study", "value": "Computer Science,Information Systems,Engineering", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
            {"type": "other", "value": "4-year bond with GovTech", "mandatory": True},
        ],
    },
    {
        "name": "SG Digital Scholarship",
        "provider": "Infocomm Media Development Authority (IMDA)",
        "amount": 45000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Scholarship developing Singapore's digital workforce. For students "
            "pursuing tech and digital media fields with commitment to work in "
            "Singapore's infocomm sector."
        ),
        "source_url": "https://www.imda.gov.sg/sgdigitalscholarship",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "field_of_study", "value": "Computer Science,Data Science,Information Systems,Digital Media", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "HDB Scholarship",
        "provider": "Housing & Development Board",
        "amount": 40000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "For students interested in urban planning, architecture, and public "
            "housing development. Covers tuition with guaranteed career at HDB "
            "shaping Singapore's housing landscape."
        ),
        "source_url": "https://www.hdb.gov.sg/cs/infoweb/about-us/careers/scholarships",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "field_of_study", "value": "Architecture,Engineering,Urban Planning,Real Estate", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "MOH Healthcare Scholarship",
        "provider": "Ministry of Health Singapore",
        "amount": 55000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "For students pursuing medicine, nursing, pharmacy, and allied health "
            "professions. Covers full tuition and provides structured career pathway "
            "in Singapore's healthcare system."
        ),
        "source_url": "https://www.moh.gov.sg/scholarships",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "field_of_study", "value": "Medicine,Nursing,Pharmacy,Dentistry", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # INDUSTRY SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "OCBC Scholarship",
        "provider": "OCBC Bank",
        "amount": 35000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Banking and finance scholarship from one of Singapore's largest banks. "
            "Covers tuition with internships and career opportunities in banking, "
            "fintech, and financial services."
        ),
        "source_url": "https://www.ocbc.com/group/careers/students-graduates/ocbc-scholarship.page",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "field_of_study", "value": "Business,Finance,Economics,Accountancy,Computing", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Singapore Power Scholarship",
        "provider": "Singapore Power Group",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "For students interested in energy sector careers. Covers engineering "
            "and business studies with pathway to careers in power generation, "
            "transmission, and sustainable energy."
        ),
        "source_url": "https://www.spgroup.com.sg/careers/scholarships",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "field_of_study", "value": "Engineering,Electrical Engineering,Business", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Raffles Medical Group Scholarship",
        "provider": "Raffles Medical Group",
        "amount": 40000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Healthcare scholarship from Singapore's leading private healthcare group. "
            "For medical and nursing students with career pathway in Raffles Hospital "
            "and affiliated institutions."
        ),
        "source_url": "https://www.rafflesmedicalgroup.com/careers/scholarships",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen/PR", "mandatory": True},
            {"type": "field_of_study", "value": "Medicine,Nursing", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    {
        "name": "Singapore-Industry Scholarship (SgIS)",
        "provider": "Ministry of Education Singapore",
        "amount": 35000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Partnership scholarship between MOE and leading Singapore companies. "
            "Matches students with sponsoring companies across various industries "
            "for internships and employment."
        ),
        "source_url": "https://www.sgis.gov.sg/",
        "eligibility": [
            {"type": "nationality", "value": "Singapore Citizen", "mandatory": True},
            {"type": "min_gpa", "value": "3.3", "mandatory": True},
            {"type": "degree_level", "value": "undergraduate", "mandatory": True},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # POSTGRADUATE SCHOLARSHIPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "NUS Research Scholarship",
        "provider": "National University of Singapore",
        "amount": 24000.00,
        "currency": "SGD",
        "deadline": "2026-01-15",
        "description": (
            "Full funding for PhD candidates at NUS including monthly stipend, "
            "tuition fees waiver, and conference travel support. Available across "
            "all research programs."
        ),
        "source_url": "https://nusgs.nus.edu.sg/scholarships/",
        "eligibility": [
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "phd", "mandatory": True},
            {"type": "other", "value": "Research aptitude, strong recommendations", "mandatory": True},
        ],
    },
    {
        "name": "NUS Graduate Scholarship for ASEAN Nationals",
        "provider": "National University of Singapore",
        "amount": 22000.00,
        "currency": "SGD",
        "deadline": "2026-01-15",
        "description": (
            "For outstanding ASEAN nationals pursuing graduate research degrees at NUS. "
            "Covers tuition, monthly stipend, and travel allowance for conferences."
        ),
        "source_url": "https://nusgs.nus.edu.sg/scholarships/",
        "eligibility": [
            {"type": "region", "value": "ASEAN", "mandatory": True},
            {"type": "min_gpa", "value": "3.5", "mandatory": True},
            {"type": "degree_level", "value": "masters,phd", "mandatory": True},
        ],
    },
    {
        "name": "A*STAR Graduate Scholarship",
        "provider": "Agency for Science, Technology and Research",
        "amount": 30000.00,
        "currency": "SGD",
        "deadline": "2026-03-31",
        "description": (
            "Premier scholarship for PhD students in science and engineering. "
            "Full funding to study at NUS with research attachment at A*STAR "
            "research institutes. Career pathway in Singapore's R&D ecosystem."
        ),
        "source_url": "https://www.a-star.edu.sg/Scholarships/",
        "eligibility": [
            {"type": "nationality", "value": "All nationalities", "mandatory": False},
            {"type": "field_of_study", "value": "Science,Engineering,Biomedical Sciences", "mandatory": True},
            {"type": "min_gpa", "value": "3.8", "mandatory": True},
            {"type": "degree_level", "value": "phd", "mandatory": True},
        ],
    },
]


def seed():
    """Seed NUS scholarships into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    scholarships_created = 0
    criteria_created = 0

    for scholarship in NUS_SCHOLARSHIPS:
        sid = str(uuid.uuid4())
        try:
            cursor.execute(
                """
                INSERT INTO scholarships (id, name, provider, funding_amount, currency, deadline,
                                          description, source_url, crawled_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE 
                    funding_amount = VALUES(funding_amount), 
                    deadline = VALUES(deadline),
                    description = VALUES(description)
                """,
                (
                    sid,
                    scholarship["name"],
                    scholarship["provider"],
                    scholarship["amount"],
                    scholarship["currency"],
                    scholarship["deadline"],
                    scholarship["description"],
                    scholarship["source_url"],
                    datetime.utcnow(),
                ),
            )
            scholarships_created += 1
            print(f"  ✓ Seeded: {scholarship['name']}")

            # Insert eligibility criteria
            for criterion in scholarship.get("eligibility", []):
                cid = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO eligibility_criteria 
                        (id, scholarship_id, criterion_type, criterion_value, is_mandatory)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        cid,
                        sid,
                        criterion["type"],
                        criterion["value"],
                        criterion.get("mandatory", True),
                    ),
                )
                criteria_created += 1

        except Exception as exc:
            print(f"  ✗ Error seeding {scholarship['name']}: {exc}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"NUS Scholarship Seeding Complete!")
    print(f"{'='*60}")
    print(f"  Scholarships created: {scholarships_created}")
    print(f"  Eligibility criteria created: {criteria_created}")
    print(f"{'='*60}")


if __name__ == "__main__":
    seed()
