import re
import base64
import logging # For internal logging of the decryption script itself
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- Configuration ---
# For decrypting your ORIGINAL log file, you MUST put your actual private key here.
# This is the private key that corresponds to the public key used in the original Fo76Bot script.
PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC+DFK8MnaA437a
vGnIIrXjL3EOIVhegs3EmpyzVbiiDEEF0WXCd0CrXemEh34cI9Nk9QezIXHWh+l8
/Dco+S4plTXjRVskbnGuLnhRQ2juk7gRAqO18U3iIUKItaIbzU/zcjnb5ymoY4nV
LOcIzyCq6GE8bkiI6fe+EgDzldp0tnIyj3bx2JOjXYCaNHMMtNixW8BL8XxvwZNo
GKbXy/iJ0fPfdBq/giDPHJLlPkNOYLrOhFGDBfNmu75hXR2o5n16fYokh4mal4m3
aT8SEM/GYiQQ1ZJskBx59GyRLYKtnPC/fTWb15okohPXVLl8or5Z0vm3TjDI2TLZ
fAed8AFdAgMBAAECggEAHXiGE0a/XKuqk3CYoMn31bPuKV2fZAHkYc1YvnCXvJKq
Ofo8+E6LhJIqxlFH4O+R9lEPBsa0GKtOgwIOQGLVDJVlsV7NzD+k46NeJ2U3g5j8
TVr7mG5ugEIIchsPI+uPLzZykCNv23vFYdLgPYaieg5QwdEXm2+uFNdFjCsb9hwY
S0kWqOet7ykOdQhBA1Q3yJjrVeQZThbOLUK26YUziLSIs1+5y3nMDoh0A0/99fn+
Se2z+Ash5cYo44Armz/atfvnoOvCKhQqb/T6moaGhPdAGjlgd/k4O6Jo+37e+Kbz
BPfGbFf/berY1qcmiRzen8HhMarV3HtOLWdAR/pguwKBgQD+gP7rvyj6qByu6SJF
ED5cjjrmWckJx+kbhM/hDpNlp9UkM4LPvBqhPWekn4Nup/nLRhyTIUMftBkJsItJ
BmE/81Q2peR+2fi87Fz1hX8guQUiru6QvzE+sK5naKbsfEfZWmbCX/GQGqXcsd0q
MEMUvknqwkZ3aq91azO6A7UcywKBgQC/KlPd9ZZ91+y5X3RxqjqhjHveOpFbyoiM
ASMPH93vaVsf0dE7Az8jooEBRXtjLMHjsyTp2EwwRMB9GvWuceR62SjoXeJyZEQe
0huCQnp1KGXVLMggmw+sOHQfe+qISHvc05AXIOsHP9An+laPf1bbXv3V4lwM7miL
+lgHj4H9dwKBgHHKTzAsmi/oNlrmFdJ3Psq3NRKFFmPvJASPzzo7ACA1eBDljxk+
a1GoWMy8HVG+fOsr/96wwohMR92TN9OArL6hFwgQCCfHYXVm4PFNrNd+ohMtz7Cc
K3JyIKhPnEKkFqPRzZwetazOnVYdmFsilPuTUQ1Lq6H861I+ijQjMDkdAoGBAIXz
QOUMyzDO9l9GVa+32nGMoNctLuGk311LBqf4amjx6Bo5yWSSd9GecsrTRwxNNmc5
Biqdl3VTF5YSKAjeYXz7YcDA2IXTYDBAhWoW7vvdHM3tHSZLwQWqYSQWjlaEg9ZO
oG60cDuaKV95+OGAFvqMa01N2bZt7+/1sW1Kz4ktAoGAZAq3VRCx48iQ+inNvEAw
u4ZB8M+W4BZys+eDk80dGIv4F0UZLP0t43SiMG9uF6Xupy36C3039hSacSe+0nxe
t1g+z+OY5V5rqGoLSC7yUM2lUO2/f9O4p4IYxyDOk6MU0kIykXdEvImL89vAmNlL
8ZRUZ6ScOkZgxmbY3VCQrfU=
-----END PRIVATE KEY-----
"""

# --- Constants based on your encryption script ---
# RSA key size determines the length of the encrypted AES key.
# Assuming 2048-bit RSA key as it's common and matches your public key structure.
# If your key is different (e.g., 4096), adjust this.
RSA_KEY_SIZE_BITS = 2048
ENCRYPTED_AES_KEY_LEN = RSA_KEY_SIZE_BITS // 8  # e.g., 2048 / 8 = 256 bytes
AES_IV_SIZE = 12  # GCM standard
AES_TAG_SIZE = 16 # GCM standard, typically 16 bytes for AES-128/256

# Setup a simple logger for the decryption script itself
decryption_logger = logging.getLogger("LogDecryptor")
decryption_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
decryption_logger.addHandler(handler)


def load_private_key_from_string(pem_string):
    """Loads an RSA private key from a PEM string."""
    if "PASTE YOUR ACTUAL RSA PRIVATE KEY HERE" in pem_string or \
       "CONTENT OF new_test_private_key.pem" in pem_string: # Check for placeholder
        decryption_logger.error("Placeholder private key detected. Please replace it with the actual private key.")
        return None
    try:
        private_key = serialization.load_pem_private_key(
            pem_string.encode('utf-8'),
            password=None, # Assuming no password if not specified in generation
            backend=default_backend()
        )
        # Validate key size if possible (optional, but good for consistency)
        if private_key.key_size != RSA_KEY_SIZE_BITS:
            decryption_logger.warning(
                f"Loaded private key size ({private_key.key_size} bits) "
                f"does not match expected RSA_KEY_SIZE_BITS ({RSA_KEY_SIZE_BITS} bits). "
                "This might cause issues if ENCRYPTED_AES_KEY_LEN is incorrect."
            )
        return private_key
    except Exception as e:
        decryption_logger.error(f"Error loading private key: {e}", exc_info=True)
        return None

def decrypt_message_hybrid(encrypted_b64_message, private_key):
    """Decrypts a message encrypted with the hybrid scheme."""
    try:
        # 1. Base64 Decode
        concatenated_bytes = base64.b64decode(encrypted_b64_message)

        # 2. Deconstruct the concatenated bytes
        # Order: Encrypted AES Key + IV + GCM Tag + Ciphertext
        
        offset = 0
        encrypted_aes_key = concatenated_bytes[offset : offset + ENCRYPTED_AES_KEY_LEN]
        offset += ENCRYPTED_AES_KEY_LEN
        
        iv = concatenated_bytes[offset : offset + AES_IV_SIZE]
        offset += AES_IV_SIZE
        
        tag = concatenated_bytes[offset : offset + AES_TAG_SIZE]
        offset += AES_TAG_SIZE
        
        ciphertext = concatenated_bytes[offset:]

        if len(iv) != AES_IV_SIZE:
            raise ValueError(f"Extracted IV length {len(iv)} does not match expected {AES_IV_SIZE}")
        if len(tag) != AES_TAG_SIZE:
            raise ValueError(f"Extracted GCM tag length {len(tag)} does not match expected {AES_TAG_SIZE}")

        # 3. Decrypt the AES key using RSA private key
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 4. Decrypt the message using AES-GCM
        cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_message_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 5. Decode from UTF-8
        return decrypted_message_bytes.decode('utf-8')

    except ValueError as ve: # Handles incorrect padding, tag mismatch, etc.
        decryption_logger.error(f"Decryption ValueError (likely bad key, data corruption, or incorrect deconstruction): {ve}")
        return f"[DECRYPTION_VALUE_ERROR: {ve}]"
    except Exception as e:
        decryption_logger.error(f"General decryption failed: {e}", exc_info=False) # Set exc_info=True for more detail
        return f"[DECRYPTION_FAILED: {e}]"


def decrypt_log_file(log_filepath, output_filepath, private_key_pem):
    """Reads an encrypted log file, decrypts it, and writes to an output file."""
    private_key = load_private_key_from_string(private_key_pem)
    if not private_key:
        decryption_logger.error("Cannot proceed without a valid private key.")
        return

    decryption_logger.info(f"Attempting to decrypt '{log_filepath}' using the provided private key.")
    decryption_logger.info(f"RSA Key Size used for deconstruction: {private_key.key_size} bits.")
    decryption_logger.info(f"Expected encrypted AES key length: {ENCRYPTED_AES_KEY_LEN} bytes.")
    decryption_logger.info(f"Expected IV length: {AES_IV_SIZE} bytes.")
    decryption_logger.info(f"Expected GCM tag length: {AES_TAG_SIZE} bytes.")


    # Regex to find the [ENCRYPTED] part
    # It captures the timestamp, level, module.func:line, and the encrypted message
    log_pattern = re.compile(
        r"^(?P<timestamp>[\d\- :,\.]+?) - "
        r"(?P<loggername>Fo76Bot) - "
        r"(?P<level>ERROR|INFO|WARNING|DEBUG|CRITICAL) - "
        r"(?P<modulefunc>[\w\.]+\:\d+) - "
        r"\[ENCRYPTED\](?P<encrypted_data>.+)$"
    )
    # Simpler pattern for lines that might not be fully encrypted or are just plain
    plain_line_pattern = re.compile(
        r"^(?P<timestamp>[\d\- :,\.]+?) - "
        r"(?P<loggername>Fo76Bot) - "
        r"(?P<level>ERROR|INFO|WARNING|DEBUG|CRITICAL) - "
        r"(?P<modulefunc>[\w\.]+\:\d+) - "
        r"(?P<message>.+)$"
    )


    try:
        with open(log_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:
            
            line_num = 0
            for line in infile:
                line_num += 1
                line = line.strip()
                if not line:
                    outfile.write("\n")
                    continue

                match = log_pattern.match(line)
                if match:
                    parts = match.groupdict()
                    encrypted_b64 = parts['encrypted_data']
                    
                    decrypted_message = decrypt_message_hybrid(encrypted_b64, private_key)
                    
                    outfile.write(
                        f"{parts['timestamp']} - {parts['loggername']} - {parts['level']} - "
                        f"{parts['modulefunc']} - {decrypted_message}\n"
                    )
                else:
                    # If it's not an [ENCRYPTED] line, try to parse it as a plain line or write as is
                    plain_match = plain_line_pattern.match(line)
                    if plain_match:
                         parts = plain_match.groupdict()
                         # Check if the message part itself indicates a previous encryption failure
                         if parts['message'].startswith("[ENCRYPTION_FAILED]"):
                             outfile.write(f"{line} (Original encryption failure)\n")
                         else:
                             outfile.write(f"{line} (Not an [ENCRYPTED] line or malformed)\n")
                    else:
                        outfile.write(f"{line} (Unrecognized format)\n")
                        
        decryption_logger.info(f"Decryption complete. Output written to '{output_filepath}'")

    except FileNotFoundError:
        decryption_logger.error(f"Log file not found: {log_filepath}")
    except Exception as e:
        decryption_logger.error(f"An error occurred during log file processing: {e}", exc_info=True)


if __name__ == "__main__":
    decrypt_log_file('fo76bot.log', 'fo76decrypt.log', PRIVATE_KEY_PEM)