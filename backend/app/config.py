"""Application configuration loaded from environment variables / .env."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database ---------------------------------------------------------
    # PostgreSQL via Supabase in production, SQLite for local dev.
    database_url: str = "sqlite:///./bazaarpulse.db"

    # OpenAI ------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Keep the LLM call cheap: only classify reviews with a score that is
    # sufficiently representative.
    ai_min_review_length: int = 12

    # Data source -------------------------------------------------------
    # live (primary, real-time) → Playwright scraping of Flipkart/Amazon.in
    # mixed                     → live, fall back to simulation per cycle
    # simulation                → offline demo producer only
    scrape_mode: str = "live"

    # Scheduler ---------------------------------------------------------
    simulation_interval_minutes: int = 15
    enable_scheduler: bool = True
    reseed_on_start: bool = False

    # CORS --------------------------------------------------------------
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Scraper -----------------------------------------------------------
    scrape_headless: bool = True
    scrape_page_delay_ms: int = 4500

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def websocket_path(self) -> str:
        return "/ws/live-updates"

    def parse_cors(self) -> List[str]:
        if isinstance(self.cors_origins, str):
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return list(self.cors_origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
