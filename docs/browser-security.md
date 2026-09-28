# Browser security

The VibeSorter browser is intended for local use. It can serve cached image files through its HTTP endpoints, so the default bind address is loopback (`127.0.0.1`).

The browser CLI rejects non-loopback hosts unless network exposure is explicitly requested:

    vibesorter-browser --host 0.0.0.0 --allow-network

Only use `--allow-network` on a trusted network and when exposing the indexed image library is intentional. There is no authentication layer on the local browser server.

For normal use, keep the default loopback binding.
