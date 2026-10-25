from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_SECRET = "dev-secret-change-me-dev-secret-change-me"  # 32+ chars so JWT libraries do not warn


class Settings(BaseSettings):
    environment: str = "development"  # set ENVIRONMENT=production when deployed
    mongodb_uri: str = "mongodb://localhost:27017"
    db_name: str = "careerpilot"
    frontend_origin: str = "http://localhost:5173"
    jwt_secret: str = DEFAULT_DEV_SECRET
    jwt_expire_minutes: int = 60
    login_max_attempts: int = 5          # failed logins allowed per window (per IP + email)
    login_window_seconds: int = 900
    anthropic_api_key: str = ""          # optional: enables LLM-written career advice
    anthropic_model: str = "claude-sonnet-4-5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # ignore unknown keys in .env

    @property
    def cors_origins(self) -> list[str]:
        """FRONTEND_ORIGIN may hold several comma-separated URLs. In development, localhost and
        127.0.0.1 are both allowed because browsers treat them as different origins."""
        origins = [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]
        if self.environment.lower() != "production":
            for o in list(origins):
                for a, b in (("//localhost", "//127.0.0.1"), ("//127.0.0.1", "//localhost")):
                    if a in o and o.replace(a, b) not in origins:
                        origins.append(o.replace(a, b))
        return origins

    @model_validator(mode="after")
    def require_real_secret_in_production(self):
        """Refuse to start in production with the public default or a short secret."""
        if self.environment.lower() == "production" and (
                self.jwt_secret == DEFAULT_DEV_SECRET or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET must be set to a random string of 32+ characters in production")
        return self


settings = Settings()
