# Usage alerts and rules

`FlumeUsageAlertList` keeps the original usage-alert helper and returns typed
`UsageAlert` and `UsageAlertRule` models. Its first-page/next-page behavior is
preserved for compatibility.

Both auth modes can read usage alerts and usage-alert rules. This example uses
`PortalAuth` because the following write example needs it; you do not need
PortalAuth merely to call `get_usage_alerts()` or `get_usage_alert_rules()`.

```python
import pyflumeng

auth = pyflumeng.PortalAuth(
    username="your_email",
    password="your_password",
)
usage = pyflumeng.FlumeUsageAlertList(auth)
alerts = usage.get_usage_alerts()
rules = usage.get_usage_alert_rules("device-id")
```

The equivalent read-only setup with `PersonalAuth` is also valid:

```python
auth = pyflumeng.PersonalAuth(
    username="your_email",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
usage = pyflumeng.FlumeUsageAlertList(auth)
rules = usage.get_usage_alert_rules("device-id")
```

## Writing rules

Rule writes are where the auth distinction matters. Flume's Personal API token
can read these resources, but it does not have the broader scope required by
the customer-portal write route. Use `PortalAuth` when creating, patching,
enabling/disabling, or deleting rules through that surface.

```python
usage.set_usage_alert_rule_active("device-id", "rule-id", False)
usage.set_usage_alert_rule_active("device-id", "rule-id", True)
```

With `FlumeClient`, the portal write methods explicitly check the
`portal_writes` capability. Passing `PersonalAuth` to methods such as
`update_portal_usage_alert_rule()` or
`set_portal_usage_alert_rule_active()` raises `FlumeCapabilityError` before a
request is sent.

## Schedules and related portal operations

`FlumeClient` exposes the broader portal surface: event rules, usage-alert rule
CRUD, do-not-alert schedules, rule/schedule association, and shutoff
configuration. `UsageAlertRule.schedules` is modeled as
`list[UsageAlertSchedule]` and serializes back through `to_dict()`. The nested
schedule association returned on a rule is a compact object with
`schedule_id`, `active`, `name`, and `description`; it is different from the
full `DoNotAlertSchedule` resource returned by the do-not-alert schedule
endpoint.

See the [API reference](api-reference.md) for every method and return type.
