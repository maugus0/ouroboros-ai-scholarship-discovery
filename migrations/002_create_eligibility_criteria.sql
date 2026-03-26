CREATE TABLE IF NOT EXISTS eligibility_criteria (
    id VARCHAR(36) PRIMARY KEY,
    scholarship_id VARCHAR(36) NOT NULL,
    criterion_type ENUM(
        'min_gpa',
        'nationality',
        'region',
        'field_of_study',
        'degree_level',
        'language_test',
        'work_experience',
        'age_limit',
        'other'
    ) NOT NULL,
    criterion_value TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE,
    INDEX idx_scholarship_id (scholarship_id),
    INDEX idx_criterion_type (criterion_type),
    INDEX idx_is_mandatory (is_mandatory)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
