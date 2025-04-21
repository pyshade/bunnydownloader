# Bunny CDN "DRM" Video Downloader

A Python class for downloading Bunny
CDN's "[DRM](https://bunny.net/stream/media-cage-video-content-protection/)" videos
using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Requirements

You'll need to install `yt-dlp` and `requests` modules in your Python environment.

```bash
pip install -r requirements.txt
```

> It is also better to have [FFmpeg](https://ffmpeg.org) installed on your system and its executable added to the PATH
> environment variable.

## Usage

To try the script for testing and demonstration, simply paste the iframe embed page URL at the bottom, where indicated
between the quotes, as well as the webpage referer, and run the script.

```bash
python3 b-cdn-drm-vod-dl.py
```

> Embed link structure: [
`https://iframe.mediadelivery.net/embed/{video_library_id}/{video_id}`](https://docs.bunny.net/docs/stream-embedding-videos)

## Expected Result

By default:

* the highest resolution video is to be downloaded. You can change this behavior in the `main_playlist` function located
  under the `prepare_dl` method.
* The video will be downloaded in the `~/Videos/Bunny CDN/` directory. This configuration can be changed by providing
  the `path` argument when instantiating a new `BunnyVideoDRM` object.
* The video file name will be extracted from the embed page. This can be overridden by providing the `name` argument .

> Please note that the video format will be always `mp4`.

## Explanation

The idea is all about simulating what's happening in a browser.

The program runs a sequence of requests tied to
a [session](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects) object (for cookie persistence and
connection pooling) first of which is the embed page request, from which information are extracted such as the video
name.

The script now supports two methods of downloading:

1. **Direct Stream Method**: If the embed page contains a direct m3u8/mpd stream URL, the script will use it directly without needing to perform the DRM authentication steps.

2. **Traditional DRM Method**: For older or protected streams, the script will perform the necessary DRM authentication steps to obtain a valid playback URL.

After obtaining the appropriate URL, it's fed to `yt-dlp` to download the video segments, decrypt them if needed (as Bunny CDN's "DRM" videos are encrypted with the AES-128 algorithm), and merge them into a single playable video file.

## Recent Updates

- **Automatic Stream Detection**: The script now automatically detects whether the video uses traditional DRM protection or direct m3u8/mpd streams.
- **Improved Error Handling**: Better error messages and recovery mechanisms.
- **Backward Compatibility**: Still works with older Bunny CDN embed formats that use contextId and secret parameters.