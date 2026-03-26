CREATE TABLE IF NOT EXISTS llm_call_logs (
    id VARCHAR(36) PRIMARY KEY,
    operation VARCHAR(100) NOT NULL,
    llm_provider VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    input_tokens INT NULL,
    output_tokens INT NULL,
    total_cost_usd DECIMAL(10, 6) NULL,
    latency_ms INT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT NULL,
    retry_count INT DEFAULT 0,
    trace_id VARCHAR(36) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation (operation),
    INDEX idx_provider (llm_provider),
    INDEX idx_created_at (created_at),
    INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
