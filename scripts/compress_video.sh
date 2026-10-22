#!/usr/bin/env bash
# Compress a screen recording of the interface.
#
# The recordings are screen captures: the text is the content, the screen
# changes every couple of seconds, and nothing moves between the changes.
# So the encode is tuned for still images, the frame rate is cut down to
# what the eye needs to follow the typing, and the resolution is left alone
# so the text stays sharp.
#
# The 15 MB original of the three way debate becomes 4.9 MB this way, and
# the text is still as crisp as in the original.
#
# Usage:
#   scripts/compress_video.sh docs/assets/videos/3way-auto-debate.mp4
#
# The result lands next to the source as <name>.compressed.mp4.

set -euo pipefail

SOURCE="${1:-}"
if [[ -z "$SOURCE" ]]; then
  echo "usage: $(basename "$0") <video file>" >&2
  exit 1
fi

if [[ ! -f "$SOURCE" ]]; then
  echo "no such file: $SOURCE" >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is not on the path" >&2
  exit 1
fi

TARGET="${SOURCE%.mp4}.compressed.mp4"

echo "source: $SOURCE"
echo "target: $TARGET"

ffmpeg -hide_banner -loglevel error -y -i "$SOURCE" \
  -vf "fps=5" \
  -c:v libx264 \
  -preset veryslow \
  -tune stillimage \
  -profile:v high \
  -pix_fmt yuv420p \
  -x264-params "aq-mode=3" \
  -g 100 \
  -keyint_min 100 \
  -sc_threshold 0 \
  -movflags +faststart \
  "$TARGET"

echo
ls -la "$SOURCE" "$TARGET"
echo
echo "move it over the source when it looks right:"
echo "  mv $TARGET $SOURCE"
