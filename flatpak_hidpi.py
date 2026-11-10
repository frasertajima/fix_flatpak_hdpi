#!/usr/bin/env python3
"""flatpak_hidpi - give X11-only Flatpak apps a sane scale on a HiDPI Wayland desktop.

Many Flatpak apps (Synology Drive, older Qt/Java/Electron apps) only ship the X11 socket,
so on Wayland they run under XWayland, which does not pass the compositor's scale to the
app: tiny text on a 4K laptop panel. Most toolkits honour an environment variable that
scales fonts *and* widgets together. This script sets it as a per-user Flatpak override
(~/.local/share/flatpak/overrides/<app-id>), which also covers autostart entries.

Stdlib only. Commands:
  check APP            is this app a candidate? (X11-only, no Wayland socket)
  show  APP            print the current override for the app
  set   APP [--scale auto|N] [--var QT_SCALE_FACTOR] [--dry-run]
  reset APP [--var QT_SCALE_FACTOR]
"""
import argparse
import re
import subprocess
import sys

DEFAULT_VAR = "QT_SCALE_FACTOR"

# Logical monitor entry in Mutter's GetCurrentState reply:
#   (x, y, scale, uint32 transform, primary, [('eDP-1', 'vendor', 'product', 'serial')], {...})
_LOGICAL = re.compile(
    r"\(\s*-?\d+,\s*-?\d+,\s*([0-9.]+),\s*uint32 \d+,\s*(true|false),\s*\[\('")


def parse_mutter_scale(text):
    """Return the primary logical monitor's scale (else the first), or None."""
    found = [(float(m.group(1)), m.group(2) == "true") for m in _LOGICAL.finditer(text)]
    if not found:
        return None
    for scale, primary in found:
        if primary:
            return scale
    return found[0][0]


def detect_scale():
    out = subprocess.run(
        ["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.DisplayConfig",
         "--object-path", "/org/gnome/Mutter/DisplayConfig",
         "--method", "org.gnome.Mutter.DisplayConfig.GetCurrentState"],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return parse_mutter_scale(out.stdout)


def flatpak(*args, check=True):
    r = subprocess.run(["flatpak", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"flatpak {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r


def require_installed(app):
    if flatpak("info", app, check=False).returncode != 0:
        sys.exit(f"'{app}' is not an installed Flatpak app id. Try: flatpak list --app")


def sockets(app):
    perms = flatpak("info", "--show-permissions", app).stdout
    m = re.search(r"^sockets=(.*)$", perms, re.M)
    return set(m.group(1).split(";")) - {""} if m else set()


def cmd_check(a):
    require_installed(a.app)
    s = sockets(a.app)
    x11 = "x11" in s or "fallback-x11" in s
    wl = "wayland" in s
    print(f"{a.app} sockets: {', '.join(sorted(s)) or '(none)'}")
    if x11 and not wl:
        print("-> Candidate: X11-only, so it runs under XWayland and ignores the desktop scale.")
        print("   It must also use a toolkit that honours the variable (Qt: QT_SCALE_FACTOR).")
        print("   Verify by running `set` and looking at the app.")
    elif wl:
        print("-> Has the Wayland socket: it should already follow the desktop scale. "
              "Override probably not needed.")
    else:
        print("-> No display socket listed (headless or unusual); this script won't help.")


def cmd_show(a):
    require_installed(a.app)
    print(flatpak("override", "--user", "--show", a.app).stdout.strip() or "(no user override)")


def cmd_set(a):
    require_installed(a.app)
    if a.scale == "auto":
        scale = detect_scale()
        if scale is None:
            sys.exit("Could not read the scale from GNOME (Mutter). Pass --scale N explicitly.")
        print(f"Detected desktop scale: {scale:.4f}")
    else:
        try:
            scale = float(a.scale)
        except ValueError:
            sys.exit("--scale must be 'auto' or a number")
    if not 0.5 <= scale <= 8:
        sys.exit(f"Refusing implausible scale {scale}")
    value = f"{scale:.4f}".rstrip("0").rstrip(".")
    if a.var == "GDK_SCALE" and scale != int(scale):
        print("Warning: GDK_SCALE only accepts integers; the toolkit will likely ignore or round it.")
    cmd = ["override", "--user", f"--env={a.var}={value}", a.app]
    if a.dry_run:
        print("Would run: flatpak " + " ".join(cmd))
        return
    flatpak(*cmd)
    print(f"Set {a.var}={value} for {a.app}.")
    print(f"Restart the app to apply:  flatpak kill {a.app}  (then launch it again)")
    print(f"Undo:                      {sys.argv[0]} reset {a.app}")


def cmd_reset(a):
    require_installed(a.app)
    flatpak("override", "--user", f"--unset-env={a.var}", a.app)
    print(f"Removed {a.var} override for {a.app}. Restart the app.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("check", cmd_check), ("show", cmd_show), ("set", cmd_set), ("reset", cmd_reset)):
        sp = sub.add_parser(name)
        sp.add_argument("app", help="Flatpak app id, e.g. com.synology.SynologyDrive")
        sp.set_defaults(fn=fn)
        if name in ("set", "reset"):
            sp.add_argument("--var", default=DEFAULT_VAR, help=f"env var to set (default {DEFAULT_VAR})")
        if name == "set":
            sp.add_argument("--scale", default="auto", help="'auto' (read from GNOME) or a number")
            sp.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
