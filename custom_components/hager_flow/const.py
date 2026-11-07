"""Constants for the Hager flow integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hager_flow"
VERSION = "0.3.0"

# Optionaler Cloud-Zugang (Optionen der Integration)
CONF_CLOUD_ENABLED = "cloud_enabled"
CONF_CLOUD_EMAIL = "cloud_email"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_INSTALLATION = "cloud_installation"
# Tokens liegen in entry.data, damit eine Erneuerung keinen Reload auslöst
CONF_CLOUD_ACCESS_TOKEN = "cloud_access_token"
CONF_CLOUD_REAUTH_TOKEN = "cloud_reauth_token"
