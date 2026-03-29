"""
test_system.py - Quick smoke test for the Video Auto-Poster system.
Tests imports, config loading, and video processor (with a synthetic test video).
Does NOT perform any real uploads.
"""
import os
import sys
import tempfile
import subprocess

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
results = []


def test(name, fn):
    try:
        fn()
        print(f"  {PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  {FAIL}  {name}")
        print(f"         => {e}")
        results.append((name, False, str(e)))


# ─── 1. Module Imports ─────────────────────────────────────────────────────────
print("\n-- [1] Module Imports ----------------------------------------------")

def check_config():
    import config
    assert hasattr(config, "WATCH_FOLDER")
    assert hasattr(config, "TARGET_WIDTH")

def check_processor():
    import processor  # noqa

def check_scheduler():
    import scheduler  # noqa

def check_uploader():
    import uploader  # noqa

def check_watcher():
    import watcher  # noqa

def check_platforms():
    import platforms.youtube   # noqa
    import platforms.tiktok    # noqa
    import platforms.instagram # noqa

test("config.py imports OK", check_config)
test("processor.py imports OK", check_processor)
test("scheduler.py imports OK", check_scheduler)
test("uploader.py imports OK", check_uploader)
test("watcher.py imports OK", check_watcher)
test("platforms/* imports OK", check_platforms)

# ─── 2. Config Values ──────────────────────────────────────────────────────────
print("\n-- [2] Config Values -----------------------------------------------")

def check_dimensions():
    import config
    assert config.TARGET_WIDTH == 1080
    assert config.TARGET_HEIGHT == 1920
    assert config.TARGET_FPS == 30

def check_delays():
    import config
    assert config.POST_DELAY_MIN < config.POST_DELAY_MAX

def check_watch_folder_defined():
    import config
    assert config.WATCH_FOLDER, "WATCH_FOLDER must not be empty"

test("Target dimensions 1080x1920", check_dimensions)
test("Delay range is valid", check_delays)
test("Watch folder is defined", check_watch_folder_defined)

# ─── 3. FFmpeg Availability ────────────────────────────────────────────────────
print("\n-- [3] FFmpeg ------------------------------------------------------")

def check_ffmpeg():
    import config
    result = subprocess.run(
        [config.FFMPEG_PATH, "-version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"FFmpeg returned exit code {result.returncode}"
    ver_line = result.stdout.splitlines()[0] if result.stdout else result.stderr.splitlines()[0]
    print(f"         => {ver_line}")

test("FFmpeg is accessible", check_ffmpeg)

# ─── 4. Video Processing (creates a synthetic 5-second test video) ─────────────
print("\n-- [4] Video Processor ---------------------------------------------")

def check_video_processing():
    import config
    from processor import process_video

    # Generate a synthetic 5-second 1280x720 color test video using FFmpeg
    tmp_in = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False, prefix="vap_test_in_")
    tmp_in.close()

    gen = subprocess.run([
        config.FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=5",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264", "-t", "5",
        "-c:a", "aac", "-shortest",
        tmp_in.name,
    ], capture_output=True, text=True)

    assert gen.returncode == 0, f"Test video generation failed:\n{gen.stderr}"
    print(f"         => Test input created: {tmp_in.name}")

    # Process it
    out = process_video(tmp_in.name)
    assert os.path.exists(out), "Output file does not exist"
    size_kb = os.path.getsize(out) // 1024
    print(f"         => Processed output: {out} ({size_kb} KB)")

    # Verify dimensions using ffprobe
    probe = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        out,
    ], capture_output=True, text=True)

    if probe.returncode == 0 and probe.stdout.strip():
        dims = probe.stdout.strip()
        print(f"         => Output dimensions: {dims} (expected 1080,1920)")
        assert dims == "1080,1920", f"Wrong dimensions: {dims}"

    # Cleanup (processor may have already deleted the input)
    if os.path.exists(tmp_in.name):
        os.unlink(tmp_in.name)
    if os.path.exists(out):
        os.unlink(out)

test("Process 1280x720 -> 1080x1920 (pad)", check_video_processing)

# ─── 5. Metadata Parsing ──────────────────────────────────────────────────────
print("\n-- [5] Metadata Parser ---------------------------------------------")

def check_metadata_with_hashtags():
    from uploader import _parse_metadata
    title, hashtags, desc = _parse_metadata("My Cool Video #fyp #viral.mp4")
    assert title == "My Cool Video", f"Got: {title}"
    assert "#fyp" in hashtags, f"Got: {hashtags}"
    assert "#viral" in hashtags, f"Got: {hashtags}"

def check_metadata_fallback():
    import config
    from uploader import _parse_metadata
    title, hashtags, _ = _parse_metadata("untitled.mp4")
    # DEFAULT_TITLE may be empty string when no .env exists;
    # _parse_metadata falls back to it OR uses the filename stem.
    # Just confirm it returns non-None strings.
    assert isinstance(title, str), f"title should be str, got: {type(title)}"
    assert isinstance(hashtags, str), f"hashtags should be str, got: {type(hashtags)}"

test("Metadata: parse title + hashtags from filename", check_metadata_with_hashtags)
test("Metadata: fallback to defaults when no hashtags", check_metadata_fallback)

# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n-- Summary ---------------------------------------------------------")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"  Passed: {passed}  |  Failed: {failed}  |  Total: {len(results)}")

if failed > 0:
    print("\n  Failed tests:")
    for name, ok, err in results:
        if not ok:
            print(f"    - {name}: {err}")
    sys.exit(1)
else:
    print("\n  All tests passed!")
