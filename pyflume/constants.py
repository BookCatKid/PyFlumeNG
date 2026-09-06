"""Constants to support PyFlume."""

# Time-related constants
API_LIMIT = 60
DEFAULT_TIMEOUT = 30

# Operation constants
CONST_OPERATION = "SUM"
CONST_UNIT_OF_MEASUREMENT = "GALLONS"

# Base URL
API_BASE_URL = "https://api.flumetech.com"

# Endpoints
URL_OAUTH_TOKEN = f"{API_BASE_URL}/oauth/token"
API_QUERY_URL = f"{API_BASE_URL}/users/{{user_id}}/devices/{{device_id}}/query"
API_DEVICES_URL = f"{API_BASE_URL}/users/{{user_id}}/devices"
API_NOTIFICATIONS_URL = f"{API_BASE_URL}/users/{{user_id}}/notifications"
API_LEAK_URL = f"{API_BASE_URL}/users/{{user_id}}/devices/{{device_id}}/leaks/active"
API_USAGE_URL = f"{API_BASE_URL}/users/{{user_id}}/usage-alerts"
API_USAGE_RULES_URL = (
    f"{API_BASE_URL}/users/{{user_id}}/devices/{{device_id}}/rules/usage-alerts"
)
API_USAGE_RULE_URL = f"{API_BASE_URL}/users/{{user_id}}/devices/{{device_id}}/rules/usage-alerts/{{rule_id}}"

# Portal API (same backend, portal OAuth client + login flow)
PORTAL_API_URL = "https://api.flumewater.com"
PORTAL_OAUTH_AUTHORIZE_URL = f"{PORTAL_API_URL}/oauth/authorize"
PORTAL_OAUTH_TOKEN_URL = f"{PORTAL_API_URL}/oauth/token"
PORTAL_CLIENT_ID = "customer-portal"
PORTAL_REDIRECT_URI = "https://portal.flumewater.com"
