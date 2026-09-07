# PyFlumeNG examples

The examples use portal authentication and prompt securely for your Flume
password.

## Manage a usage-alert rule

List every rule with its current state, choose one, and explicitly set it to
`true` (enabled) or `false` (disabled):

```console
python examples/toggle_usage_alert_rule.py --username you@example.com
```

After using the displayed IDs once, the selection can be supplied directly:

```console
python examples/toggle_usage_alert_rule.py \
  --username you@example.com \
  --rule-id 3532380 \
  --state false
```
