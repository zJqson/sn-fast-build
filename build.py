#!/usr/bin/env python3
"""build.py - fetch an upstream Standard Notes release and apply our small patches to it, for the phone builds of this repository.

  py -3 build.py prepare  --target ios|android [--dest DIR] [--tag TAG]
        fetch the upstream tag (shallow) and apply our patches with `git am --3way`; STOPS LOUDLY (exit 3) when a patch no longer applies, and says which one.
        Safe to run again: finished steps are skipped (state.json).
  py -3 build.py preset-mobile --dest DIR       write the sync server + websocket URL of config.ini [mobile] into the phone apps' start page (the hosted defaults here)
  py -3 build.py check-tags TAG [TAG ...]       only checks that every patch applies to each tag (scratch clone, nothing is built); exit 3 if one does not
  py -3 build.py probe-version --platform Mobile --version 3.203.0 --snjs 2.212.9
        one request WITHOUT any credential to the hosted server: does it accept the version header string of this build? (401 = yes)
  py -3 build.py cfg SECTION KEY                print one value of config.ini

Settings live in config.ini (read once per run, nothing polls). Every command it runs is logged with millisecond timestamps to logs.txt. Progress is saved after
every step (atomic write) so a crash / restart continues where it stopped. Stdlib only. Python 3.8+.
This is an unofficial personal build recipe. It is not affiliated with Standard Notes or Proton. Upstream is AGPL-3.0; so are the patches (see LICENSE).
"""
import argparse
import configparser
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logs.txt")
STATE = os.path.join(HERE, "state.json")
CONFIG = os.path.join(HERE, "config.ini")


# ----------------------------------------------------------------------------------------------- logging / state
def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log(msg):
    line = "%s %s" % (now(), msg)
    print(line, file=sys.stderr, flush=True)   # stderr: stdout stays clean for `cfg` and `prepare` results
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def die(code, msg):
    log("STOP: " + msg)
    print("\n" + "=" * 78 + "\n" + msg + "\n" + "=" * 78, file=sys.stderr)
    sys.exit(code)


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(st):
    """Atomic: write a temp file, flush it to disk, then replace. A crash in the middle cannot corrupt state.json."""
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)


def cfg():
    c = configparser.ConfigParser(inline_comment_prefixes=("#",))
    if not c.read(CONFIG, encoding="utf-8"):
        die(2, "config.ini not found next to build.py")
    return c


def run(cmd, cwd=None, env=None, check=True, capture=False, shell=False):
    t0 = time.time()
    shown = cmd if isinstance(cmd, str) else " ".join(cmd)
    log("RUN  %s%s" % (shown, "   (in %s)" % cwd if cwd else ""))
    p = subprocess.run(cmd, cwd=cwd, env=env, shell=shell, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.STDOUT if capture else None, universal_newlines=True)
    log("DONE exit=%s in %.1fs" % (p.returncode, time.time() - t0))
    if check and p.returncode != 0:
        die(4, "command failed (exit %s): %s" % (p.returncode, shown))
    return p


def git(args, cwd, check=True, capture=True):
    p = run(["git"] + args, cwd=cwd, check=check, capture=capture)
    return (p.stdout or "").strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------- prepare
# which patch folders (keys of [patches] in config.ini) each target gets, in this order
TARGET_FOLDERS = {
    "android": ["common", "mobile", "android", "customserver"],
    "ios": ["common", "mobile", "ios", "customserver"],
}


def patch_files(c, target):
    keys = list(TARGET_FOLDERS[target])
    if c["patches"].get("apply_optional", "no").strip().lower() in ("yes", "true", "1"):
        keys.append("optional")
    out = []
    for key in keys:
        folder = c["patches"].get(key)
        if folder:
            out += sorted(glob.glob(os.path.join(HERE, folder, "*.patch")))
    return out


