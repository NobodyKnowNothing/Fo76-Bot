# generate_keys.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend # Good practice to specify backend

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,  # 2048-bit is a good minimum
    backend=default_backend() # Specify backend
)

# Generate public key
public_key = private_key.public_key()

# Serialize private key to PEM format
pem_private_key = private_key.private_bytes( # Corrected method name
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()  # For simplicity, no passphrase. For production, consider one.
)

with open('private_key.pem', 'wb') as f:
    f.write(pem_private_key)
print("Private key saved to private_key.pem")

# Serialize public key to PEM format
pem_public_key = public_key.public_bytes( # Corrected method name
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('public_key.pem', 'wb') as f:
    f.write(pem_public_key)
print("Public key saved to public_key.pem")

print("\nIMPORTANT: Keep private_key.pem extremely secure and confidential!")
print("Distribute public_key.pem to the application that needs to encrypt logs (or hardcode its content).")