from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Uptime Monitor"
    database_url: str = "postgresql+asyncpg://uptime:uptime@localhost:5432/uptime_monitor"
    database_url_sync: str = "postgresql://uptime:uptime@localhost:5432/uptime_monitor"

    # Ping defaults
    default_ping_interval: int = 180  # seconds (3 min - optimized for 90 servers)
    ping_timeout: float = 3.0  # seconds (VPN latency, but not too long)
    ping_retries: int = 2  # Reduced from 3 to 2 (still covers timeout cases)
    ping_batch_size: int = 90  # All servers in one batch

    # Data retention
    ping_retention_days: int = 90

    # Dashboard
    dashboard_refresh_seconds: int = 30

    model_config = {"env_prefix": "UPTIME_"}


settings = Settings()
