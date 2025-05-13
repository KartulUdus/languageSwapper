import os
import subprocess
import json
from datetime import datetime
from tqdm import tqdm

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".mov", ".avi", ".m4v")

def find_video_files(root_folder):
    for root, _, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                yield os.path.join(root, file)

def probe_audio_tracks(file_path):
    # ffprobe for language and default
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index,language,disposition:stream_tags=language",
        "-of", "json",
        file_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError:
        return []

    return data.get("streams", [])

def get_audio_track_ids(file_path):
    """
    Returns a list of dicts:
    [
        { "audio_index": 0, "track_id": 1 },
        { "audio_index": 1, "track_id": 2 },
    ]
    """
    cmd = ["mkvmerge", "--identify", "--verbose", file_path]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError:
        return []

    lines = result.stdout.splitlines()

    track_list = []
    audio_idx = 0
    for line in lines:
        if "Track ID" in line and "audio" in line:
            parts = line.strip().split()
            track_id = None
            for i, p in enumerate(parts):
                if p == "ID":
                    track_id = int(parts[i + 1].rstrip(":"))
                    break
            if track_id is not None:
                track_list.append({"audio_index": audio_idx, "track_id": track_id})
                audio_idx += 1

    return track_list

def set_default_audio_mkv_by_remux(video_path, track_id_to_set, all_track_ids):
    try:
        dir_name = os.path.dirname(video_path)
        base_name = os.path.basename(video_path)
        tmp_original = os.path.join(dir_name, base_name + ".bak")
        tmp_new = os.path.join(dir_name, ".__temp__.mkv")

        # Rename the original file
        os.rename(video_path, tmp_original)

        # Order audio tracks with the default track first
        audio_tracks_order = [track_id_to_set] + [tid for tid in all_track_ids if tid != track_id_to_set]

        # Build mkvmerge command
        cmd = [
            "mkvmerge",
            "--output", tmp_new,
            "--audio-tracks", ",".join(str(tid) for tid in audio_tracks_order),
        ]

        for tid in audio_tracks_order:
            if tid == track_id_to_set:
                cmd += ["--default-track", f"{tid}:yes"]
            else:
                cmd += ["--default-track", f"{tid}:no"]

        cmd.append(tmp_original)

        subprocess.run(cmd, check=True)

        # Replace the original with the fixed file
        os.rename(tmp_new, video_path)
        os.remove(tmp_original)
        return True

    except Exception as e:
        print(f"Remuxing failed for {video_path}: {e}")
        # Cleanup any partial files
        if os.path.exists(tmp_new):
            os.remove(tmp_new)
        if os.path.exists(tmp_original):
            os.rename(tmp_original, video_path)
        return False


def main():
    folder = input("Enter the folder path to scan: ").strip()

    video_files = list(find_video_files(folder))
    print(f"Found {len(video_files)} video files.\n")

    successes = []
    warnings = []

    for video in tqdm(video_files, desc="Scanning & fixing files"):
        streams = probe_audio_tracks(video)

        if len(streams) <= 1:
            continue

        # Build audio track info
        tracks = []
        for idx, s in enumerate(streams):
            language = (
                s.get("tags", {}).get("language") or
                s.get("language") or
                "und"
            ).lower()

            is_default = s.get("disposition", {}).get("default", 0) == 1

            tracks.append({
                "audio_index": idx,
                "language": language,
                "default": is_default
            })

        english_tracks = [t for t in tracks if t["language"] == "eng"]

        if not english_tracks:
            continue

        if not video.lower().endswith(".mkv"):
            warnings.append({
                "file": video,
                "reason": "Not MKV - cannot safely edit defaults"
            })
            continue

        if len(english_tracks) > 1:
            warnings.append({
                "file": video,
                "reason": "Multiple English audio tracks - manual review needed"
            })
            continue

        english_track = english_tracks[0]

        if english_track["default"]:
            continue  # Already default

        # Get mkvmerge track IDs
        track_id_list = get_audio_track_ids(video)

        # Map ffprobe index to mkvmerge track ID
        audio_index = english_track["audio_index"]
        track_id = None
        for track in track_id_list:
            if track["audio_index"] == audio_index:
                track_id = track["track_id"]
                break

        if track_id is None:
            warnings.append({
                "file": video,
                "reason": "Could not determine mkvmerge track ID for English track"
            })
            continue

        all_ids = [t["track_id"] for t in track_id_list]

        success = set_default_audio_mkv_by_remux(video, track_id, all_ids)

        if success:
            successes.append({
                "file": video,
                "track_id": track_id,
                "action": "Set English track as default"
            })
        else:
            warnings.append({
                "file": video,
                "reason": "Failed to set default track"
            })

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    success_filename = f"success-{timestamp}.json"
    with open(success_filename, "w", encoding="utf-8") as f:
        json.dump(successes, f, indent=2)
    print(f"\n✅ Updated {len(successes)} files. Details in {success_filename}")

    warning_filename = f"warnings-{timestamp}.json"
    with open(warning_filename, "w", encoding="utf-8") as f:
        json.dump(warnings, f, indent=2)
    print(f"⚠️  Logged {len(warnings)} warnings. Details in {warning_filename}")

if __name__ == "__main__":
    main()

