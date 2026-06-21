from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Wazuh API
    wazuh_api_url: str = Field(default="https://localhost:55000")
    wazuh_api_user: str = Field(default="wazuh-wui")
    wazuh_api_password: str = Field(default="MyS3cur3P4ssw0rd!")
    wazuh_verify_ssl: bool = Field(default=False)

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")
    ollama_timeout: int = Field(default=120)

    # Agent behavior
    alert_severity_threshold: int = Field(default=7)  # 1-15 Wazuh scale
    max_alerts_per_analysis: int = Field(default=50)
    auto_response_enabled: bool = Field(default=False)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
