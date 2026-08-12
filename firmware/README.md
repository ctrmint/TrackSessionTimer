# Device firmware

This directory is the complete MicroPython filesystem payload for Track Session Timer.

The source is intentionally flat **inside this directory** because the supported device loads `main.py` and its sibling modules from the MicroPython filesystem root. The repository deployment tool copies these files to that root without installing a `firmware` package or changing runtime imports.

- `main.py` is the device entry point and is uploaded last.
- `params.json` contains system-owned defaults and release metadata.
- `user.json` is an example for fresh installations; upgrades preserve the copy already stored on the device.
- `font_data*.bin` and `startup_splash.rgb565` are runtime assets, not source-code modules.

From the repository root, deploy while preserving existing user settings with:

```sh
python tools/deploy.py
```

Use `python tools/deploy.py --help` for explicit serial-port, fresh-install, and dry-run options.
