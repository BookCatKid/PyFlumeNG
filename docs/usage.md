# FlumeUsageAlertList
## Overview
FlumeUsageAlertList is a Python class designed to retrieve usage alert notifications from the Flume API. This class enables querying of usage alerts from devices owned by the user and provides control over the state of the usage alert list (read or not read).

## Dependencies
 - requests

## Initialization
To initialize the FlumeUsageAlertList object, you'll need the following parameters:

 - `flume_auth`: FlumeAuth object for authentication.
 - `http_session`: (Optional) Requests Session() object.
 - `timeout`: (Optional) Requests timeout for throttling. The default value is specified in DEFAULT_TIMEOUT.
 - `read`: (Optional) State of usage alert list; specifies if they have been read or not read. Default is "false."

## Methods
Usage Alert Retrieval

`get_usage_alerts()`
Method to return all usage alerts from devices owned by the user. This method fetches a JSON list containing the usage alerts.

`get_next_usage_alerts()`
Method to return the next page of usage alerts from devices owned by the user. This method fetches a JSON list containing the usage alerts for the next page.

Raises:
 - `ValueError`: If no next page is available.

`_has_next_page(response_json)`
Returns True if the next page exists. Used internally to handle pagination.

`_get_usage_request(api_url, query_string)`
Makes an API request to get usage alerts from the Flume API.

Usage Alert Rules

`get_usage_alert_rules(device_id)`
Method to return all usage alert rules configured for a device. This corresponds to `GET /users/{user_id}/devices/{device_id}/rules/usage-alerts`.

`get_usage_alert_rule(device_id, rule_id)`
Method to return a single usage alert rule. This corresponds to `GET /users/{user_id}/devices/{device_id}/rules/usage-alerts/{rule_id}`.

`update_usage_alert_rule(device_id, rule_id, payload)`
Method to patch a usage alert rule. This corresponds to `PATCH /users/{user_id}/devices/{device_id}/rules/usage-alerts/{rule_id}`, e.g. `{"active": False}`.

> **Limitation (verified 2026-09-06 against live API):** the Flume
> **Personal API token** (OAuth password/refresh flow, `read:personal`
> scope) returns `404 "The route requested is not defined"` for writes.
> Use `FlumePortalAuth` for rule updates; it runs the same authorization-code
> flow as the customer portal and obtains the required `customer-portal`
> scoped bearer token.

`set_usage_alert_rule_active(device_id, rule_id, active)`
Convenience wrapper around `update_usage_alert_rule` to enable (`True`) or disable (`False`) a rule.

## Example
```python
import pyflume
auth = pyflume.FlumePortalAuth(
    username='your_username',
    password='your_password',
)

usage_alert_list_obj = pyflume.FlumeUsageAlertList(
    flume_auth=auth
)
usage_alert_list = usage_alert_list_obj.get_usage_alerts()
print(usage_alert_list)  # Prints the JSON list of usage alerts
```

For subsequent pages:
```python
if usage_alert_list_obj.has_next:
    next_page_alerts = usage_alert_list_obj.get_next_usage_alerts()
    print(next_page_alerts)  # Prints the JSON list of usage alerts for the next page
```

## Managing usage alert rules (enable / disable)
```python
device_id = "test-device-01"
rule_id = test-rule-01

# List rules / fetch one rule
rules = usage_alert_list_obj.get_usage_alert_rules(device_id)
rule = usage_alert_list_obj.get_usage_alert_rule(device_id, rule_id)

# Disable a rule (equivalent to PATCH {"active": False})
usage_alert_list_obj.set_usage_alert_rule_active(device_id, rule_id, False)

# Re-enable it
usage_alert_list_obj.set_usage_alert_rule_active(device_id, rule_id, True)

# Generic patch (e.g. other rule fields when supported)
usage_alert_list_obj.update_usage_alert_rule(device_id, rule_id, {"active": False})
```
