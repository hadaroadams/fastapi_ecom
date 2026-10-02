from pydantic_settings import BaseSettings, SettingsConfigDict


class setting(BaseSettings):
    app_name: str = "Ecommerce Api"
    version: str = "0.1.0"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

    print("hello")


settings = setting()
