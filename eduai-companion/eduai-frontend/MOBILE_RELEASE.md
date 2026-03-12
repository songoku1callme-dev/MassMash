# Lumnos Mobile Release — Android APK & iOS Build Guide

## Voraussetzungen

### Allgemein
- Node.js 18+ (`node -v`)
- npm 9+ (`npm -v`)
- Capacitor CLI ist bereits installiert (`npx cap --version`)

### Android
- **Android Studio** (neueste Version) — [Download](https://developer.android.com/studio)
- **Java JDK 17+** (`java -version`)
- Android SDK (wird mit Android Studio installiert)
- Min SDK: 24 (Android 7.0 Nougat)
- Target SDK: 34 (Android 14)

### iOS (nur auf macOS)
- **Xcode 15+** aus dem Mac App Store
- Xcode Command Line Tools (`xcode-select --install`)
- CocoaPods (`sudo gem install cocoapods`)
- Apple Developer Account (99 USD/Jahr fuer App Store)

---

## 1. Web-App bauen

```bash
cd eduai-companion/eduai-frontend

# Dependencies installieren
npm install

# Production Build erstellen
npm run build
```

Der Build landet in `dist/`.

---

## 2. Android APK Build

### 2.1 Capacitor Sync
```bash
# Web-Build in das Android-Projekt kopieren
npx cap sync android
```

### 2.2 Android Studio oeffnen
```bash
npx cap open android
```

Android Studio oeffnet sich automatisch mit dem Projekt.

### 2.3 Debug APK (zum Testen)
```bash
cd android
./gradlew assembleDebug
```

Die Debug-APK liegt unter:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

Diese APK kann direkt auf ein Android-Geraet installiert werden.

### 2.4 Signierte Release APK (fuer Google Play)

#### Keystore erstellen (einmalig!)
```bash
keytool -genkey -v \
  -keystore lumnos.keystore \
  -alias lumnos \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

**WICHTIG:** Den Keystore sicher aufbewahren! Ohne ihn koennen keine Updates veroeffentlicht werden.

#### In Android Studio signieren
1. **Build** > **Generate Signed Bundle / APK**
2. **Android App Bundle** waehlen (empfohlen fuer Play Store)
3. Keystore-Datei auswaehlen (`lumnos.keystore`)
4. Alias: `lumnos`, Passwort eingeben
5. Build Variant: `release`
6. **Finish**

Die signierte AAB liegt unter:
```
android/app/build/outputs/bundle/release/app-release.aab
```

### 2.5 Google Play Upload
1. [Google Play Console](https://play.google.com/console) oeffnen
2. **App erstellen** > Name: "Lumnos", Sprache: Deutsch
3. **Internal Testing** > **Neuen Release erstellen**
4. AAB-Datei hochladen
5. Release Notes schreiben
6. **Rollout starten**

---

## 3. iOS Build (nur macOS)

### 3.1 Capacitor Sync
```bash
npx cap sync ios
```

### 3.2 Xcode oeffnen
```bash
npx cap open ios
```

### 3.3 Signing konfigurieren
1. In Xcode: **App** Target > **Signing & Capabilities**
2. **Team** auswaehlen (Apple Developer Account)
3. **Bundle Identifier**: `de.lumnos.app`
4. Xcode erstellt automatisch ein Provisioning Profile

### 3.4 Build & Archivieren
1. **Product** > **Archive** (Scheme: "App", Device: "Any iOS Device")
2. Nach dem Archive: **Distribute App**
3. **App Store Connect** waehlen
4. Upload durchfuehren

### 3.5 App Store Connect
1. [App Store Connect](https://appstoreconnect.apple.com) oeffnen
2. Neue App erstellen
3. Build aus Xcode zuweisen
4. Screenshots, Beschreibung, Datenschutz ausfuellen
5. Zur Pruefung einreichen

---

## 4. Wichtige Konfigurationen

### App-Identifikation
| Eigenschaft | Wert |
|---|---|
| Application ID | `de.lumnos.app` |
| Version Code | `1` |
| Version Name | `1.0.0` |
| Min SDK (Android) | 24 (Android 7.0+) |
| Target SDK | 34 (Android 14) |
| iOS Deployment Target | 14.0+ |

### Clerk OAuth Deep Link
Vor dem ersten nativen Login muss in der **Clerk Dashboard** > **Redirect URLs** hinzugefuegt werden:
```
de.lumnos.app://oauth-callback
```

### Environment Variables
Die nativen Apps nutzen die gleiche Vercel-URL als Backend:
- Backend: `https://lumnos-backend.onrender.com`
- Clerk: Publishable Key ist im Build enthalten (via `VITE_CLERK_PUBLISHABLE_KEY`)

---

## 5. Capacitor Plugins (bereits installiert)

| Plugin | Funktion |
|---|---|
| `@capacitor/push-notifications` | Push-Benachrichtigungen |
| `@capacitor/camera` | Kamera-Zugriff (Schulbuch-Scanner) |
| `@capacitor/haptics` | Haptisches Feedback |
| `@capacitor/splash-screen` | Splash Screen |
| `@capacitor/status-bar` | Status Bar Styling |
| `@capacitor/share` | Native Share API |
| `@capacitor/local-notifications` | Lokale Benachrichtigungen |
| `@capacitor/browser` | In-App Browser |
| `@capacitor/network` | Netzwerk-Status |
| `@capacitor/app` | App Lifecycle |
| `@capacitor/keyboard` | Keyboard Events |

---

## 6. Troubleshooting

### Android: "AAPT: resource not found"
```bash
# Sync nochmal ausfuehren
npx cap sync android
```

### iOS: "No signing certificate"
1. Xcode > Preferences > Accounts > Apple ID hinzufuegen
2. Team auswaehlen in Signing & Capabilities

### Allgemein: Aenderungen nicht sichtbar
```bash
# Web neu bauen + sync
npm run build && npx cap sync
```

### Push Notifications testen
Push Notifications funktionieren nur auf echten Geraeten (nicht im Emulator).

---

## 7. PWA als Alternative

Falls kein nativer Build noetig ist — Lumnos ist auch als PWA installierbar:
1. `mass-mash.vercel.app` im Browser oeffnen
2. Chrome: Drei-Punkte-Menu > "Zum Startbildschirm hinzufuegen"
3. Safari (iOS): Teilen-Button > "Zum Home-Bildschirm"

Die PWA bietet: Offline-Cache, Standalone-Modus, Push-Benachrichtigungen (Chrome).
