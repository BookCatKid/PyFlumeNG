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

Do-not-alert schedules have complete unprefixed CRUD helpers:

```python
schedules = client.list_do_not_alert_schedules(device_id)
schedule = client.get_do_not_alert_schedule(device_id, schedule_id)
created = client.create_do_not_alert_schedule(device_id, payload)
updated = client.update_do_not_alert_schedule(device_id, schedule_id, payload)
deleted = client.delete_do_not_alert_schedule(device_id, schedule_id)
```

The `*_portal_*` names remain compatibility aliases, but new code does not need
to choose method names based on auth type. Known portal-only writes (usage-alert
rule mutations, do-not-alert schedule mutations, schedule associations, and
shutoff configuration) enforce the `portal_writes` capability before sending a
request, so an accidental `PersonalAuth` write fails locally with
`FlumeCapabilityError`.

## Structured alert history

`client.list_usage_alert_history()` is the typed form of
`GET /users/{user_id}/usage-alerts`. Each `UsageAlert` includes a nested
`UsageAlertQuery` with the stored request ID, bucket, local since/until strings,
and timezone, plus a `duration_minutes` convenience property when the timestamps
are parseable.

## Validated rule payloads

For custom rules, `build_usage_alert_rule_payload()` and the configured
create/update helpers enforce the current portal form: a 1–32 character name,
flow rate from 0 through 40.9 gallons/minute, duration from 5 through 1439
minutes, and repeat notification interval no greater than 20100 minutes. Live
API validation adds one rule the portal form itself does not make obvious:
`notify_every` must be at least **twice the rule duration**. For example,
`duration=60` accepts `notify_every=120` but rejects `119`; the maximum tested
duration `1439` accepts `2878` but rejects `2877`. Violating this live backend
constraint produces HTTP 400 / API code 94 rather than a useful field-level
validation message.

If `notify_every` is omitted for a custom rule, PyFlumeNG now chooses the safe
minimum automatically: `2 * duration`. Passing an explicit smaller value raises
`ValueError` before any request is sent. This avoids the previous default of
zero, which the backend rejects for ordinary custom-rule creation.

The built-in Smart Leak rule is deliberately different. The portal does not
send `name`, `flow_rate`, or `shutoff_config` when editing an
`advanced_low_flow` rule. Use `build_smart_leak_rule_payload()` or
`update_smart_leak_rule_configured()` to avoid sending those fields.

For Do Not Alert schedules,
`build_do_not_alert_schedule_payload()`/the configured CRUD helpers accept
weekdays `SU` through `SA`, normalize times to `HH:mm:ss`, require at least four
minutes between start and end, and constrain weekly interval to 1–10. Empty
`span_types` is omitted exactly like the portal form.

See the [API reference](api-reference.md) for every method and return type.
