# LanguageSwapper: Default English Audio Fixer for MKV Libraries

This tool scans a video library for `.mkv` files with multiple audio tracks and automatically **sets English as the default audio** when it's safe to do so.

It uses `ffprobe` and `mkvmerge` to detect and remux files where:

* There are multiple audio tracks
* English is present
* English is **not currently the default**
* There is **only one English track**

If these conditions are met, the file is:

1. Renamed to a backup `.bak` file
2. Remuxed using `mkvmerge` with English as the default audio
3. If successful, the new file replaces the original
4. If unsuccessful, the original is restored and the failed file is deleted

---

## ✅ Features

* 🔍 Deep recursive folder scan
* 🎯 Only updates `.mkv` files with exactly **one English audio track**
* 🚫 Skips and logs:

  * Files with multiple English tracks
  * Non-MKV files
* 📁 Generates success and warning logs
* 🔒 Safe: original files are backed up before editing

---

## ⚙️ Requirements

### Python 3.9 or later

Install Python and set up the environment:

```bash
sudo apt install python3 python3-venv python3-pip
```

In your project directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install tqdm
```

### External Tools Required

Make sure the following tools are installed and available in your `$PATH`:

* [`ffprobe`](https://ffmpeg.org/ffprobe.html) (comes with `ffmpeg`)
* [`mkvmerge`](https://mkvtoolnix.download/)
* \[`mkvinfo`]\(optional, for verification)
* \[`jq`]\(optional, for JSON formatting)

Ubuntu install:

```bash
sudo apt install ffmpeg mkvtoolnix mkvtoolnix-gui jq
```

---

## Usage

```bash
python swap.py
```

You'll be prompted for a folder path:

```bash
Enter the folder path to scan: /your/media/folder
```

The script will process `.mkv` files recursively under that folder.

---

## Output

* `success-YYYYMMDD-HHMMSS.json` – files successfully updated
* `warnings-YYYYMMDD-HHMMSS.json` – skipped files with reasons

Example reasons:

* Not MKV - cannot safely edit defaults
* Multiple English audio tracks - manual review needed
* English track already default
* Failed to remux

---

## Verifying Results

### With ffprobe:

```bash
ffprobe -v error -select_streams a \
  -show_entries stream=index:stream_tags=language,disposition \
  -of json "file.mkv"
```

Look for:

```json
"disposition": {
  "default": 1
}
```

on the English audio track.

### With mkvmerge:

```bash
mkvmerge -i -F json "file.mkv" | jq
```

Check for:

```json
"default_track": true
```

on the English audio entry.

---

## License

MIT License — free to use, modify, and distribute.

---

## Acknowledgements

* Built with Python, FFmpeg, and MKVToolNix
* Inspired by many hours of manually switching audio tracks 😅

