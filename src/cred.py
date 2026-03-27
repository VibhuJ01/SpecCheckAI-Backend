import os


class Credentials:
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    directory = os.getenv("DIRECTORY", "")

    mongo_url = os.getenv("MONGO_URL", "")
    db_name = os.getenv("DB_NAME", "")

    auth_key = os.getenv("AUTH_KEY", "")
    redirect_url = os.getenv("REDIRECT_URL", "")
    environment = os.getenv("ENVIRONMENT", "LOCAL")

    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_provider = os.getenv("SMTP_PROVIDER", "")
