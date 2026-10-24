import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash


load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from the .env file."
    )

#Uses HS256 to sign the JWT 
ALGORITHM = "HS256"
TOKEN_EXPIRY_MINUTES = 30

password_hasher = PasswordHash.recommended()


def hash_password(password):
    """
    Converts a password into a secure Argon2 hash.
    The original password cannot be recovered from the hash.
    """
    return password_hasher.hash(password)


def verify_password(plain_password, stored_hash):
    """
    Checks whether the entered password matches the stored hash.
    """
    return password_hasher.verify(
        plain_password,
        stored_hash
    )


def create_access_token(username):
    """
    Creates a signed JWT identifying the logged-in user.
    """
    expiry_time = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRY_MINUTES
    )

    token_data = {
        "sub": username,
        "exp": expiry_time
    }
    #Signs the jwt with HS256
    return jwt.encode(
        token_data,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token):
    """
    Verifies the JWT and returns the username inside it.

    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload.get("sub")

    except InvalidTokenError:
        return None