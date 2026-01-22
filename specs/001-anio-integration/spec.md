# Feature Specification: ANIO Smartwatch Home Assistant Integration

**Feature Branch**: `001-anio-integration`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "Es soll eine Integration für die ANIO Smartwatch für Home Assistant gebaut werden über ein Home Assistant Plugin."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Uhr einrichten und Status sehen (Priority: P1)

Als Home Assistant Nutzer möchte ich meine ANIO Kinder-Smartwatch in Home Assistant einbinden, um den aktuellen Status (Batterie, Standort, Online-Status) meiner Kinder-Uhr auf einen Blick im Dashboard zu sehen.

**Why this priority**: Dies ist die Grundfunktion der Integration. Ohne Geräteeinrichtung und Statusanzeige sind alle anderen Features nutzlos. Die Statusübersicht gibt Eltern Sicherheit über den Zustand der Uhr ihres Kindes.

**Independent Test**: Kann vollständig getestet werden, indem man die Integration hinzufügt und prüft, ob alle Sensoren korrekte Werte anzeigen.

**Acceptance Scenarios**:

1. **Given** Home Assistant läuft und der Nutzer hat ANIO-Zugangsdaten, **When** der Nutzer die Integration über die UI hinzufügt und sich anmeldet, **Then** erscheint die Uhr als Gerät mit allen Sensoren (Batterie, Standort, Online-Status, Schritte).

2. **Given** die Integration ist eingerichtet, **When** sich der Batteriestatus der Uhr ändert, **Then** wird der neue Wert innerhalb von 5 Minuten in Home Assistant angezeigt.

3. **Given** die Integration ist eingerichtet, **When** die Uhr offline geht (ausgeschaltet/kein Netz), **Then** zeigt der Online-Status-Sensor dies korrekt an.

4. **Given** der Nutzer hat 2FA aktiviert, **When** er sich in der Integration anmeldet, **Then** wird er aufgefordert, den OTP-Code einzugeben, und die Anmeldung erfolgt nach korrekter Eingabe.

---

### User Story 2 - Nachrichten an die Uhr senden (Priority: P2)

Als Elternteil möchte ich über Home Assistant Textnachrichten oder Emojis an die Smartwatch meines Kindes senden, um schnell kommunizieren zu können - auch automatisiert über Automationen.

**Why this priority**: Die Messaging-Funktion ist ein Kernfeature der ANIO-Uhr und ermöglicht direkte Kommunikation. Die Integration in Home Assistant ermöglicht zudem Automatisierungen (z.B. "Essen ist fertig" bei Sonnenuntergang).

**Independent Test**: Kann getestet werden, indem eine Nachricht über den Notify-Service gesendet und auf der Uhr empfangen wird.

**Acceptance Scenarios**:

1. **Given** die Integration ist eingerichtet, **When** der Nutzer den Notify-Service mit einer Textnachricht aufruft, **Then** erscheint die Nachricht auf der Uhr des Kindes.

2. **Given** die Integration ist eingerichtet, **When** der Nutzer eine Emoji-Nachricht (E01-E12) sendet, **Then** wird das entsprechende Emoji auf der Uhr angezeigt.

3. **Given** die Nachrichtenlänge überschreitet das Maximum der Uhr (95 Zeichen), **When** der Nutzer die Nachricht sendet, **Then** wird eine klare Fehlermeldung angezeigt (keine stille Kürzung).

4. **Given** eine Automation ist konfiguriert, **When** der Trigger auslöst, **Then** wird die Nachricht automatisch an die Uhr gesendet.

5. **Given** die Integration ist eingerichtet, **When** das Kind eine Nachricht von der Uhr sendet, **Then** wird ein `anio_message_received` Event in Home Assistant gefeuert mit Inhalt und Absender.

6. **Given** eine Automation lauscht auf `anio_message_received`, **When** das Kind eine Nachricht sendet, **Then** kann die Automation reagieren (z.B. Push-Benachrichtigung an Eltern-Handy).

---

### User Story 3 - Standortverfolgung auf der Karte (Priority: P3)

Als Elternteil möchte ich den aktuellen Standort der Uhr auf der Home Assistant Karte sehen und bei Bedarf eine aktuelle Ortung anfordern, um zu wissen, wo sich mein Kind befindet.

**Why this priority**: Standortverfolgung ist wichtig für die Kindersicherheit, aber erst sinnvoll nutzbar, wenn die Grundintegration (P1) funktioniert. Der Device Tracker ermöglicht auch Zonen-Automationen.

**Independent Test**: Kann getestet werden, indem der Standort auf der Karte überprüft und eine manuelle Ortung ausgelöst wird.

**Acceptance Scenarios**:

1. **Given** die Integration ist eingerichtet und die Uhr hat GPS-Empfang, **When** der Nutzer die Karte öffnet, **Then** wird der Standort der Uhr mit korrekten Koordinaten angezeigt.

