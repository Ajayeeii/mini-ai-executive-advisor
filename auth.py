
import hashlib
import hmac
import secrets


# PBKDF2 configuration
HASH_NAME = "sha256"
ITERATIONS = 600_000
SALT_SIZE = 16


def hash_password(password):
    """Create a salted PBKDF2 password hash."""

    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    salt = secrets.token_bytes(SALT_SIZE)

    password_hash = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )

    # Store algorithm, iterations, salt, and hash together.
    return (
        f"pbkdf2_{HASH_NAME}$"
        f"{ITERATIONS}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


def verify_password(password, stored_hash):
    """Check a password against its stored hash."""

    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")

        if algorithm != f"pbkdf2_{HASH_NAME}":
            return False

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            HASH_NAME,
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (AttributeError, TypeError, ValueError):
        return False