def prepare(target, dest, tag, reuse=True):
    c = cfg()
    tag = tag or c["upstream"]["tag"]
    repo = c["upstream"]["repo"]
    patches = patch_files(c, target)
    if not patches:
        die(2, "no patches found for target %s (check [patches] in config.ini)" % target)
    # the folder is part of the key: "already prepared" is a fact about ONE folder
    key = "prepare:%s:%s:%s:%s" % (target, tag, os.path.abspath(dest).lower(), hashlib.sha256("".join(sha256_file(p) for p in patches).encode()).hexdigest()[:16])
    st = load_state()
    if reuse and st.get(key, {}).get("done") and os.path.exists(os.path.join(dest, ".git")):
        if git(["rev-parse", "HEAD"], dest, check=False) == st[key].get("head"):
            log("prepare %s: already done for this tag and these patches, continuing (%s)" % (target, dest))
            return st[key]
        log("prepare %s: %s is not at the prepared commit any more: preparing again" % (target, dest))
    if os.path.exists(os.path.join(dest, ".git")):
        log("prepare: %s exists; resetting it to the tag" % dest)
        git(["fetch", "--depth", "1", "origin", "tag", tag], dest, check=False)
        git(["reset", "-q", "--hard"], dest, check=False)
        git(["checkout", "-q", "--detach", tag], dest)
        git(["reset", "-q", "--hard", tag], dest)
    else:
        if os.path.exists(dest) and os.listdir(dest):
            die(2, "%s exists and is not an empty git checkout; give another --dest" % dest)
        # -c core.autocrlf=false: check files out byte for byte (like the Linux runners), so patches apply exactly
        run(["git", "clone", "-c", "core.autocrlf=false", "--depth", "1", "--branch", tag, repo, dest])
    git(["config", "user.name", "SN Fast Sync"], dest)
    git(["config", "user.email", "snfast@localhost.invalid"], dest)
    git(["config", "core.autocrlf", "false"], dest)
    sha = git(["rev-parse", "HEAD"], dest)
    log("upstream %s = commit %s" % (tag, sha))
    git(["checkout", "-q", "-B", "snfast-%s-%s" % (target, sha[:7])], dest)
    applied = []
    for p in patches:
        r = run(["git", "am", "--3way", "--quiet", p], cwd=dest, check=False, capture=True)
        if r.returncode != 0:
            run(["git", "am", "--abort"], cwd=dest, check=False, capture=True)
            die(3, "PATCH DOES NOT APPLY ANY MORE\n  patch:    %s\n  upstream: %s (%s)\n"
                   "  git said: %s\n"
                   "  What to do: rebase that one patch onto the new upstream code (open the file it touches, redo the\n"
                   "  same small change, `git format-patch`), put the new patch in the patches folder, run again.\n"
                   "  Nothing was built." % (os.path.basename(p), tag, sha[:10], (r.stdout or "").strip()[-600:]))
        applied.append({"patch": os.path.relpath(p, HERE).replace("\\", "/"), "sha256": sha256_file(p)})
        log("applied %s" % os.path.basename(p))
    ver, snjs = "", ""
    for rel, name in (("packages/web/package.json", "ver"), ("packages/snjs/package.json", "snjs")):
        try:
            with open(os.path.join(dest, *rel.split("/")), encoding="utf-8") as f:
                v = json.load(f).get("version", "")
        except (OSError, ValueError):
            v = ""
        if name == "ver":
            ver = v
        else:
            snjs = v
    info = {"target": target, "tag": tag, "upstream_commit": sha, "upstream_version": ver, "snjs_version": snjs,
            "head": git(["rev-parse", "HEAD"], dest), "patches": applied, "done": True, "when": now()}
    st = load_state()
    st[key] = info
    save_state(st)
    with open(os.path.join(dest, "snfast-build-info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    log("prepare %s OK: %d patches on %s (version %s)" % (target, len(applied), sha[:10], ver))
    return info


# ------------------------------------------------------------------------------------------------- URL presets
def preset_mobile(dest):
    """Writes the sync server URL and the websocket URL of config.ini [mobile] into the phone apps' start page (packages/mobile/html/Web.bundle/src/index.html).
    Here they are the HOSTED defaults; a private server address is written into the finished app locally afterwards (personalize_ipa.py / personalize_apk.py)."""
    c = cfg()
    m = c["mobile"] if "mobile" in c else {}
    sync = m.get("default_sync_server", "https://api.standardnotes.com").strip()
    ws = m.get("websocket_url", "wss://sockets.standardnotes.com").strip()
    if not sync.startswith(("http://", "https://")) or not ws.startswith(("ws://", "wss://")) or '"' in sync + ws:
        die(2, "config.ini [mobile]: default_sync_server must start with http(s):// and websocket_url with ws(s)://, no quotes")
    page = os.path.join(dest, "packages", "mobile", "html", "Web.bundle", "src", "index.html")
    with open(page, "rb") as f:
        data = f.read().decode("utf-8")
    for var, value in (("defaultSyncServer", sync), ("websocketUrl", ws)):
        pat = re.compile(r'(window\.%s = ")[^"]*(";)' % var)
        if len(pat.findall(data)) != 1:
            die(3, "preset-mobile: expected exactly one window.%s line in %s (did upstream change its start page?)" % (var, page))
        data = pat.sub(lambda mo: mo.group(1) + value + mo.group(2), data)
    with open(page, "wb") as f:
        f.write(data.encode("utf-8"))
    line = "presets         : default sync server %s, websocket URL %s" % (sync, ws)
    log("preset-mobile: " + line)
    info_path = os.path.join(dest, "snfast-build-info.json")
    try:
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
        info["presets"] = {"default_sync_server": sync, "websocket_url": ws}
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
    except (OSError, ValueError):
        pass
    return line


def check_tags(tags):
    bad = []
    for tag in tags:
        d = os.path.join(os.environ.get("SNF_SCRATCH", os.path.join(HERE, ".scratch")), "check-" + hashlib.sha1(tag.encode()).hexdigest()[:8])
        if os.path.isdir(d):   # never delete for good: move an old scratch clone aside
            os.replace(d, d + ".old-" + time.strftime("%Y%m%d-%H%M%S"))
        for target in ("android", "ios"):
            try:
                prepare(target, d, tag, reuse=False)   # prepare() resets the one clone to the tag before every target
            except SystemExit as e:
                if e.code == 3:
                    bad.append((tag, target))
                else:
                    raise
    if bad:
        die(3, "patches do not apply to: " + ", ".join("%s (%s)" % b for b in bad))
    log("check-tags OK: every patch applies to " + ", ".join(tags))


# ------------------------------------------------------------------------------------------ version header probe
def probe_version(platform, version, snjs_version):
    """Asks the REAL sync server, without any credentials, whether it accepts the headers a build sends:
    X-Application-Version: <Platform>-<version>  (Mobile-3.203.0) together with X-SNJS-Version: <snjs version of the build> (the gate needs both).
    The hosted server answers 401 (accepted, wants a login) for a plain x.y.z and HTTP 400 "client version is no longer supported" for anything else,
    for example 3.203.0-fastsync. Sends no token, no account, no note: one POST with an empty body to the sockets-token endpoint."""
    import urllib.error
    import urllib.request
    header = "%s-%s" % (platform, version)
    req = urllib.request.Request("https://api.standardnotes.com/v1/sockets/tokens", data=b"{}", method="POST",
                                 headers={"X-Application-Version": header, "X-SNJS-Version": snjs_version,
                                          "Content-Type": "application/json", "User-Agent": "snfast-version-probe"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except OSError as e:
        log("probe: network error %s" % e)
        return -1
    log("probe: X-Application-Version '%s' + X-SNJS-Version '%s' -> HTTP %s (401 = accepted, 400 = refused)" % (header, snjs_version, code))
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--target", required=True, choices=sorted(TARGET_FOLDERS))
    p.add_argument("--dest", default=None)
    p.add_argument("--tag", default=None)
    p = sub.add_parser("preset-mobile")
    p.add_argument("--dest", required=True)
    p = sub.add_parser("check-tags")
    p.add_argument("tags", nargs="+")
    p = sub.add_parser("cfg")
    p.add_argument("section")
    p.add_argument("key")
    p = sub.add_parser("probe-version")
    p.add_argument("--platform", required=True, choices=["Desktop", "Mobile", "Web"])
    p.add_argument("--version", required=True)
    p.add_argument("--snjs", required=True, help="the snjs version of the build (packages/snjs/package.json)")
    a = ap.parse_args()
    if a.cmd != "cfg":
        log("build.py %s" % " ".join(sys.argv[1:]))
    c = cfg()
    if a.cmd == "cfg":
        print(c[a.section][a.key])
    elif a.cmd == "prepare":
        dest = os.path.abspath(a.dest or os.path.join(HERE, "work", "upstream-" + a.target))
        info = prepare(a.target, dest, a.tag)
        print(json.dumps({k: info[k] for k in ("tag", "upstream_commit", "upstream_version", "snjs_version", "head")}))
    elif a.cmd == "check-tags":
        check_tags(a.tags)
    elif a.cmd == "preset-mobile":
        print(preset_mobile(os.path.abspath(a.dest)))
    elif a.cmd == "probe-version":
        code = probe_version(a.platform, a.version, a.snjs)
        print(code)
        sys.exit(0 if code == 401 else 5)


if __name__ == "__main__":
    main()
