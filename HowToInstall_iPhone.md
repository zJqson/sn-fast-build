# How to install the iPhone build ("SN Fast") on your own iPhone

The `.ipa` from this repository is **unsigned**: Apple only lets an iPhone open apps that are signed. You sign it yourself, on your own phone, with your own Apple ID, using a free tool. Nobody else ever sees your Apple ID password.
(Unofficial personal build, not affiliated with Standard Notes or Proton.)

## What you need
* A Windows PC or a Mac with **Sideloadly** (free, https://sideloadly.io) and Apple's USB driver (iTunes / Apple Devices app on Windows).
* Your iPhone on the USB cable, **unlocked**, with **Developer Mode** switched on (Settings > Privacy & Security > Developer Mode; the phone restarts once).
* An Apple ID. A free one is enough (a free account is limited, see "Limits" below).
* The file `SN-Fast.ipa` from the release page (check its SHA-256 against `SN-Fast.ipa.sha256`).

## Steps
1. Plug the iPhone in, unlock it, tap **Trust** if asked (on the phone).
2. Open Sideloadly. The iPhone appears in the device box.
3. Drag `SN-Fast.ipa` onto the Sideloadly window (or use the IPA button).
4. Type your **Apple ID e-mail** in Sideloadly and press **Start**. Sideloadly asks for the Apple ID password and, if the account has two-factor sign-in, for the 6-digit code that appears on your iPhone. **You type these yourself.**
5. Wait until Sideloadly says it is done (a minute or two). The app "SN Fast" is now on the Home Screen.
6. On the iPhone: **Settings > General > VPN & Device Management > Developer App > your Apple ID > Trust**. Without this the app says "Untrusted Developer".
7. Open **SN Fast**. It has its own bundle id (`com.standardnotes.fastsync`), so it lives **next to** the App Store version of Standard Notes; the two do not share data.

## Sign in
* If the file was **personalized for your own sync server**, the sign-in screen already points at it: type your e-mail and password there.
* If you installed the plain release file, it starts on the hosted default server like the original app. To use another server: sign-in screen > **Advanced options** > **Custom** > type the address of your sync server (the websocket for push is derived from it).
* If your server is only reachable inside a VPN / tailnet, the VPN app must be connected on the phone before you sign in.

## Every 7 days (free Apple ID)
A free Apple ID signs an app for **7 days**. After that the app stops opening ("Unable to verify" / it just closes). Renew **before** that: plug the phone in and run Sideloadly again with the same file and the same Apple ID. It replaces the app **in place**:
your notes stay (they are synced with your server anyway). **Do not delete the app first.** Sideloadly can also refresh by itself while the PC and the phone are on the same Wi-Fi (its "daemon" option); that is a convenience, not a promise.

## Limits of a free Apple ID (why this build removes the Share extension)
* At most **3 sideloaded apps** at the same time (other sideloaded apps count too).
* At most **10 new App IDs per 7 days**. An app with extensions uses one App ID for each extension; this build removes the Share extension so it needs exactly one.
* No push notifications, no iCloud, no associated domains: this build does not use them.

## If something goes wrong
| what you see | what to do |
|---|---|
| "Untrusted Developer" on the phone | step 6 (Trust the Apple ID under VPN & Device Management) |
| Sideloadly: "maximum number of apps" | remove another sideloaded app, or wait until it expires |
| Sideloadly: "App ID limit" | wait (the counter is per 7 days) or use another Apple ID |
| The app does not open any more after a week | it expired: sign again with Sideloadly (see "Every 7 days") |
| Sideloadly cannot see the phone | unlock it, replug, tap Trust, check Developer Mode |
