#!/usr/bin/env python3
"""List Flume usage-alert rules and explicitly enable or disable one."""

import argparse
from getpass import getpass

import pyflumeng


def _state_label(active: bool) -> str:
    """Return a readable fixed-width rule state."""
    return "ENABLED " if active else "DISABLED"


def main() -> None:
    """Select and update one usage-alert rule through the portal API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    parser.add_argument("--rule-id")
    parser.add_argument("--state", choices=("true", "false"))
    args = parser.parse_args()

    username = args.username or input("Flume email: ").strip()
    password = getpass("Flume password: ")
    client = pyflumeng.FlumeClient(
        pyflumeng.PortalAuth(username=username, password=password)
    )

    rules = []
    for device in client.list_portal_devices():
        for rule in client.list_portal_usage_alert_rules(str(device.id)):
            rules.append((device, rule))

    if not rules:
        raise SystemExit("No usage alert rules found")

    number_width = len(str(len(rules)))
    name_width = max(len(rule.name or "Unnamed rule") for _, rule in rules)
    print("\nUsage-alert rules\n")
    print(f"{'#':>{number_width}}  {'STATE':<8}  {'NAME':<{name_width}}  DEVICE / RULE")
    print(f"{'-' * number_width}  {'-' * 8}  {'-' * name_width}  {'-' * 24}")
    for number, (device, rule) in enumerate(rules, start=1):
        name = rule.name or "Unnamed rule"
        print(
            f"{number:>{number_width}}  {_state_label(rule.active)}  "
            f"{name:<{name_width}}  {device.id} / {rule.id}"
        )

    if args.rule_id is not None:
        selected = next(
            ((device, rule) for device, rule in rules if str(rule.id) == args.rule_id),
            None,
        )
        if selected is None:
            raise SystemExit(f"Rule {args.rule_id!r} was not found")
        device, rule = selected
    else:
        try:
            choice = int(input(f"\nSelect a rule [1-{len(rules)}]: "))
            if not 1 <= choice <= len(rules):
                raise ValueError
            device, rule = rules[choice - 1]
        except (ValueError, IndexError):
            raise SystemExit("Invalid rule number") from None

    if args.state is None:
        print("\nSet the active state:")
        print("  1. true  (enabled)")
        print("  2. false (disabled)")
        state_choice = input("Choose [1-2]: ").strip().lower()
    else:
        state_choice = args.state
    if state_choice in ("1", "true"):
        state = True
    elif state_choice in ("2", "false"):
        state = False
    else:
        raise SystemExit("Invalid state; enter 1/true or 2/false")

    name = rule.name or "Unnamed rule"
    print(f"\nSetting {name!r} to {_state_label(state).strip()}...")
    print(
        client.set_portal_usage_alert_rule_active(
            str(device.id),
            str(rule.id),
            state,
        )
    )
    print(f"Done. {name!r} is now {_state_label(state).strip()}.")


if __name__ == "__main__":
    main()
