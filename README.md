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
Flatpak is modified.

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

## Apps that autostart at login

The override is applied when the app is launched, but an app launched by GNOME autostart can
still come up small. On the test machine (GNOME 49 / Fedora Silverblue 45), autostart starts the
app within about a second of the session starting. At that moment the X server had **no
`Xft.dpi` set yet** (it appeared about 20 seconds later, as 192), so the app started before the
desktop had published its DPI. The same app started by hand a minute later was fine.

- `X-GNOME-Autostart-Delay=` in the `.desktop` file did **not** help here; it was ignored.
- What worked: point the autostart entry's `Exec=` at a small wrapper that sleeps, then `exec`s the
  normal `flatpak run ...` command:

```sh
#!/bin/sh
sleep 20
exec /usr/bin/flatpak run --branch=stable --arch=x86_64 --command=synology-drive com.synology.SynologyDrive start
```

  Use the app's original `Exec=` line after `exec`; copy it from
  `~/.config/autostart/<app-id>.desktop`. Keep a copy of the original `.desktop` file.
- The app's tray icon appears late and may change a second time as it finishes starting. That is
  normal for this setup, not a sign it failed.

The 20-second figure is not tuned. A shorter sleep may work, so adjust it for your machine.

## Limitations

- The scale is global for the app. On a mixed-DPI setup (for example a 1x external monitor), the
  app will look too large there.
- The scale is read once when you run `set`. If you later change the desktop scale, run `set` again.
- Autostart timing: see the section above; the override alone may not be enough at login.
- Not for the GRUB boot menu. That's a different mechanism (GRUB's own `gfxmode` and font settings).

## Tests

`python3 -m unittest discover -s tests` checks the Mutter output parser with no Flatpak or GNOME needed.

## License

GPLv3 (see LICENSE)
