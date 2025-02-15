from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict

templates = Jinja2Templates(directory = './templates')




class Settings(BaseSettings):
    """
        Base settings and configuration of all the credentials that are used across the app.
    """
    db_name: str
    db_host: str
    db_port: int 
    db_user: str
    db_password: str

    base_url: str


    password_reset_token_serializer_key: str

    jwt_token_algorithm: str
    jwt_token_expire_minutes: int
    jwt_token_secret_key: str
    
    
    email_server_port: int
    sender_email_id: str
    sender_email_password: str


    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

