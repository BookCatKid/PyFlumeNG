#!/usr/bin/env python3
"""Interactively test Flume usage alert rule toggling through PyFlumeNG."""

import argparse
from getpass import getpass

import pyflume


def main() -> None:
    """Select and toggle one usage-alert rule through the portal API."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    args = parser.parse_args()

    username = args.username or input("Flume email: ").strip()
    password = getpass("Flume password: ")
    client = pyflume.FlumeClient(
        pyflume.PortalAuth(username=username, password=password)
    )

    rules = []
    print("Usage alert rules:")
    for device in client.list_portal_devices():
        for rule in client.list_portal_usage_alert_rules(str(device.id)):
            rules.append((device, rule))
            print(
                f"[{len(rules)}] {rule.name!r} "
                f"device={device.id} rule={rule.id} active={rule.active}"
            )

    if not rules:
        raise SystemExit("No usage alert rules found")

    try:
        choice = int(input("\nSelect rule number: "))
        if not 1 <= choice <= len(rules):
            raise ValueError
        device, rule = rules[choice - 1]
    except (ValueError, IndexError):
        raise SystemExit("Invalid rule number") from None

    state = input("Enable this rule? [y/N]: ").strip().lower() in ("y", "yes")
    print(f"Setting {rule.name!r} active={state}")
    print(
        client.set_portal_usage_alert_rule_active(
            str(device.id),
            str(rule.id),
            state,
        )
    )


if __name__ == "__main__":
    main()
