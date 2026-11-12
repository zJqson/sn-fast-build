# How to use this build recipe

Unofficial personal recipe, not affiliated with Standard Notes or Proton (see [README.md](README.md)). Upstream and our patches are AGPL-3.0 ([LICENSE](LICENSE)).

## Where the settings are
Everything you may want to change is in **`config.ini`** (read once per run by `build.py` and by the workflows; nothing polls):

| section / key | meaning |
|---|---|
| `[upstream] repo`, `tag` | which upstream release to build (for example `@standardnotes/desktop@3.203.0`); the workflow clones it at build time |
| `[patches]` | the patch folders and their order; `apply_optional = yes/no` switches the optional folder |
| `[mobile] default_sync_server`, `websocket_url` | the presets written into the phone app's start page: the **hosted** defaults. A private server address is NOT put here (this repo is public) |
| `[ios] bundle_id`, `display_name`, `xcode_primary`, `xcode_fallback`, `strip_extensions` | the app's identity and which Xcode to try first (26, then 27); `strip_extensions = yes` removes the Share extension (it would need its own App ID on a free Apple account) |
| `[outputs] logs_branch`, `keep_releases` | the branch with the logs and how many `ios-N` pre-releases stay |

## Start a build
* **Push to `main`** (any change starts a run), or on GitHub: Actions > "iOS IPA (SN Fast, unsigned)" > Run workflow (optional input `only_xcode` = 26 or 27 to skip the fallback logic).
* A run takes about 15 to 45 minutes. Standard GitHub-hosted runners are free in a public repository.
* A newer push cancels the run that is still going (concurrency group `ios`).

## Where the result appears (no login needed)
* **Release** `ios-<run number>` (pre-release): `SN-Fast.ipa` (unsigned), `SN-Fast.ipa.sha256`, `INFO.txt` (upstream tag and commit, patch list with hashes, bundle id, minimum iOS, the IPA's SHA-256).
  `https://github.com/<owner>/<repo>/releases` ; direct file: `https://github.com/<owner>/<repo>/releases/download/ios-<N>/SN-Fast.ipa`
* **Log branch** `build-logs`: `LATEST.txt` = outcome of the newest run + the first 40 error lines (read this first), `run-<N>.log` = the full output.
  `curl -s https://raw.githubusercontent.com/<owner>/<repo>/build-logs/LATEST.txt`
* While a run is still going: the branch **`build-logs-live`** holds a snapshot of the log (`LATEST.txt` says RUNNING, `run-<N>.log` is the log so far), refreshed every 4 minutes. `curl -s https://raw.githubusercontent.com/<owner>/<repo>/build-logs-live/LATEST.txt` (the page itself is cached for a few minutes).
* Check the download: `shasum -a 256 SN-Fast.ipa` (macOS) or `certutil -hashfile SN-Fast.ipa SHA256` (Windows) must equal the line in `SN-Fast.ipa.sha256`.

Example of a successful `LATEST.txt` head:
```
run 7: SUCCESS - 1a2b3c4 - 2026-11-12T01:23:45Z
Status:   SUCCESS
Steps:    checkout=success setup_xcode=success xcode=success prepare=success node=success ruby=success yarn=success bundler=success bundle=success archive=success package=success probe=success release=success
Release:  https://github.com/<owner>/<repo>/releases/download/ios-7/SN-Fast.ipa
```

## Move to the next upstream release (one change)
1. Edit `tag` in `config.ini` (the upstream tag list: https://github.com/standardnotes/app/tags).
2. Optional, on any computer with git + Python 3: `py -3 build.py check-tags <new tag>` tells in a minute whether every patch still applies (exit 3 and the name of the patch if not).
3. Push. If a patch no longer applies the run stops at the step `prepare` and says which one: rebase that one patch onto the new code (redo the small change, `git format-patch`), replace the file in `patches/`, push again.

## The commands of `build.py` (Python 3.8+, standard library only)
| command | what it does |
|---|---|
| `py -3 build.py prepare --target ios --dest DIR` | clone the upstream tag (shallow) into DIR and apply the patches with `git am --3way`; stops loudly if one does not apply |
| `py -3 build.py preset-mobile --dest DIR` | write the `[mobile]` presets into the phone app's start page |
| `py -3 build.py check-tags TAG ...` | scratch-clone each tag and check that every patch applies (nothing is built) |
| `py -3 build.py probe-version --platform Mobile --version 3.203.0 --snjs 2.212.9` | one request without any credential to the hosted server: does it accept the version string of this build? (401 = yes) |
| `py -3 build.py cfg SECTION KEY` | print one value of `config.ini` |
Every command is written to `logs.txt` with a millisecond time. `state.json` (written atomically) lets a re-run skip finished steps.

## The finished file is unsigned, and has no private address
The `.ipa` from the release starts on the hosted default servers. It is signed later on the phone ([HowToInstall_iPhone.md](HowToInstall_iPhone.md)). Writing the address of a private sync server into the finished file is done locally, on your own computer,
after the download: the page that holds the two preset lines is `Payload/<app>.app/Web.bundle/src/index.html`. That step is deliberately not part of this repository.

## Android (optional second use)
`.github/workflows/android.yml` builds the same patches into an Android APK **without any secret**: Gradle's release signing needs a keystore, so the run makes a throwaway one and throws it away with the run. The result is a **base**: release `android-<run number>` (`SN-Fast-android-base.apk`, `.sha256`, `INFO.txt`) and the log on the branch `build-logs-android`. Re-sign it on your own computer with your own key before installing it, and write your own server address into it (the page that holds the two preset lines is `assets/Web.bundle/src/index.html` inside the APK); that script is not part of this repository. Do not install the base as it is: nothing could ever update it. It starts when you change `android.yml` or press Run workflow, not on every push (an iPhone-only push does not start it).

## If something goes wrong
Open `LATEST.txt` first: the first failed step is named in its first lines ("FAILURE at step 'archive'") and the first 40 error lines follow. Typical causes: a patch that no longer applies (step `prepare`), CocoaPods (step `bundle`),
Xcode / the scheme (step `archive`), a missing marker in the web bundle (step `package`: our patches are not inside, or the measuring hook is). Xcode 26 failing starts the Xcode 27 fallback job automatically.
