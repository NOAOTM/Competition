from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "真知 Agent API"
    app_env: str = "development"
    secret_key: str
    database_url: str = "sqlite:///./data/zhenzhi_agent.db"
    access_token_expire_minutes: int = 1440
    ollama_provider: str = "ollama"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "deepseek-r1:7b"
    vision_model: str = "qwen2.5vl:7b"
    ollama_num_ctx: int = 8192
    ollama_timeout_seconds: int = 360
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    output_dir: str = "./output"
    upload_dir: str = "./uploads"
    log_dir: str = "./logs"
    pipeline_passes: str = "1,2"
    chunk_size: int = 1800
    chunk_overlap: int = 200
    max_chunks: int = 8
    admin_username: str = ""
    admin_password: str = ""
    chaoxing_cookie: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def llm_provider(self) -> str:
        return self.ollama_provider.lower()

    @property
    def llm_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_model
        return self.ollama_model

    @property
    def llm_base_url(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_base_url
        return self.ollama_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
