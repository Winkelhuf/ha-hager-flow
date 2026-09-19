"""Constants for ha_integration_domain."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hager_flow"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"

DEFAULT_UPDATE_INTERVAL_HOURS = 1.0
