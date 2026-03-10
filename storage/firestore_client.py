#!/usr/bin/env python3
"""
Firestore client base class for MENA News Intelligence System.
"""
import os
import logging
from typing import Optional
from google.cloud import firestore
from config import Config

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Base Firestore client with connection management."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize Firestore client.

        Args:
            config: Configuration object (uses global config if not provided)
        """
        self.config = config or Config()
        self._client: Optional[firestore.Client] = None

    @property
    def client(self) -> firestore.Client:
        """Get or create Firestore client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> firestore.Client:
        """Create a new Firestore client.

        Returns:
            Firestore client instance
        """
        # Check for explicit credentials path
        creds_path = self.config.firestore.credentials_path

        if creds_path and os.path.exists(creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(creds_path)
            logger.info(f"Using credentials from: {creds_path}")

        try:
            client = firestore.Client(project=self.config.firestore.project_id)
            logger.info(f"Connected to Firestore project: {self.config.firestore.project_id}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
            raise

    def collection(self, name: str):
        """Get a collection reference.

        Args:
            name: Collection name

        Returns:
            Firestore collection reference
        """
        return self.client.collection(name)
