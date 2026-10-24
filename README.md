# NourOS

NourOS is an experimental native Android launcher with a futuristic glass interface, subtle cyan accents, a live clock, app search, and an app drawer.

## Current scope

- Native Kotlin + Jetpack Compose
- Android HOME intent so NourOS can be selected as the default launcher
- Queries installed activities that expose the standard launcher intent
- Search and launch apps
- GitHub Actions cloud build that uploads a debug APK

This is a launcher application, not custom Android firmware. Android continues to manage the lock screen, status bar, permissions, and protected system features.

## Build

Every push to `main` and manual workflow dispatch runs **NourOS Android Build**. Download the `nouros-debug-apk` artifact from the successful Actions run.

The workflow installs JDK 17, Gradle 8.9, Android SDK platform 35, and build tools 35.0.0, then runs `gradle assembleDebug`.

## Install on a Pixel

1. Download the artifact ZIP from GitHub Actions and extract `app-debug.apk`.
2. Open the APK on the Pixel and approve installation if Android asks.
3. Open Settings and search for **Default apps** or **Home app**.
4. Select NourOS to try it as the home screen. You can switch back to Pixel Launcher from the same setting.

Only install APKs you built or trust. This is a debug build intended for testing, not a production release.

## Development

- Application ID: `com.nour.os`
- Minimum Android version: Android 8.0 (API 26)
- Compile/target SDK: 35
- Kotlin: 2.0.21
- Android Gradle Plugin: 8.7.3
