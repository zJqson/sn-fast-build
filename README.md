# sn-fast-build

An **unofficial personal build recipe**: it takes a release of the open-source [Standard Notes app](https://github.com/standardnotes/app), applies a handful of small patches that make syncing feel faster on a phone,
and builds an **unsigned iPhone app (.ipa)** on GitHub's free macOS runner. It is **not affiliated with Standard Notes or Proton**, it is not an official build, and nothing here is endorsed by them.

* The workflow **clones upstream at a tag at build time**. No upstream source code is stored in this repository; only our patches, the workflow and a few small scripts.
* The builds are **unsigned**: nobody signs them for you. You sign and install the file yourself on your own phone (for example with Sideloadly and your own Apple ID), see [HowToInstall_iPhone.md](HowToInstall_iPhone.md).
* The app starts on the **hosted default servers**, exactly like the original. Nothing private is baked in or committed here.

## What the patches change (all small, all in `patches/`)

| patch | what it does |
|---|---|
| 0001 | sync right after the server says "items changed" (push), and a safety sync when no notification came for a while |
| 0002 | reconnect the websocket with a growing back-off and catch up after it was down |
| 0003 | sync and reconnect when the mobile app returns to the foreground |
| 0012 | optional fast polling (off unless switched on) |
| 0014 | allow the push websocket on the sync server's own host (a self-hosted server) |
| 0015 | retry quietly when the websocket service itself is down |
| 0017 | a custom sync server typed into the sign-in screen also gets its websocket (the URL path is kept) |
| mobile/0006 | open the push websocket in the mobile app (the stock mobile page leaves it empty) |
| android/0004 | side-by-side app id `com.standardnotes.fastsync` and the name "SN Fast" (Android) |
| ios/0005 | side-by-side bundle id `com.standardnotes.fastsync` and the name "SN Fast"; no entitlement a free Apple ID cannot sign |
| optional/0008 | the editor saves 350 ms after the last keystroke instead of 700 ms |

## How a build happens

Every push to `main` (and a manual "Run workflow") starts **iOS IPA (SN Fast, unsigned)**: Xcode 26 on `macos-15` (what upstream's own release job uses), and only if that fails Xcode 27 on the `xcode-27` runner.
Result: a pre-release **`ios-<run number>`** with `SN-Fast.ipa`, `SN-Fast.ipa.sha256` and `INFO.txt`, and the full log on the branch **`build-logs`** (`LATEST.txt` first). Both are public pages, no login needed:

* logs: `https://raw.githubusercontent.com/<owner>/<repo>/build-logs/LATEST.txt`
* builds: `https://github.com/<owner>/<repo>/releases`  (`<owner>/<repo>` = the address of this repository)

An **Android** base APK can be built too (`android.yml`, started by hand or by a change of that file): it is signed with a throwaway key made inside the run, so it is only a base that you re-sign on your own computer.

Details, settings and how to move to the next upstream release: [HowToUse.md](HowToUse.md).

## License

Upstream is licensed under the **GNU Affero General Public License v3.0**; the text is in [LICENSE](LICENSE). The patches in this repository are changes to that code and are **AGPL-3.0 as well**. The helper script
`.github/scripts/buildlog.py` carries an MPL-2.0 header (kept as it was). "Standard Notes" and "Proton" are trademarks of their owners; they are used here only to say what the build is made from.
