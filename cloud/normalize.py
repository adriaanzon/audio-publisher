import subprocess
from os.path import basename, splitext
from pathlib import Path


def normalize(recording: Path) -> Path:
    # target location should be a mounted cloud storage
    target_location = Path("var/" + splitext(basename(recording))[0] + ".mp3")

    subprocess.run(
        [
            "ffmpeg",
            "-i",
            recording,
            # Normalize loudness to -16dB LUFS and remove long silences
            "-af",
            "loudnorm=I=-16,silenceremove=stop_periods=-1:stop_duration=10:stop_threshold=-50dB",
            target_location,
        ]
    )

    return target_location
