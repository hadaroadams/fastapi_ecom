from pydantic_settings import BaseSettings, SettingsConfigDict


class setting(BaseSettings):
    app_name: str = "Ecommerce Api"
    version: str = "0.1.0"
    debug: bool = False
    database_url: str
    model_config = SettingsConfigDict(env_file=".env.local")
    secrete_key: str
    access_token_expire_minutes: int = 30
    paystack_secret_key: str
    paystack_callback_url: str = "http://localhost:3000/payment/callback"


settings = setting()
