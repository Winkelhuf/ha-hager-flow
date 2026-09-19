# Hager flow Modbus Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-blue.svg)](https://www.home-assistant.io/)
[![Python](https://shields.io)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HACS](https://shields.io)](https://hacs.xyz)

A modern, highly optimized Home Assistant custom integration to monitor your **Hager flow Energy Management System (EMS)** locally over Modbus TCP. It features an intelligent strict **Auto-Discovery engine** that automatically maps and dynamically names connected hardware while filtering out offline devices to keep your entities clean.

---

## 📋 Features

- ⚡ **100% Local Control:** Connects directly via Modbus TCP (Port 502) to your system without relying on cloud APIs.
- 📦 **Multi-Hub Support:** Add multiple Hager flow devices with different IP addresses simultaneously without entity conflicts.
- 🧠 **Smart Auto-Discovery (Powermeters):** Scans Slave IDs 30–37 on startup. Dynamically creates entities *only* if a valid text name starting with `EC` (Energy Control) is broadcasted, natively using the device's real name.
- 🚗 **Smart Auto-Discovery (Witty Wallboxes):** Scans Slave IDs 1–7. Dynamically creates up to 12 individual diagnostic and energy sensors *only* if the connection register (`4613`) confirms active presence (`== 1`).
- 🔄 **Real-Time Data Scaling:** Handles complex datatype conversions (`int32`, `uint32`, `int16`) and automatically applies scaling factors (e.g., converting network raw data to real Amperes or kWh).

---

## 📊 Monitored Entities

### Static Main System Sensors (Slave 0 & 1)
*   **EMC PV Gesamtleistung** (Total PV Power in W)
*   **EMC Batterie SOC** (State of Charge in %)
*   **EMC Hausverbrauch Gesamt** (Total Household Consumption in W)
*   **EMC Main Leistung Gesamt** (Total Grid Power in W)
*   **EMC Main Strom L1** (Grid Current Phase 1 in A)

### Dynamic Powermeter Sensors (Slaves 30-37, if detected)
*   **Total Power** (W)
*   **Power L1 / L2 / L3** (Individual Phase Power in W)
*   **Total Charged Energy** (Wh)

### Dynamic Witty Wallbox Sensors (Slaves 1-7, if detected)
*   **Device Info:** Name, Firmware Version, IP Address
*   **Charging Status:** Active session total energy, Grid energy portion, PV energy portion (all in kWh)
*   **Diagnostic Values:** Current Witty Solar Power (W), Session Badge ID, RFID Card ID, Connection state, Boost Mode status

---

## 🚀 Installation

### Option 1: Via HACS (Recommended once public)
1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste your repository URL: `https://github.com`
4. Select **Integration** as the category and click **Add**.
5. Find **Hager flow Modbus** in HACS and click **Download**.
6. **Restart** Home Assistant.

### Option 2: Manual Installation (Private Testing)
1. Download the latest release or clone the repository.
2. Copy the inner `hager_flow` folder from `custom_components/` into your Home Assistant's local `config/custom_components/` directory.
3. Your path should look like this: `/config/custom_components/hager_flow/`
4. **Restart** Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services**.
2. Click the **+ Add Integration** button in the bottom right corner.
3. Search for **"Hager flow"** and select it.
4. Enter the **IP Address** of your local Hager flow system (Default fallback preset: `192.168.70.30`).
5. Click **Submit**. The integration will automatically fire up the discovery engine and populate your dashboard with all your active local hardware!

> [!IMPORTANT]
> Since the integration runs a deep network scanning matrix upon initial load, if you alter physical RS485 connections (adding/removing RTU meters or wallboxes), simply reload the integration or restart Home Assistant to trigger a fresh Auto-Discovery sequence.

---

## 🛠️ Tech Stack & Architecture

This integration utilizes the modern async **DataUpdateCoordinator** design pattern to group register polling into single cohesive block requests every 5 seconds. It is built natively to comply with modern **Pymodbus 3.9+ up to 3.11+ API signatures** running under high-tier environments (Python 3.12 through Python 3.14). 

- All multi-byte data decodings are mapped directly through native client memory conversions (`convert_from_registers`).
- Unique IDs are bound cryptographically via `entry.entry_id` strings preventing cross-talk collisions across multiple installations.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Built with AI

This blueprint was developed with significant assistance from AI coding assistants (GitHub Copilot, Claude). We believe
that community integrations may benefit from extensive AI assistance when their actual review, testing, limitations,
and maturity are communicated honestly. See our [`AI_POLICY.md`](AI_POLICY.md) for the distinction between community
custom integrations and contributions to Home Assistant Core.

The comprehensive AI agent instructions included in this repository ([`AGENTS.md`](AGENTS.md),
`.agents/instructions/`) help humans and agents produce inspectable code using Home Assistant Core patterns and
automated quality checks. These safeguards improve verifiability but do not guarantee correctness.

---

**Happy coding! 🎉** If you build something cool with this blueprint, let us know!
