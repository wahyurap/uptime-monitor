from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Uptime Monitor"
    database_url: str = "postgresql+asyncpg://uptime:uptime@localhost:5432/uptime_monitor"
    database_url_sync: str = "postgresql://uptime:uptime@localhost:5432/uptime_monitor"

    # Ping defaults
    default_ping_interval: int = 60  # seconds
    ping_timeout: float = 5.0  # seconds (increased for VPN/private network latency)
    ping_retries: int = 3
    ping_batch_size: int = 50

    # Data retention
    ping_retention_days: int = 90

    # Dashboard
    dashboard_refresh_seconds: int = 30

    model_config = {"env_prefix": "UPTIME_"}


settings = Settings()
