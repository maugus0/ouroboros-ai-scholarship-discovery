CREATE TABLE IF NOT EXISTS scholarship_program_links (
    id VARCHAR(36) PRIMARY KEY,
    scholarship_id VARCHAR(36) NOT NULL,
    program_id VARCHAR(36) NOT NULL,
    link_type ENUM('university', 'field', 'degree', 'geographic') NOT NULL,
    confidence_score DECIMAL(4, 3) NOT NULL,
    match_metadata JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE,
    INDEX idx_scholarship_id (scholarship_id),
    INDEX idx_program_id (program_id),
    INDEX idx_confidence_score (confidence_score DESC),
    UNIQUE KEY unique_scholarship_program (scholarship_id, program_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
