"""Memory-efficient loading of the startup splash framebuffer."""


SPLASH_FILE = "startup_splash.rgb565"
READ_CHUNK_BYTES = 2048


def load_splash(surface, path=SPLASH_FILE):
    """Load an RGB565 image into an existing framebuffer without duplicating it."""
    buffer = surface.buffer
    expected_size = len(buffer)

    try:
        with open(path, "rb") as splash_file:
            splash_file.seek(0, 2)
            if splash_file.tell() != expected_size:
                return False
            splash_file.seek(0)

            target = memoryview(buffer)
            offset = 0
            while offset < expected_size:
                end = min(offset + READ_CHUNK_BYTES, expected_size)
                bytes_read = splash_file.readinto(target[offset:end])
                if not bytes_read:
                    return False
                offset += bytes_read
    except OSError:
        return False

    return True
