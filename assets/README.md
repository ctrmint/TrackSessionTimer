# Startup splash source

`startup_splash.gif` is the user-supplied source artwork from:

https://static.wixstatic.com/media/467f72_bdf20d6c823c42a18bc41c04e17e7345~mv2.gif

The runtime asset and preview are regenerated with:

```sh
python tools/convert_splash.py assets/startup_splash.gif startup_splash.rgb565 \
  --preview assets/startup_splash_preview.png
```
