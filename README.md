# flatpak_hidpi

Fix tiny text in X11-only Flatpak apps on a HiDPI Wayland desktop (GNOME).

Originally written for **Synology Drive Client**, whose Flatpak is unreadable on a 4K laptop
panel at 1.67x scale. After the fix the text is readable and sharp, with no blur.

```
./flatpak_hidpi.py check com.synology.SynologyDrive   # is it a candidate?
./flatpak_hidpi.py set   com.synology.SynologyDrive   # scale = whatever GNOME is using
flatpak kill com.synology.SynologyDrive               # restart the app to apply
./flatpak_hidpi.py reset com.synology.SynologyDrive   # undo
```

Python 3 standard library only. `set --scale 1.5` overrides auto-detection; `--dry-run` shows
the command without running it.

## Why it happens

The Flatpak only has the `x11` socket, so on Wayland it runs under XWayland. XWayland does not
hand the compositor's scale to the app, so the app draws at 1x and its fixed-pixel fonts are tiny.
Qt reads `QT_SCALE_FACTOR` and scales fonts and widgets together. The script sets that as a
per-user Flatpak override (`flatpak override --user --env=...`). Nothing inside the app or the
Flatpak is modified, and the override also applies to autostart entries.

## Will it work for my app?

Both must be true:

1. **X11-only.** `./flatpak_hidpi.py check <app-id>` reports this. If the app already has the
   `wayland` socket it should follow the desktop scale and doesn't need this.
2. **The toolkit honours a scale variable.** The script can't detect this. Qt does
   (`QT_SCALE_FACTOR`, fractional values work). Try it and look at the app.

To try another toolkit, pass the variable name:

```
./flatpak_hidpi.py set org.example.App --var GDK_SCALE --scale 2
```

Only the Qt case (`QT_SCALE_FACTOR`) has been tested, on Synology Drive 4.2.0. Other toolkits
are untested guesses. Notes: `GDK_SCALE` accepts integers only, and Electron apps usually want a
command-line flag (`--force-device-scale-factor`), which an environment variable can't provide.

## Adapting for a different app

1. Find the id: `flatpak list --app`.
2. `./flatpak_hidpi.py check <id>`. Proceed only if it says "Candidate".
3. `./flatpak_hidpi.py set <id>`, restart the app (`flatpak kill <id>`), look at it.
4. If it's too big or small, use `set <id> --scale N`. If nothing changes, the toolkit ignores
   the variable. `reset <id>` removes the override.

Auto-detection reads the primary monitor's scale from GNOME's Mutter D-Bus API
(`org.gnome.Mutter.DisplayConfig`), so it's GNOME-only. On other desktops use `--scale N`.
Overrides live in `~/.local/share/flatpak/overrides/<app-id>`.

## Limitations

- The scale is global for the app. On a mixed-DPI setup (for example a 1x external monitor), the
  app will look too large there.
- The scale is read once when you run `set`. If you later change the desktop scale, run `set` again.
- Not for the GRUB boot menu. That's a different mechanism (GRUB's own `gfxmode` and font settings).

## Tests

`python3 -m unittest discover -s tests` checks the Mutter output parser with no Flatpak or GNOME needed.

## License

MIT
