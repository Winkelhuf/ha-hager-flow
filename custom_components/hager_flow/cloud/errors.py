"""Fehlerklassen des Cloud-Zugangs."""
from __future__ import annotations


class HagerCloudError(Exception):
    """Allgemeiner Fehler der Hager flow Cloud."""


class HagerCloudConnectionError(HagerCloudError):
    """Cloud nicht erreichbar."""


class HagerCloudAuthError(HagerCloudError):
    """Anmeldung abgelehnt oder Token ungültig."""
