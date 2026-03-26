"""Data-access layer for the llm_call_logs table (raw SQL, aiomysql)."""

from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_base import MySQLBaseRepository
from app.utils.helpers import generate_uuid

logger = get_logger(__name__)


class LLMCallLogRepository(MySQLBaseRepository):
    """Audit logging for LLM API calls with token usage and cost tracking."""

    async def log_call(self, data: dict[str, Any]) -> str:
        """Record an LLM API call."""
        log_id = generate_uuid()
        query = """
            INSERT INTO llm_call_logs (
                id, operation, llm_provider, model_name,
                input_tokens, output_tokens, total_cost_usd,
                latency_ms, success, error_message,
                retry_count, trace_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            log_id,
            data["operation"],
            data["llm_provider"],
            data["model_name"],
            data.get("input_tokens"),
            data.get("output_tokens"),
            data.get("total_cost_usd"),
            data.get("latency_ms"),
            data["success"],
            data.get("error_message"),
            data.get("retry_count", 0),
            data.get("trace_id"),
        )
        await self.execute_write(query, params)
        return log_id

    async def get_cost_summary(self, days: int = 30) -> dict[str, Any]:
        """Return aggregated cost summary for recent LLM calls."""
        query = """
            SELECT
                llm_provider,
                COUNT(*) AS total_calls,
                SUM(input_tokens) AS total_input_tokens,
                SUM(output_tokens) AS total_output_tokens,
                SUM(total_cost_usd) AS total_cost,
                AVG(latency_ms) AS avg_latency_ms,
                SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) AS successful_calls
            FROM llm_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY llm_provider
        """
        rows = await self.execute_query(query, (days,))
        return {"providers": rows, "period_days": days}

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent LLM call logs."""
        query = "SELECT * FROM llm_call_logs ORDER BY created_at DESC LIMIT %s"
        return await self.execute_query(query, (limit,))
