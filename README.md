# Hager flow Modbus Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-blue.svg)](https://www.home-assistant.io/)
[![Python](https://shields.io)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modern, highly optimized Home Assistant custom integration to monitor and control your **Hager flow Energy Management System (EMS / EMC R3)** locally over Modbus TCP. It features a strict **Auto-Discovery engine** that automatically maps and dynamically names connected hardware while filtering out offline devices to keep your entities clean.

---

## 📋 Features

- ⚡ **100% Local Control:** Connects directly via Modbus TCP (Port 502) to your system without relying on cloud APIs.
- 📦 **Multi-Hub Support:** Add multiple Hager flow devices with different IP addresses simultaneously without entity conflicts.
- 🧠 **Smart Auto-Discovery (Powermeters):** Scans Slave IDs 30–37 on startup. Dynamically creates entities *only* if a valid text name starting with `EC` (Energy Control) is broadcasted, natively using the device's real name.
- 🚗 **Smart Auto-Discovery (Witty Wallboxes):** Scans Slave IDs 1–7. Dynamically creates diagnostic, energy sensors, and control switches *only* if the connection register (`4613`) confirms active presence (`== 1`).
- 🔄 **Smart Auto-Discovery (SG Ready):** Scans Slave IDs 50–59. Automatically registers heat pumps or thermal systems if a name is broadcasted on register `4098`.
- 🗂️ **Advanced Device Grouping:** Entities no longer land under "Unassigned". The core EMC controller, each Powermeter, each Witty Wallbox, and each SG Ready interface are mapped into **individual devices** with native branding logos.
- 🔠 **Enum Text Mapping:** Cryptic Modbus numbers (like SG Ready states `1-4`, Meter Types `0-8`, or Power Priorities) are dynamically translated into clear, human-readable text.

---

## 📊 Monitored & Controlled Entities

### 🏠 Static Main System Sensors (Slave 0)
*   **EMC PV Leistung Gesamt** (Total PV Power in W)
*   **EMC Batterie SOC** (State of Charge in % without floating decimals)
*   **EMC Hausverbrauch Gesamt** (Total Household Consumption in W)
*   **Hausanschluss Leistung** (Total Grid Power in W)
*   **Battery Power** (Battery Charge/Discharge in W)
*   **EMC Autarkie / Eigenverbrauch** (Hourly statistics in %)
*   **Ladepriorität** (Text State: *Auto zuerst* / *Batterie zuerst*)
*   **Batterieentladung ins Auto** (Text State: *Erlaubt* / *Verboten*)
*   **Device Info:** System Serial Number, Mainboard Firmware Version

### ⏱️ Dynamic Powermeter Sensors (Slaves 30-37, if detected)
*   **Total Power** (W)
*   **Power L1 / L2 / L3** (Individual Phase Power in W)
*   **Meter Typ** (Text translation: *Hauptzähler (Root)*, *Zusatzverbraucher*, *Zusatzerzeugung*, *Wallbox*, etc.)

### 🔌 Dynamic Witty Wallbox Sensors & Controls (Slaves 1-7, if detected)
*   **Device Info:** Name, Firmware Version, IP Address
*   **Charging Status:** Active session total energy, Grid energy portion, PV energy portion (all in kWh)
*   **Diagnostic Values:** Current Witty Solar Power (W), Session Badge ID, RFID Card ID, Connection state
*   **🚀 Witty Boostmodus Schalter:** Active writeable control switch (*On* = Full power / *Off* = Eco/Solar mode)

### 🌡️ Dynamic SG Ready Sensors (Slaves 50-59, if detected)
*   **SG Ready Status** (Text translation: *Blockiert*, *Normalbetrieb*, *Anlaufempfehlung*, *Anlaufbefehl*)

---

## ⚠️ Important Information: Wallbox Boost Mode Sync & Cloud Latency

When toggling the **Witty Boost Mode Switch**, the underlying Modbus backend writes directly to register `4631`. However, Hager's internal state machine processing and cloud synchronization logic cause a **significant feedback delay** (up to 20 seconds) before the register reflects the updated value.

To prevent rapid toggle-looping (where the switch jumps back and forth while waiting for the cloud) and to eliminate UI accidental double-clicks, this integration implements a **30-second Clouzd-Latency Cooldown Filter**:

1. **Immediate Reaction:** Toggling the switch flips the UI immediately to your desired target state.
2. **UI Lockout:** The switch instantly turns grey (**Disabled**) for **exactly 30 seconds**.
3. **Background Processing:** Pymodbus pushes the command and gives the hardware ample time to process the state change.
4. **Re-Arming:** After 30 seconds, the lockout releases, the switch becomes colorful/clickable again, and normal real-time Modbus polling resumes.

---

## 🚀 Installation

### Option 1: Manual Installation (Private Testing)
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
5. Click **Submit**. The integration will automatically fire up the discovery engine and populate your dashboard with all your active local hardware grouped cleanly into distinct devices with beautiful integrated brand logos!

> [!TIP]
> Since the integration runs a deep network scanning matrix upon initial load, if you alter physical RS485 connections (adding/removing RTU meters or wallboxes), simply reload the integration or restart Home Assistant to trigger a fresh Auto-Discovery sequence.

---

## 🛠️ Tech Stack & Architecture

This integration utilizes the modern async **DataUpdateCoordinator** design pattern to group register polling into single cohesive block requests every 5 seconds. It is built natively to comply with modern **Pymodbus 3.9+ up to 3.11+ API signatures** running under high-tier environments (Python 3.12 through Python 3.14). 

- All multi-byte data decodings are mapped directly through native client memory conversions (`convert_from_registers`).
- Unique IDs are bound cryptographically via `entry.entry_id` strings preventing cross-talk collisions across multiple installations.
- Brand assets are stored natively in the `/brand` subdirectory conforming to modern local rendering specifications without pulling external tracking pixels.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Built with AI

This blueprint was developed with significant assistance from AI coding assistants (GitHub Copilot, Claude). We believe that community integrations may benefit from extensive AI assistance when their actual review, testing, limitations, and maturity are communicated honestly. See our [`AI_POLICY.md`](AI_POLICY.md) for the distinction between community custom integrations and contributions to Home Assistant Core.

The comprehensive AI agent instructions included in this repository ([`AGENTS.md`](AGENTS.md), `.agents/instructions/`) help humans and agents produce inspectable code using Home Assistant Core patterns and automated quality checks. These safeguards improve verifiability but do not guarantee correctness.

---

**Happy coding! 🎉** If you build something cool with this blueprint, let us know!
