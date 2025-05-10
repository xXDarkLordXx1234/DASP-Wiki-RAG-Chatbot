import requests
import jwt
from jwt import PyJWKClient
from rag_retriever_service.src.config.load_config import get_config_value
from rag_retriever_service.src.utils.utils import *
import logging

logger = logging.getLogger(__name__)
JWKS_URL = get_config_value("JWKS_URL", "https://auth.ukp.informatik.tu-darmstadt.de/realms/UKP/protocol/openid-connect/certs")

def fetch_jwks() -> dict:
    """Fetch the JWKS from Keycloak."""
    try:
        response = requests.get(JWKS_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching JWKS: {e}")
        return {}

def verify_token(jwt_token: str) -> dict:
    """Verify a JWT using the public key from JWKS.
    
    Args:
        jwt_token (str): The JWT token.
    
    Returns:
        dict: Decoded payload if successful, or an error dict.
    """
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(jwt_token)
        decoded_payload = jwt.decode(
            jwt_token,
            signing_key.key,
            algorithms=["RS256"],
            audience="account",  # Update to match the actual audience if needed.
            issuer="https://auth.ukp.informatik.tu-darmstadt.de/realms/UKP"
        )
        return decoded_payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError as e:
        return {"error": f"Invalid token: {str(e)}"}

def verify_and_decode_token(received_jwt: str) -> list:
    """Verify a JWT token and return the user groups.
    
    Args:
        received_jwt (str): The received JWT token.
    
    Returns:
        list: A list of user groups if verification is successful; otherwise, an empty list.
    """
    decoded_payload = verify_token(received_jwt)
    if "groups" in decoded_payload:
        groups = decoded_payload['groups']
        return map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(groups)
    else:
        return []