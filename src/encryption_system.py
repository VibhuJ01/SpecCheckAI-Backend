import json

from cryptography.fernet import Fernet

from src.cred import Credentials


class EncryptionSystem:
    key: bytes
    cipher_suite: Fernet

    def __init__(self):
        self.key = Credentials.auth_key.encode()
        self.cipher_suite = Fernet(self.key)

    def encrypt_dict(self, input_json: dict) -> str:
        """Encrypts input JSON object
        Args:
            input_json (dict): input JSON object
        Returns:
            str: encrypted string
        """
        json_string = json.dumps(input_json)

        encrypted_string = self.cipher_suite.encrypt(json_string.encode())
        return encrypted_string.decode()

    def decrypt_string(self, encrypted_string: str) -> dict:
        """Decrypts input string
        Args:
            encrypted_string (str): encrypted string
        Returns:
            dict: decrypted JSON object
        """
        decrypted_string = self.cipher_suite.decrypt(encrypted_string.encode()).decode()
        return json.loads(decrypted_string)
