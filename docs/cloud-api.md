# Hager flow Cloud-API (inoffiziell)

Diese Integration liest alles lokal per **Modbus TCP**. Einige Einstellungen sind per
Modbus aber nicht beschreibbar. Dafür gibt es den **optionalen Cloud-Zugang**, der die
gleiche (undokumentierte) API nutzt wie das Webportal <https://flow.hager.com>.

> ⚠️ Inoffiziell: Hager/E3DC kann die API jederzeit ändern. Die Cloud-Funktionen sind
> deshalb standardmäßig **aus** und werden nur für Schreibbefehle genutzt.
> Die offizielle *Hager Energy API* (<https://developer.hagerenergy.com>) bietet diese
> Schreibfunktionen derzeit (noch) nicht an.

Mitgeschnitten am 07.11.2026 im Webportal (Anlage mit EMC, Speicher und einer Witty-Wallbox).

## Anmeldung

| Schritt | Request |
|---|---|
| Login | myHager-Login (`login.hager.com`, SAML) über `https://e3dc.e3dc.com/auth-saml/service-providers/hager/login?app=hager`; am Ende stehen `token` und `reAuthToken` in der Redirect-URL |
| Token erneuern | `POST https://e3dc.e3dc.com/auth-saml/re-auth` mit `{"reAuthToken": "…"}` → `{"token", "reAuthToken"}` |
| Aufrufe | Header `Authorization: Bearer <token>` |

Der Login-Ablauf ist aus [hebrru/Hager-local](https://github.com/hebrru/Hager-local) (MIT) übernommen.

## Lesen

| Request | Inhalt |
|---|---|
| `GET https://installations.e3dc.com/installations` | Anlagen des Kontos (spaltenweise: `{"id": [..], …}`) |
| `GET …/installations/{id}/device-links` | verknüpfte Geräte (`deviceType` `emc`/`storage`, `deviceId` = Seriennummer) |
| `GET …/installations/{id}/device-links/{emcLinkId}/sub` | Untergeräte; `controlled[]` = Wallboxen (`type: "Evse"`) |
| `GET …/installations/{id}/config` | Anlagen-Konfiguration (siehe unten) |

## Schreiben

Jeder Schreibbefehl wird mit `POST …/installations/{id}/config/sync` an das Gerät übertragen
(Antwort: Liste von Job-IDs).

### Anlagen-Konfiguration – `PUT …/installations/{id}/config` (Antwort 204)

| Portal | Feld | Wert |
|---|---|---|
| Einstellungen → Solar Priorität: Priorität 2 = Energiespeicher | `emsBatteryBeforeCarMode` | `true` = Batterie zuerst, `false` = Ladestation zuerst |
| Speichermanagement → Solarmodus: Speicher nutzen | `emsBatteryToCarMode` | `true`/`false` – nur bei `emsBatteryBeforeCarMode = false` |
| Speichermanagement → Boost-Modus: Speicher nutzen | `emsWallboxEnforcePowerAssignment` | `true`/`false` – nur bei `emsBatteryBeforeCarMode = false` |

Das Portal schickt `emsBatteryBeforeCarMode` immer mit, z. B.
`{"emsBatteryBeforeCarMode": false, "emsBatteryToCarMode": true}`.

### Wallbox-Ladestrategie – `PUT …/installations/{id}/device-links/{emcLinkId}/sub/controlled/{evseId}` (204)

Body = `deviceName`, `parameters` (aktueller Stand) und `evseSubTypeParameters`. Entscheidend ist
`parameters.activated` und `parameters.sunMode`:

| Ladestrategie | `sunMode.activated` | `sunMode.chargingStrategy` | `sunMode.parameterList` |
|---|---|---|---|
| PV-Überschussladen | `true` | `Disabled` | `[]` |
| PV + Mindestladung | `true` | `Immediate` | 7× `{"minEnergy": "7"}` (kWh, je Wochentag) |
| PV + Zieltermin | `true` | `Delayed` | 7× `{"daytime": "21600", "minEnergy": "7"}` (Sekunden ab Mitternacht) |
| Boostladen | `false` | `Disabled` | `[]` |

### Entladegrenze „Bis Ladezustand“ (%) – Wallbox-Konfiguration

E3/DC-Speicher kennen eine Untergrenze, bis zu der der Speicher ins Auto entladen wird
(z. B. 60 % für die Nacht behalten). Im **flow**-Portal gibt es diese Einstellung nicht;
die Anlagen-Konfiguration (`…/installations/{id}/config`) hat dafür kein Feld. Sie sitzt
stattdessen auf der **E3/DC-Wallbox-Konfiguration** – demselben Objekt, über das auch der
Boost (`chargeFull`) geschrieben wird:

```
GET/PUT https://e3dc.e3dc.com/wallboxes/{emcSeriennummer}/{index}/configuration
```

| Portal (my.e3dc.com → Wallbox) | Feld | Wert |
|---|---|---|
| Batterieentladung durch Wallbox → Bis Ladezustand | `soc` | 0–100 (%), `0` = keine Grenze |

- `{emcSeriennummer}` ist die `deviceId` des EMC-Device-Links (die SN aus der Portal-URL).
- `{index}` ist der `index` der Wallbox aus `…/sub` → `controlled[]`.
- Schreiben als Teil-PUT `{"soc": <wert>}`, wie beim Boost. Kein `config/sync` nötig.
- Verifiziert per Mitschnitt am 07.11.2026 (Feldname `soc`, Nachbarfelder `sunModeActive`,
  `minChargeCurrent`, `minChargePower`, `maxChargeCurrent`, `parameterList`, `chargeFull`).