2. **Given** der Nutzer drückt den "Orten"-Button, **When** die Uhr erreichbar ist, **Then** wird eine aktuelle Standortabfrage an die Uhr gesendet und der Standort aktualisiert.

3. **Given** die Uhr betritt/verlässt eine Home Assistant Zone, **When** der Standort aktualisiert wird, **Then** können Automationen basierend auf der Zone ausgelöst werden.

---

### User Story 4 - Schrittzähler und Aktivitätsdaten (Priority: P4)

Als Elternteil möchte ich die täglichen Schritte meines Kindes in Home Assistant sehen, um die Aktivität zu verfolgen und ggf. in Dashboards oder Statistiken zu verwenden.

**Why this priority**: Nice-to-have Feature, das die vorhandenen API-Daten nutzt. Bietet Mehrwert für gesundheitsbewusste Familien, ist aber nicht kritisch.

**Independent Test**: Kann getestet werden, indem der Schrittezähler-Sensor geprüft und mit der ANIO-App verglichen wird.

**Acceptance Scenarios**:

1. **Given** die Integration ist eingerichtet, **When** das Kind Schritte geht, **Then** wird der Schrittezähler-Sensor in Home Assistant aktualisiert.

2. **Given** der Nutzer nutzt Home Assistant Statistiken, **When** er den Schrittezähler-Sensor hinzufügt, **Then** werden historische Daten korrekt aufgezeichnet und visualisiert.

---

### Edge Cases

- Was passiert, wenn die ANIO API nicht erreichbar ist? → Integration zeigt "Unavailable" Status, versucht erneut beim nächsten Polling-Intervall
- Was passiert, wenn das Access Token abläuft? → Integration refresht automatisch proaktiv vor Ablauf
- Was passiert, wenn der Nutzer mehrere Uhren hat? → Alle Uhren werden als separate Geräte mit eigenen Entities angelegt
- Was passiert bei Rate Limiting (429)? → Exponentielles Backoff, Warnung im Log
- Was passiert, wenn die Uhr keine GPS-Daten hat? → Standort-Entity zeigt "Unknown" an
- Was passiert bei ungültigen Zugangsdaten während der Einrichtung? → Klare Fehlermeldung, erneute Eingabemöglichkeit

## Requirements *(mandatory)*

### Functional Requirements

**Authentifizierung & Setup**
- **FR-001**: System MUSS Nutzer über E-Mail und Passwort authentifizieren können
- **FR-002**: System MUSS Zwei-Faktor-Authentifizierung (OTP) unterstützen, wenn vom ANIO-Konto aktiviert
- **FR-003**: System MUSS Access Tokens automatisch erneuern, bevor sie ablaufen
- **FR-004**: System MUSS die Einrichtung über die Home Assistant UI (Config Flow) ermöglichen
- **FR-005**: System MUSS gespeicherte Zugangsdaten sicher ablegen

**Geräte & Sensoren**
- **FR-006**: System MUSS alle verknüpften Uhren des Nutzers als separate Geräte darstellen
- **FR-007**: System MUSS für jede Uhr folgende Sensoren bereitstellen: Batteriestatus (%), Online-Status, Schrittezähler, Letzter Kontakt
- **FR-008**: System MUSS Geräteinformationen anzeigen: Name, Firmware-Version, Gerätegeneration
- **FR-009**: System MUSS Daten im konfigurierbaren Intervall aktualisieren (Standard: 5 Minuten)

**Standortverfolgung**
- **FR-010**: System MUSS den letzten bekannten Standort jeder Uhr als Device Tracker bereitstellen
- **FR-011**: System MUSS GPS-Koordinaten, Genauigkeit und Zeitstempel der letzten Ortung anzeigen
- **FR-012**: System MUSS eine manuelle Ortungsanfrage per Button ermöglichen
- **FR-020**: System MUSS konfigurierte ANIO-Geofences als Binary Sensoren anzeigen (aktiv wenn Uhr in Zone)

**Gerätesteuerung**
- **FR-023**: System MUSS einen Button zum Ausschalten der Uhr bereitstellen
- **FR-024**: Der Power-Off Button MUSS eine Warnung in der Entity-Beschreibung enthalten (Uhr nicht mehr erreichbar nach Ausschalten)

**Messaging**
- **FR-013**: System MUSS das Senden von Textnachrichten an die Uhr über einen Notify-Service ermöglichen
- **FR-014**: System MUSS das Senden von Emoji-Nachrichten (E01-E12) unterstützen
- **FR-015**: System MUSS die maximale Nachrichtenlänge der Uhr validieren und bei Überschreitung einen Fehler melden
- **FR-016**: System MUSS einen konfigurierbaren Absendernamen für Nachrichten unterstützen
- **FR-021**: System MUSS eingehende Nachrichten von der Uhr als Home Assistant Events feuern
- **FR-022**: Events MÜSSEN Nachrichtentyp (Text/Emoji/Voice), Inhalt, Zeitstempel und Geräte-ID enthalten

