import os
from pydub import AudioSegment
import sys
import os
import argparse
from collections import OrderedDict
import shutil
from pathlib import Path


def to_bids_audio(audio_list):
    for file_path in audio_list:
        record_id = file_path.split("/")[1]
        session = file_path.split("/")[2]
        destination_directory = f"""peds_audio/{record_id}/{session}1/audio/"""
        os.makedirs(destination_directory, exist_ok=True)
        if os.path.exists(file_path):
            shutil.copy(file_path, destination_directory)
        else:
            print(f'File not found: {file_path}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    # string param of path to folder containing reproschema files
    parser.add_argument("audio_dir",
                        type=str,
                        help="path to folder containing audio files")

    args = parser.parse_args()

    audio_folder = Path(args.audio_dir)
    if not os.path.isdir(audio_folder):
        raise FileNotFoundError(
            f"{audio_folder} does not exist. Please check if folder exists and is located at the correct directory"
        )

    audio_list = []
    for file in audio_folder.glob("**/*"):
        if file.is_file() and str(file).endswith(".wav"):
            audio_list.append(str(file))
    to_bids_audio(audio_list)
