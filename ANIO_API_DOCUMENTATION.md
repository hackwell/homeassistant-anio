# ANIO Cloud API - Entwicklerdokumentation

Diese Dokumentation beschreibt die Integration mit der ANIO Cloud API für die Entwicklung von Apps, die mit ANIO Kinder-Smartwatches kommunizieren.

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Basis-Konfiguration](#basis-konfiguration)
3. [Authentifizierung](#authentifizierung)
4. [Token-Management](#token-management)
5. [Geräte-Verwaltung](#geräte-verwaltung)
6. [Chat-Funktionen](#chat-funktionen)
7. [Weitere Endpunkte](#weitere-endpunkte)
8. [Fehlerbehandlung](#fehlerbehandlung)
9. [Code-Beispiele](#code-beispiele)

---

## Übersicht

### API-Basis-URL
```
https://api.anio.cloud
```

### API-Dokumentation (Swagger)
Die vollständige OpenAPI-Spezifikation ist verfügbar unter:
```
https://api.anio.cloud/api
```

### Authentifizierungsschema
- **Typ**: JWT (JSON Web Token)
- **Header**: `Authorization: Bearer <accessToken>`
- **Token-Gültigkeit**: Access Token ~15 Minuten, Refresh Token ~1 Jahr

---

## Basis-Konfiguration

### Erforderliche Header für alle Requests

| Header | Erforderlich | Beschreibung |
|--------|--------------|--------------|
| `Content-Type` | Ja | `application/json` |
| `client-id` | Ja (Login) | Client-Identifier: `anio` |
| `app-uuid` | Ja | Eindeutige App-Installations-ID (UUID v4) |
| `Authorization` | Nach Login | `Bearer <accessToken>` |
| `accept-language` | Optional | Sprache für Antworten, z.B. `de-DE` |

### App-UUID generieren

Die `app-uuid` identifiziert eine App-Installation eindeutig. Sie sollte einmalig beim ersten App-Start generiert und persistent gespeichert werden.

```javascript
// JavaScript/TypeScript
const appUuid = crypto.randomUUID();
// Beispiel: "550e8400-e29b-41d4-a716-446655440000"
```

```swift
// Swift/iOS
let appUuid = UUID().uuidString
```

```kotlin
// Kotlin/Android
val appUuid = UUID.randomUUID().toString()
```

---

## Authentifizierung

### Login-Endpunkt

**POST** `/v1/auth/login`

Authentifiziert einen Benutzer und gibt Tokens zurück.

#### Request

**Headers:**
```
Content-Type: application/json
client-id: anio
app-uuid: <deine-app-uuid>
```

**Body:**
```json
{
  "email": "benutzer@example.com",
  "password": "geheimes-passwort",
  "otpCode": "123456"  // Optional, nur bei aktivierter 2FA
}
```

#### Response (200 OK)

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "isOtpCodeRequired": false
}
```

#### Response bei 2FA erforderlich

```json
{
  "isOtpCodeRequired": true,
  "refreshToken": null,
  "accessToken": null
}
```

Bei dieser Antwort muss der Login-Request mit dem `otpCode` wiederholt werden.

#### Fehler-Responses

| Status | Bedeutung |
|--------|-----------|
| 401 | Falsche Zugangsdaten oder ungültige client-id |
| 400 | Ungültiges JSON oder fehlende Felder |

#### cURL-Beispiel

```bash
curl -X POST "https://api.anio.cloud/v1/auth/login" \
  -H "Content-Type: application/json" \
  -H "client-id: anio" \
  -H "app-uuid: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "email": "benutzer@example.com",
    "password": "geheimes-passwort"
  }'
```

---

## Token-Management

### Access Token erneuern

**POST** `/v1/auth/refresh-access-token`

Der Access Token ist nur ~15 Minuten gültig. Vor Ablauf muss ein neuer Token angefordert werden.

#### Request

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <refreshToken>
app-uuid: <deine-app-uuid>
```

#### Response (200 OK)

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Logout

**POST** `/v1/auth/logout`

Invalidiert die aktuelle Session.

**Headers:**
```
Authorization: Bearer <accessToken>
app-uuid: <deine-app-uuid>
```

### Token-Struktur (JWT Payload)

```json
{
  "type": "ACCESS_TOKEN",
  "id": "c7816af8-a875-4ecb-bcaf-10c2049c94ef",  // User-ID
  "clientId": "ANIO",
  "iat": 1769096895,  // Issued at (Unix timestamp)
  "exp": 1769097795   // Expires at (Unix timestamp)
}
```

---

## Geräte-Verwaltung

### Geräteliste abrufen

**GET** `/v1/device/list`

Gibt alle Geräte zurück, die dem eingeloggten Benutzer zugeordnet sind.

#### Request

**Headers:**
```
Authorization: Bearer <accessToken>
app-uuid: <deine-app-uuid>
```

#### Response (200 OK)

```json
[
  {
    "id": "4645a84ad7",
    "imei": "351552420608023",
    "registrationCode": "152042006008020",
    "firstRegisteredAt": "2026-01-22T13:51:54.000Z",
    "additionalInfo": null,
    "config": {
      "generation": "6",
      "type": "WATCH",
      "firmwareVersion": "ANIO6_Kids_V2.00.12.B",
      "maxChatMessageLength": 95,
      "maxPhonebookEntries": 20,
      "maxAlarmTimes": 3,
      "maxSilenceTimes": 4,
      "maxGeofences": 5,
      "hasChatName": true,
      "hasTextChat": true,
      "hasVoiceChat": true,
      "hasEmojis": true,
      "hasLaidDownAlert": false,
      "hasLowBatteryAlert": true,
      "hasEmergencyAlert": true,
      "hasHearts": false,
      "hasBestFriend": false,
      "hasStepTarget": true,
      "hasStepCounter": true,
      "hasLocatingSwitch": true,
      "hasSilenceTime": true,
      "hasSilenceTimeSwitch": true,
      "hasCallButton": true,
      "hasSilenceTimeWeekdays": true,
      "hasPoliceCallSwitch": false,
      "hasPhonebookSwitch": false,
      "hasAutomaticTimeChange": true,
      "hasDialPadSwitch": true,
      "hasLanguages": ["ENGLISH", "GERMAN", "FRENCH", "..."],
      "hasRingProfiles": ["VIBRATE", "RING_AND_VIBRATE"],
      "hasPhonebookAvatars": true,
      "maxSchoolWayTimeLength": 60,
      "firmwareAutoUpdateDisabled": false,
      "minSatellitesForValidPosition": 5
    },
    "settings": {
      "locatingInterval": "SIXTY_MINUTES",
      "timezone": "+01:00",
      "language": "GERMAN",
      "sosPhoneNr1": "+49123456789",
      "sosPhoneNr2": "+49987654321",
      "centerPhoneNr": "+49123456789",
      "smsPassword": "123456",
      "name": "Marla",
      "avatarUploadedAt": "2026-01-22T13:52:24.500Z",
      "gender": "FEMALE",
      "ringProfile": "RING_AND_VIBRATE",
      "hexColor": "#E7451B",
      "phoneNr": "+49151123456789",
      "weight": 50,
      "stepLength": 50,
      "hearts": 0,
      "stepTarget": 100000,
      "isLaidDownAlertActive": false,
      "isLowBatteryAlertActive": true,
      "isEmergencyAlertActive": true,
      "isLocatingActive": true,
      "isPoliceCallActive": false,
      "isPhonebookActive": true,
      "isAutomaticTimeChangeEnabled": true,
      "isDialPadEnabled": true,
      "isStepCountEnabled": true
    },
    "user": {
      "id": "c7816af8-a875-4ecb-bcaf-10c2049c94ef",
      "email": "benutzer@example.com",
      "gender": "FEMALE",
      "isVerified": true,
      "isBanned": false,
      "loginNotificationType": "PUSH",
      "isOtpEnabled": false,
      "mailLanguage": "DE",
      "createdAt": "2026-01-22T13:51:54.195Z",
      "updatedAt": "2026-01-22T13:52:09.000Z"
    }
  }
]
```

### Wichtige Felder für die App-Entwicklung

| Feld | Beschreibung | Verwendung |
|------|--------------|------------|
| `id` | Geräte-ID | Für alle gerätespezifischen API-Calls |
| `config.maxChatMessageLength` | Max. Nachrichtenlänge | Validierung vor dem Senden |
| `config.hasTextChat` | Text-Chat verfügbar | Feature-Toggle |
| `config.hasVoiceChat` | Voice-Chat verfügbar | Feature-Toggle |
| `config.hasEmojis` | Emojis verfügbar | Feature-Toggle |
| `settings.name` | Gerätename | Anzeige in der UI |
| `settings.hexColor` | Zugewiesene Farbe | UI-Styling |

### Einzelnes Gerät abrufen

**GET** `/v1/device/{deviceId}`

---

## Chat-Funktionen

### Text-Nachricht senden

**POST** `/v1/chat/message/text`

Sendet eine Textnachricht an ein Gerät.

#### Request

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <accessToken>
app-uuid: <deine-app-uuid>
```

**Body:**
```json
{
  "deviceId": "4645a84ad7",
  "text": "Hallo! Wie geht es dir?",
  "username": "Papa"
}
```

| Feld | Typ | Erforderlich | Beschreibung |
|------|-----|--------------|--------------|
| `deviceId` | string | Ja | ID des Zielgeräts |
| `text` | string | Ja | Nachrichtentext (max. siehe `config.maxChatMessageLength`) |
| `username` | string | Nein | Absendername (wird auf der Uhr angezeigt) |

#### Response (201 Created)

```json
{
  "id": "697246f55bbb8c58a60436c1",
  "username": "Papa",
  "text": "Hallo! Wie geht es dir?",
  "type": "TEXT",
  "sender": "APP",
  "isReceived": false,
  "isRead": false,
  "deviceId": "4645a84ad7",
  "createdAt": "2026-01-22T15:49:09.345Z",
  "updatedAt": "2026-01-22T15:49:09.345Z"
}
```

| Feld | Beschreibung |
|------|--------------|
| `id` | Eindeutige Nachrichten-ID |
| `type` | Nachrichtentyp: `TEXT`, `VOICE`, `EMOJI` |
| `sender` | Absender: `APP` (von der App) oder `WATCH` (von der Uhr) |
| `isReceived` | `true` wenn die Uhr die Nachricht empfangen hat |
| `isRead` | `true` wenn die Nachricht auf der Uhr gelesen wurde |

### Emoji-Nachricht senden

**POST** `/v1/chat/message/emoji`

**Body:**
```json
{
  "deviceId": "4645a84ad7",
  "text": "E01",
  "username": "Papa"
}
```

Emoji-Codes: `E01` bis `E12` (abhängig vom Gerät)

### Sprachnachricht senden

**POST** `/v1/chat/message/voice`

**Content-Type:** `multipart/form-data`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `deviceId` | string | ID des Zielgeräts |
| `username` | string | Absendername |
| `file` | binary | MP3-Datei (max. 2 MB) |

### Chat-Verlauf abrufen

**GET** `/v1/activity`

Gibt alle Aktivitäten inkl. Chat-Nachrichten zurück.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `from` | ISO 8601 DateTime | Nachrichten ab diesem Zeitpunkt |

---

## Weitere Endpunkte

### Standort & Tracking

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/device/{deviceId}/find` | POST | Gerät orten lassen |
| `/v1/geofence` | POST | Geofence erstellen |
| `/v1/geofence` | GET | Geofences abrufen |

### Geräte-Einstellungen

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/device/{deviceId}/settings` | PATCH | Einstellungen ändern |
| `/v1/device/{deviceId}/avatar` | POST | Avatar hochladen |
| `/v1/device/{deviceId}/poweroff` | POST | Gerät ausschalten |

### System

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/health` | GET | Health-Check |
| `/v1/version` | GET | API-Version |

---

## Fehlerbehandlung

### Standard-Fehlerformat

```json
{
  "message": "Beschreibung des Fehlers",
  "error": "Fehlertyp",
  "statusCode": 400
}
```

### HTTP-Statuscodes

| Code | Bedeutung | Aktion |
|------|-----------|--------|
| 200 | Erfolg | - |
| 201 | Erstellt | Ressource wurde angelegt |
| 400 | Bad Request | Request-Body prüfen |
| 401 | Unauthorized | Token erneuern oder neu einloggen |
| 403 | Forbidden | Keine Berechtigung für diese Ressource |
| 404 | Not Found | Endpunkt oder Ressource existiert nicht |
| 429 | Too Many Requests | Rate-Limit erreicht, warten |
| 500 | Server Error | Später erneut versuchen |

### Token-Ablauf behandeln

```javascript
async function apiCall(endpoint, options) {
  let response = await fetch(endpoint, options);

  if (response.status === 401) {
    // Token abgelaufen - erneuern
    const newToken = await refreshAccessToken();
    options.headers['Authorization'] = `Bearer ${newToken}`;
    response = await fetch(endpoint, options);
  }

  return response;
}
```

---

## Code-Beispiele

### TypeScript/JavaScript API-Client

```typescript
// anio-api-client.ts

interface LoginCredentials {
  email: string;
  password: string;
  otpCode?: string;
}

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  isOtpCodeRequired?: boolean;
}

interface Device {
  id: string;
  config: DeviceConfig;
  settings: DeviceSettings;
}

interface ChatMessage {
  id: string;
  text: string;
  username?: string;
  type: 'TEXT' | 'VOICE' | 'EMOJI';
  sender: 'APP' | 'WATCH';
  isReceived: boolean;
  isRead: boolean;
  deviceId: string;
  createdAt: string;
}

class AnioApiClient {
  private baseUrl = 'https://api.anio.cloud';
  private appUuid: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor(appUuid: string) {
    this.appUuid = appUuid;
  }

  // ============ Authentifizierung ============

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const response = await fetch(`${this.baseUrl}/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'client-id': 'anio',
        'app-uuid': this.appUuid,
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status}`);
    }

    const tokens: AuthTokens = await response.json();

    if (!tokens.isOtpCodeRequired) {
      this.accessToken = tokens.accessToken;
      this.refreshToken = tokens.refreshToken;
    }

    return tokens;
  }

  async refreshAccessToken(): Promise<string> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${this.baseUrl}/v1/auth/refresh-access-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.refreshToken}`,
        'app-uuid': this.appUuid,
      },
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    this.accessToken = data.accessToken;
    return this.accessToken;
  }

  async logout(): Promise<void> {
    await this.authenticatedRequest('/v1/auth/logout', { method: 'POST' });
    this.accessToken = null;
    this.refreshToken = null;
  }

  // ============ Geräte ============

  async getDevices(): Promise<Device[]> {
    return this.authenticatedRequest('/v1/device/list');
  }

  async getDevice(deviceId: string): Promise<Device> {
    return this.authenticatedRequest(`/v1/device/${deviceId}`);
  }

  // ============ Chat ============

  async sendTextMessage(
    deviceId: string,
    text: string,
    username?: string
  ): Promise<ChatMessage> {
    return this.authenticatedRequest('/v1/chat/message/text', {
      method: 'POST',
      body: JSON.stringify({ deviceId, text, username }),
    });
  }

  async sendEmojiMessage(
    deviceId: string,
    emojiCode: string,
    username?: string
  ): Promise<ChatMessage> {
    return this.authenticatedRequest('/v1/chat/message/emoji', {
      method: 'POST',
      body: JSON.stringify({ deviceId, text: emojiCode, username }),
    });
  }

  // ============ Helper ============

  private async authenticatedRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    if (!this.accessToken) {
      throw new Error('Not authenticated');
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.accessToken}`,
      'app-uuid': this.appUuid,
      ...options.headers,
    };

    let response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    // Token abgelaufen - erneuern und erneut versuchen
    if (response.status === 401) {
      await this.refreshAccessToken();
      headers['Authorization'] = `Bearer ${this.accessToken}`;
      response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      });
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || `Request failed: ${response.status}`);
    }

    return response.json();
  }
}

export default AnioApiClient;
```

### Verwendungsbeispiel

```typescript
// Beispiel: App-Initialisierung und Nachricht senden

import AnioApiClient from './anio-api-client';

// App-UUID einmalig generieren und persistent speichern
const APP_UUID = localStorage.getItem('app-uuid') || crypto.randomUUID();
localStorage.setItem('app-uuid', APP_UUID);

const api = new AnioApiClient(APP_UUID);

async function main() {
  try {
    // 1. Einloggen
    console.log('Logging in...');
    const tokens = await api.login({
      email: 'benutzer@example.com',
      password: 'geheimes-passwort',
    });

    if (tokens.isOtpCodeRequired) {
      // 2FA erforderlich - OTP-Code vom Benutzer anfordern
      const otpCode = prompt('Enter OTP code:');
      await api.login({
        email: 'benutzer@example.com',
        password: 'geheimes-passwort',
        otpCode: otpCode!,
      });
    }

    // 2. Geräte abrufen
    console.log('Fetching devices...');
    const devices = await api.getDevices();
    console.log(`Found ${devices.length} device(s)`);

    if (devices.length > 0) {
      const device = devices[0];
      console.log(`First device: ${device.settings.name} (${device.id})`);

      // 3. Nachrichtenlänge prüfen
      const maxLength = device.config.maxChatMessageLength;
      console.log(`Max message length: ${maxLength}`);

      // 4. Nachricht senden
      const message = await api.sendTextMessage(
        device.id,
        'Hallo! Wie geht es dir?',
        'Papa'
      );
      console.log(`Message sent: ${message.id}`);
    }

    // 5. Ausloggen
    await api.logout();
    console.log('Logged out');

  } catch (error) {
    console.error('Error:', error);
  }
}

main();
```

### Swift/iOS Beispiel

```swift
import Foundation

class AnioApiClient {
    private let baseUrl = "https://api.anio.cloud"
    private let appUuid: String
    private var accessToken: String?
    private var refreshToken: String?

    init(appUuid: String) {
        self.appUuid = appUuid
    }

    func login(email: String, password: String) async throws -> Bool {
        var request = URLRequest(url: URL(string: "\(baseUrl)/v1/auth/login")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("anio", forHTTPHeaderField: "client-id")
        request.setValue(appUuid, forHTTPHeaderField: "app-uuid")

        let body = ["email": email, "password": password]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(LoginResponse.self, from: data)

        if response.isOtpCodeRequired == true {
            return false // OTP erforderlich
        }

        self.accessToken = response.accessToken
        self.refreshToken = response.refreshToken
        return true
    }

    func getDevices() async throws -> [Device] {
        return try await authenticatedRequest(endpoint: "/v1/device/list")
    }

    func sendMessage(deviceId: String, text: String, username: String?) async throws -> ChatMessage {
        var body: [String: String] = ["deviceId": deviceId, "text": text]
        if let username = username {
            body["username"] = username
        }

        return try await authenticatedRequest(
            endpoint: "/v1/chat/message/text",
            method: "POST",
            body: body
        )
    }

    private func authenticatedRequest<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: [String: String]? = nil
    ) async throws -> T {
        guard let token = accessToken else {
            throw ApiError.notAuthenticated
        }

        var request = URLRequest(url: URL(string: "\(baseUrl)\(endpoint)")!)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue(appUuid, forHTTPHeaderField: "app-uuid")

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(T.self, from: data)
    }
}

// MARK: - Models

struct LoginResponse: Decodable {
    let accessToken: String?
    let refreshToken: String?
    let isOtpCodeRequired: Bool?
}

struct Device: Decodable {
    let id: String
    let config: DeviceConfig
    let settings: DeviceSettings
}

struct DeviceConfig: Decodable {
    let maxChatMessageLength: Int
    let hasTextChat: Bool
    let hasVoiceChat: Bool
}

struct DeviceSettings: Decodable {
    let name: String
    let hexColor: String
}

struct ChatMessage: Decodable {
    let id: String
    let text: String
    let username: String?
    let type: String
    let sender: String
    let isReceived: Bool
    let isRead: Bool
}

enum ApiError: Error {
    case notAuthenticated
}
```

---

## Anhang

### Vollständige Endpunkt-Übersicht

```
Auth:
  POST /v1/auth/login
  POST /v1/auth/refresh-access-token
  POST /v1/auth/logout

Devices:
  GET  /v1/device/list
  GET  /v1/device/{deviceId}
  POST /v1/device/register
  POST /v1/device/{deviceId}/unlink
  GET  /v1/device/{deviceId}/settings
  PATCH /v1/device/{deviceId}/settings
  POST /v1/device/{deviceId}/avatar
  POST /v1/device/{deviceId}/find
  POST /v1/device/{deviceId}/poweroff

Chat:
  POST /v1/chat/message/text
  POST /v1/chat/message/voice
  POST /v1/chat/message/emoji

Activity:
  GET /v1/activity

Geofence:
  GET  /v1/geofence
  POST /v1/geofence
  DELETE /v1/geofence/{id}

System:
  GET /v1/health
  GET /v1/version
  GET /metrics
```

### Wichtige Hinweise

1. **Rate Limiting**: Die API hat Rate Limits. Implementiere exponentielles Backoff bei 429-Fehlern.

2. **Token-Speicherung**: Speichere Tokens sicher (Keychain auf iOS, EncryptedSharedPreferences auf Android).

3. **App-UUID**: Die `app-uuid` muss pro Installation eindeutig sein und persistent gespeichert werden.

4. **Nachrichtenlänge**: Prüfe immer `config.maxChatMessageLength` bevor du eine Nachricht sendest.

5. **Feature-Flags**: Prüfe die `config.has*`-Felder um zu wissen, welche Features das Gerät unterstützt.

6. **Offline-Handling**: Nachrichten werden in eine Queue gestellt. `isReceived: false` bedeutet, dass die Uhr die Nachricht noch nicht empfangen hat.

---

*Dokumentation erstellt am: 22. Januar 2026*
*API-Version: v1*
