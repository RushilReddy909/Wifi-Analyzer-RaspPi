import time
import shutil
from pathlib import Path

SOURCE = Path("/home/rushi/wifi-collector")
DEST = Path("/home/rushi/wifi-heatmap-dashboard/data")

print("📡 Auto-mover started...")
print("Watching:", SOURCE)
print("Moving to:", DEST)

already_moved = set()

while True:
    for file in SOURCE.glob("*.csv"):
        dest_file = DEST / file.name

        if file.name not in already_moved:
            print(f"Moving {file.name} -> {DEST}")
            shutil.move(str(file), str(dest_file))
            already_moved.add(file.name)

    time.sleep(5)
