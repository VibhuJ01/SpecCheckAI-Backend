from cryptography.fernet import Fernet

print("\n\n[Random Auth Token]:", Fernet.generate_key().decode(), "\n\n")
