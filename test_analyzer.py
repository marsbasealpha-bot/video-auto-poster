r"""
test_analyzer.py - CLI test script for the standalone video/image analyzer.

Usage:
    python test_analyzer.py <path_to_video_or_image>

Example:
    python test_analyzer.py C:/Users/Admin/Desktop/my_video.mp4
"""
import sys
import os
import json
import logging

# Set up logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_analyzer.py <path_to_video_or_image>")
        print("\nSupported formats:")
        print("  Video: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v")
        print("  Image: .jpg, .jpeg, .png, .gif, .bmp, .webp")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Video Analyzer - Test Run")
    print(f"{'='*60}")
    print(f"  Input: {file_path}")
    print(f"  Size:  {os.path.getsize(file_path) / (1024*1024):.1f} MB")
    print(f"{'='*60}\n")

    from analyzer import analyze_media

    try:
        result = analyze_media(file_path)

        print(f"\n{'='*60}")
        print(f"  [OK] ANALYSIS COMPLETE")
        print(f"{'='*60}\n")

        print(f"  Title:       {result['title']}")
        print(f"  Description: {result['description']}")
        print(f"  Hashtags:    {result['hashtags']}")
        print(f"  Mentions:    {result['mentions']}")
        print(f"  Thumb Prompt:{result['thumbnail_prompt'][:80]}...")
        print(f"\n  Output Folder: {result['output_folder']}")
        print(f"  Output File:   {result['output_path']}")
        print(f"  Metadata:      {result['metadata_path']}")

        # Show the metadata.json content
        print(f"\n{'-'*60}")
        print("  metadata.json:")
        print(f"{'-'*60}")
        with open(result['metadata_path'], 'r', encoding='utf-8') as f:
            print(json.dumps(json.load(f), indent=2, ensure_ascii=False))

        print(f"\n{'='*60}")
        print(f"  [OK] All files saved successfully!")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
