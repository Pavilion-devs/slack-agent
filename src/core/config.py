"""Configuration management for the Slack Support AI Agent."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Slack Configuration (Optional for testing)
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    slack_signing_secret: Optional[str] = Field(default=None, env="SLACK_SIGNING_SECRET")
    
    # OpenAI Configuration (Optional)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Supabase Configuration (for session management)
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, env="SUPABASE_KEY")
    
    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    
    # Application Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # FastAPI Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Streamlit Configuration
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # RAG System Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    retrieval_k: int = Field(default=5, env="RETRIEVAL_K")
    mmr_fetch_k: int = Field(default=20, env="MMR_FETCH_K")
    mmr_lambda: float = Field(default=0.7, env="MMR_LAMBDA")
    
    # Confidence Thresholds
    soc2_confidence_threshold: float = Field(default=0.75, env="SOC2_CONFIDENCE_THRESHOLD")
    hipaa_confidence_threshold: float = Field(default=0.75, env="HIPAA_CONFIDENCE_THRESHOLD")
    gdpr_confidence_threshold: float = Field(default=0.75, env="GDPR_CONFIDENCE_THRESHOLD")
    iso27001_confidence_threshold: float = Field(default=0.75, env="ISO27001_CONFIDENCE_THRESHOLD")
    general_confidence_threshold: float = Field(default=0.65, env="GENERAL_CONFIDENCE_THRESHOLD")
    
    # Legacy settings for backward compatibility
    confidence_threshold: float = Field(default=0.65, env="CONFIDENCE_THRESHOLD")
    max_response_time: int = Field(default=15, env="MAX_RESPONSE_TIME")  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()