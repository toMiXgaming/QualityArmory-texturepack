# LightAPI 5.3.0 – port for Paper 1.21.4

Port of [BeYkeRYkt/LightAPI](https://github.com/BeYkeRYkt/LightAPI) (MIT, see `LICENSE`) to Paper 1.21.4.

- New module `craftbukkit-nms-v1_21_R3`: handler for Paper's built-in Starlight (Moonrise), Mojang-mapped.
- `HandlerFactory` picks the handler from the Minecraft version, because Paper no longer relocates CraftBukkit.
- bStats metrics removed. Paper only (not Spigot).
- For plugins using the old `ru.beykerykt.lightapi` API (e.g. QualityArmory) set `force-enable-legacy: true`
  in `plugins/LightAPI/config.yml`.

Build: start a Paper 1.21.4 server once in a directory, then `PAPER_DIR=<that dir> ./build.sh`.
Output: `build/LightAPI-5.3.0-paper-1.21.4.jar`.

Tested on a real Paper 1.21.4 build 232: createLight raised block light 0 -> 15 and it spread to neighbours,
deleteLight set it back to 0. Not tested with a connected client (packet display).
