# Privacy Policy for OctoPrint Plugin: OctoHeat

**Last updated:** 2026-07-10

## Overview

OctoHeat is an OctoPrint plugin that controls a heater via a Home Assistant instance based on temperature sensor readings. This privacy policy explains how the plugin handles data.

## Data Collection

OctoHeat does **not** collect, transmit, or store any data externally. There is no analytics, telemetry, or tracking of any kind.

## Data Flow

OctoHeat communicates exclusively with **your own Home Assistant instance** over your local network (or a URL you configure). Specifically:

- **Reads** temperature sensor state from Home Assistant
- **Controls** a heater switch in Home Assistant (turn on/off)

All communication is between your OctoPrint server and your Home Assistant instance. No data leaves your local network unless you configure an external Home Assistant URL.

## Data Stored Locally

OctoHeat stores the following settings locally in OctoPrint's configuration (`config.yaml`):

- Home Assistant URL
- Home Assistant long-lived access token
- Sensor and switch entity IDs
- Temperature and control preferences

These values never leave your system.

## Third-Party Services

OctoHeat does not connect to any third-party services, cloud providers, or external APIs beyond the Home Assistant instance you configure.

## Security

- The plugin communicates with Home Assistant using your provided long-lived access token over HTTP/HTTPS.
- Users are encouraged to use HTTPS for their Home Assistant instance when accessible over the internet.

## Changes to This Policy

Any changes to this policy will be reflected in the plugin repository with an updated date.
