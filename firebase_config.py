"""
Firebase Configuration Module for Sovereign News Collector

Place your Firebase service account JSON file at:
firebase_service_account.json

You can download this from the Firebase Console:
1. Go to Project Settings > Service Accounts
2. Click "Generate Private Key"
3. Save the JSON file as firebase_service_account.json
"""

import os
from pathlib import Path
from typing import Optional
import json
from google.cloud import firestore
from google.oauth2 import service_account


# Default paths to check for service account
DEFAULT_SERVICE_ACCOUNT_PATHS = [
    "firebase_service_account.json",
    "config/firebase_service_account.json",
    os.path.expanduser("~/.config/firebase_service_account.json"),
]

# Firestore collection name
NEWS_COLLECTION = "news"


def get_service_account_path() -> Optional[str]:
    """
    Find the Firebase service account JSON file.

    Returns:
        Path to service account file if found, None otherwise
    """
    for path in DEFAULT_SERVICE_ACCOUNT_PATHS:
        if Path(path).exists():
            return path

    # Check environment variable
    env_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    return None


def initialize_firestore(service_account_path: Optional[str] = None) -> firestore.Client:
    """
    Initialize Firebase Firestore client.

    Args:
        service_account_path: Path to service account JSON file.
                            If None, will search default locations.

    Returns:
        Firestore client instance

    Raises:
        FileNotFoundError: If service account file not found
        Exception: If Firebase initialization fails
    """
    if service_account_path is None:
        service_account_path = get_service_account_path()

    if service_account_path is None:
        raise FileNotFoundError(
            "Firebase service account JSON file not found.\n"
            "Please place your service account file at one of these locations:\n"
            "  - firebase_service_account.json (in project root)\n"
            "  - config/firebase_service_account.json\n"
            "  - ~/.config/firebase_service_account.json\n"
            "Or set the FIREBASE_SERVICE_ACCOUNT_PATH environment variable.\n"
            "\n"
            "Download your service account key from:\n"
            "Firebase Console > Project Settings > Service Accounts"
        )

    if not Path(service_account_path).exists():
        raise FileNotFoundError(
            f"Service account file not found: {service_account_path}"
        )

    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path
        )
        client = firestore.Client(
            credentials=credentials,
            project=credentials.project_id
        )
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize Firebase Firestore: {e}")


def test_connection(db: firestore.Client) -> bool:
    """
    Test the Firestore connection by attempting a simple query.

    Args:
        db: Firestore client instance

    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Try to fetch one document from the news collection
        docs = db.collection(NEWS_COLLECTION).limit(1).get()
        return True
    except Exception as e:
        print(f"Firestore connection test failed: {e}")
        return False


# Convenience function for easy import
def get_firestore_client() -> firestore.Client:
    """
    Get a Firestore client with automatic configuration detection.

    Returns:
        Initialized Firestore client
    """
    return initialize_firestore()