**Fehlerbehandlung**
- **FR-017**: System MUSS bei API-Fehlern benutzerfreundliche Meldungen anzeigen
- **FR-018**: System MUSS bei Rate Limiting exponentielles Backoff implementieren
- **FR-019**: System MUSS bei Authentifizierungsfehlern einen Re-Auth Flow starten

### Key Entities

- **ANIO Watch (Gerät)**: Repräsentiert eine einzelne Kinder-Smartwatch. Enthält Geräte-ID, Name, Firmware-Version, Generation, zugewiesene Farbe.

- **Batterie-Sensor**: Aktueller Batteriestand der Uhr in Prozent. Zeigt niedrigen Batteriestand visuell an.

- **Online-Status (Binary Sensor)**: Gibt an, ob die Uhr aktuell mit der ANIO Cloud verbunden ist. Ermöglicht Automationen bei Verbindungsverlust.

- **Schrittezähler-Sensor**: Anzahl der Schritte des aktuellen Tages. Wird für Aktivitätsstatistiken verwendet.

- **Standort (Device Tracker)**: GPS-Position der Uhr mit Koordinaten und Genauigkeit. Ermöglicht Kartenansicht und Zonen-Automationen.

- **Letzte Aktivität (Sensor)**: Zeitstempel des letzten bekannten Kontakts mit der Uhr.

- **Ortungs-Button**: Löst eine aktuelle Standortabfrage bei der Uhr aus.

- **Power-Off Button**: Schaltet die Uhr aus. Enthält Warnung: "Uhr ist nach dem Ausschalten nicht mehr erreichbar bis manuell eingeschaltet."

- **Nachrichtenservice (Notify)**: Ermöglicht das Senden von Text- und Emoji-Nachrichten an die Uhr.

- **Geofence-Sensor (Binary Sensor)**: Zeigt an, ob sich die Uhr innerhalb eines in ANIO konfigurierten Geofence befindet. Ein Sensor pro Geofence.

- **Eingehende Nachrichten (Event)**: `anio_message_received` Event mit Nachrichtentyp, Inhalt, Zeitstempel und Geräte-ID. Ermöglicht Automationen bei Nachrichten vom Kind.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nutzer können die Integration innerhalb von 2 Minuten einrichten (inkl. 2FA wenn aktiviert)
- **SC-002**: Alle Sensoren zeigen aktuelle Werte innerhalb von 5 Minuten nach Änderung auf der Uhr
- **SC-003**: Gesendete Nachrichten erscheinen innerhalb von 30 Sekunden auf der Uhr
- **SC-004**: Die Integration verbraucht weniger als 50 MB Arbeitsspeicher bei 5 verbundenen Uhren
- **SC-005**: Der Home Assistant Start wird durch die Integration um maximal 5 Sekunden verzögert
- **SC-006**: 100% der Funktionen sind über die Home Assistant UI bedienbar (keine YAML-Konfiguration erforderlich)
- **SC-007**: Bei API-Ausfällen erholt sich die Integration automatisch innerhalb von 10 Minuten nach Wiederherstellung

## Clarifications

### Session 2026-01-22

- Q: Distributionsmodell (HACS, HA Core, Custom Component)? → A: HACS
- Q: Sprachnachrichten (MP3-Upload) unterstützen? → A: Nein, später (zukünftige Erweiterung)
- Q: Geofence-Verwaltung über HA? → A: Read-only (ANIO-Geofences als Sensoren anzeigen)
- Q: Eingehende Nachrichten von der Uhr empfangen? → A: Ja, als HA-Events (für Automationen)
- Q: Power Off Button für Uhr? → A: Ja, mit Warnung in Entity-Beschreibung

## Out of Scope (v1.0)

- **Sprachnachrichten**: MP3-Upload an die Uhr (zukünftige Erweiterung)
- **Geofence-Verwaltung**: Erstellen/Bearbeiten/Löschen von ANIO-Geofences (nur Read-only)

## Assumptions

- **Distribution**: Die Integration wird über HACS (Home Assistant Community Store) verteilt
- Der Nutzer hat ein bestehendes ANIO Cloud Konto mit mindestens einer registrierten Uhr
- Die ANIO Cloud API bleibt in ihrer aktuellen Form verfügbar (v1)
- Home Assistant Version 2024.1 oder neuer wird verwendet
- Eine stabile Internetverbindung ist vorhanden
- Die Uhr ist mit der ANIO Cloud verbunden (nicht nur lokal via Bluetooth)
