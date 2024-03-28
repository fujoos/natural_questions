
import base64
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes


def encrypt_to_base64(data, encrypt_key):
    iv = get_random_bytes(AES.block_size)  # Generate a random IV
    cipher = AES.new(encrypt_key, AES.MODE_CBC, iv)  # Initialize the cipher
    encrypted_data = cipher.encrypt(pad(data.encode(), AES.block_size))  # Encrypt and pad the data
    return base64.b64encode(iv + encrypted_data).decode('utf-8')  # Return Base64-encoded IV + encrypted data


key = get_random_bytes(32)  # Generate a 32-byte key for AES-256

# Replace these with your actual Kaggle username and key
kaggle_username = ""
kaggle_key = ""

# Encrypt the Kaggle username and key
encrypted_kaggle_username = encrypt_to_base64(kaggle_username, key)
encrypted_kaggle_key = encrypt_to_base64(kaggle_key, key)

# Optionally, encrypt the encryption key itself if you need to store it
encrypted_key = base64.b64encode(key).decode('utf-8')  # You might choose not to encrypt the key itself but to encode it

# Set the encrypted data as environment variables
os.environ['ENCRYPTED_KAGGLE_USERNAME'] = encrypted_kaggle_username
os.environ['ENCRYPTED_KAGGLE_KEY'] = encrypted_kaggle_key
os.environ['ENCRYPTED_KEY'] = encrypted_key
os.environ['KAGGLE_DATASET_PATH'] = 'frankossai/natural-questions-dataset'
print('successfully saved the environment variables')

# Retrieve the saved environment variables
saved_kaggle_username = os.environ.get('ENCRYPTED_KAGGLE_USERNAME')
saved_kaggle_key = os.environ.get('ENCRYPTED_KAGGLE_KEY')
saved_encryption_key = os.environ.get('ENCRYPTED_KEY')
saved_dataset_path = os.environ.get('KAGGLE_DATASET_PATH')

# Print the retrieved environment variables
print('Retrieved environment variables:')
print(f'ENCRYPTED_KAGGLE_USERNAME: {saved_kaggle_username}')
print(f'ENCRYPTED_KAGGLE_KEY: {saved_kaggle_key}')
print(f'ENCRYPTED_KEY: {saved_encryption_key}')
print(f'KAGGLE_DATASET_PATH: {saved_dataset_path}')
