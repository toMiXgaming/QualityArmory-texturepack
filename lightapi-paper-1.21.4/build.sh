#!/bin/bash
# Builds LightAPI for Paper 1.21.4 without Maven.
# Usage: PAPER_DIR=/path/to/paper/server ./build.sh   (server dir must have been started once, so that
# versions/1.21.4/paper-1.21.4.jar and libraries/ exist)
set -e
cd "$(dirname "$0")"
PAPER_DIR=${PAPER_DIR:?set PAPER_DIR to a Paper 1.21.4 server directory}
CP="$PAPER_DIR/versions/1.21.4/paper-1.21.4.jar:$(find "$PAPER_DIR/libraries" -name '*.jar' | tr '\n' ':')"
rm -rf build && mkdir -p build/classes
find common bukkit-common bukkit-backward-support craftbukkit-common craftbukkit-nms-v1_21_R3 -name '*.java' > build/sources.txt
javac -nowarn --release 21 -encoding UTF-8 -cp "$CP" -d build/classes @build/sources.txt
cp -r bukkit-common/src/main/resources/* build/classes/
sed -i 's/^version: .*/version: 5.3.0-paper1.21.4/; s/^api-version: .*/api-version: "1.21"/' build/classes/plugin.yml
# tells Paper the jar already uses Mojang mappings, so it must not be remapped from Spigot mappings
printf "Manifest-Version: 1.0\npaperweight-mappings-namespace: mojang\n" > build/MANIFEST.MF
jar cfm build/LightAPI-5.3.0-paper-1.21.4.jar build/MANIFEST.MF -C build/classes .
echo "Built build/LightAPI-5.3.0-paper-1.21.4.jar"
