CREATE TABLE IF NOT EXISTS crawl_jobs (
    id VARCHAR(36) PRIMARY KEY,
    job_type ENUM('batch', 'on_demand') NOT NULL,
    target_url VARCHAR(500) NULL,
    target_source VARCHAR(100) NULL,
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT NULL,
    scholarships_crawled INT DEFAULT 0,
    scholarships_updated INT DEFAULT 0,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_job_type (job_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
