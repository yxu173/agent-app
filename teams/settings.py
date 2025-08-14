from pydantic_settings import BaseSettings


class TeamSettings(BaseSettings):
    """Team settings that can be set using environment variables.

    Reference: https://pydantic-docs.helpmanual.io/usage/settings/
    """

    gpt_4_mini: str = "gpt-4o-mini"
    gpt_4: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    default_max_completion_tokens: int = 16000
    default_temperature: float = 0
    google_api_key: str = "AIzaSyB7BcruqBz7uN1NPYmafiGP3w1h1BriOow"
    openrouter_api_key: str = "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"
    tavily_api_key: str = "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"


# Create an TeamSettings object
team_settings = TeamSettings()
