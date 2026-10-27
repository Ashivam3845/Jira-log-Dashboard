import json
import os
import sys
from functools import lru_cache
from typing import Any, ClassVar, List, Optional, Tuple, Type

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .logger import logger

ENV = os.getenv("ENV", sys.argv[1] if len(sys.argv) > 1 else "LOCAL")
CURRENT_REGION = os.getenv("AWS_REGION", "us-east-1").lower()
CURRENT_SECRET_MANAGER = os.getenv("AWS_SECRET_NAME")

SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() == "true"

logger.info("Total Arguments length : " + str(len(sys.argv)))
if len(sys.argv) > 3:
    SKIP_AUTH = sys.argv[3].lower() == "true" if isinstance(sys.argv[3], str) else bool(sys.argv[3])
    logger.info("SKIP_AUTH Flag : " + str(sys.argv[3]))


def get_secrets() -> dict:
    """
    Fetch secrets from AWS Secrets Manager.
    Falls back to environment variables in LOCAL mode.
    """
    if ENV == "LOCAL":
        logger.info("[SECRETS] LOCAL mode — loading from environment variables")
        return {
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "APM_TOKEN": os.getenv("APM_TOKEN", ""),
        }

    try:
        import boto3
        secret_name = os.getenv("AWS_SECRET_NAME")
        if not secret_name:
            logger.info("[SECRETS] AWS_SECRET_NAME is not set; using environment variables")
            return {
                "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                "APM_TOKEN": os.getenv("APM_TOKEN", ""),
            }
        client = boto3.client(service_name="secretsmanager", region_name=CURRENT_REGION)

        logger.info(f"[SECRETS] Fetching secrets from: {secret_name}")
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name.lower()
        )

        secret = get_secret_value_response["SecretString"]
        secrets_dict = json.loads(secret)

        logger.info(
            f"[SECRETS] Successfully fetched {len(secrets_dict)} secrets from AWS Secrets Manager"
        )
        return secrets_dict
    except Exception as e:
        logger.warning(f"[SECRETS] Failed to fetch from AWS, falling back to env vars: {e}")
        return {
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "APM_TOKEN": os.getenv("APM_TOKEN", ""),
        }


class SecretsManagerSettingsSource(PydanticBaseSettingsSource):
    """
    Custom settings source that fetches from AWS Secrets Manager.
    """

    def get_field_value(self, field: Any, field_name: str) -> Tuple[Any, str, bool]:
        secrets = get_secrets()
        value = secrets.get(field_name)
        return value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        return get_secrets()


class ConfigLoader(BaseSettings):
    """
    Handles all environment-specific configuration for the Jira Logger service.

    Features:
    - Loads AWS Secrets Manager keys (non-LOCAL)
    - Falls back to env vars in LOCAL mode
    - Per-user credentials stored in SQLite, not here
    """

    PROJECT_NAME: str = "Jira Logger"
    PROJECT_DESCRIPTION: str = "AI-Powered Engineering Activity Tracker"
    PROJECT_VERSION: str = "1.0.0"

    ENV: ClassVar[str] = ENV
    CURRENT_REGION: ClassVar[str] = CURRENT_REGION
    PORT: ClassVar[str] = os.getenv("PORT", sys.argv[2] if len(sys.argv) > 2 else "5302")

    API_PREFIX: str = "/project/jira-logger"
    DEBUG: bool = False

    CORS_ORIGINS: List[str] = ["*"]

    SQLITE_URL: str = "sqlite:///./jira_logger.db"

    TIME_ZONE: str = "Asia/Kolkata"
    CRON_SCHEDULE: str = "0 0 * * *"

    # --- Secrets (from AWS or env) ---
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440  # 24 hours

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    SESSION_TIMEOUT_MINUTES: int = 30

    OPENAI_API_KEY: Optional[str] = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    CHAT_SESSION_TTL_MINUTES: int = 30

    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None

    APM_TOKEN: str = ""
    APM_URL: Optional[str] = None

    SKIP_AUTH: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    def model_post_init(self, __context: Any) -> None:
        self.APM_URL = os.getenv("APM_URL")
        self.SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() == "true"
        if not self.SKIP_AUTH and len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "Set JWT_SECRET_KEY to a unique random value of at least 32 characters"
            )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Define the sources and their order for loading settings.
        """
        return (
            init_settings,
            SecretsManagerSettingsSource(settings_cls),
            dotenv_settings,
            env_settings,
        )


@lru_cache()
def get_settings() -> ConfigLoader:
    return ConfigLoader()


REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379

SESSION_TIMEOUT_MINUTES: int = 30

# ------------------------------------------------------------------------------
# EXPORT CONFIG
# ------------------------------------------------------------------------------
settings = get_settings()
