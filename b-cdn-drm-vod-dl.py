import re
import sys
from hashlib import md5
from html import unescape
from random import random
from urllib.parse import urlparse

import requests
import yt_dlp

# Script updated to handle both traditional DRM-protected streams and direct m3u8/mpd streams
# The script now detects the stream type automatically and uses the appropriate method


class BunnyVideoDRM:
    # user agent and platform related headers
    user_agent = {
        "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    }
    session = requests.Session()
    session.headers.update(user_agent)

    def __init__(self, referer="https://127.0.0.1/", embed_url="", name="", path=""):
        self.referer = referer if referer else sys.exit(1)
        self.embed_url = embed_url if embed_url else sys.exit(1)
        self.guid = urlparse(embed_url).path.split("/")[-1]
        self.headers = {
            "embed": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": referer,
                "sec-fetch-dest": "iframe",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "cross-site",
                "upgrade-insecure-requests": "1",
            },
            "ping|activate": {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "origin": "https://iframe.mediadelivery.net",
                "pragma": "no-cache",
                "referer": "https://iframe.mediadelivery.net/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
            },
            "playlist": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": embed_url,
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        }
        embed_response = self.session.get(embed_url, headers=self.headers["embed"])
        embed_page = embed_response.text
        try:
            # Extract the server ID from the HTML
            server_match = re.search(r"https://video-(.*?)\.mediadelivery\.net", embed_page)
            if server_match:
                self.server_id = server_match.group(1)
            else:
                # Try to find the CDN URL in the HTML
                cdn_match = re.search(r"https://vz-(.*?)\.b-cdn\.net", embed_page)
                if cdn_match:
                    self.server_id = cdn_match.group(1)
                else:
                    sys.exit(1)
        except AttributeError:
            sys.exit(1)
            
        self.headers["ping|activate"].update(
            {"authority": f"video-{self.server_id}.mediadelivery.net"}
        )
        
        # Extract direct stream URL from the HTML
        stream_url_match = re.search(r'(https://[^"\s]+\.(?:m3u8|mpd))', embed_page)
        if stream_url_match:
            self.direct_stream_url = stream_url_match.group(1)
            print(f"Found direct stream URL: {self.direct_stream_url}")
            # For compatibility with the rest of the code, set dummy values
            self.context_id = "direct"
            self.secret = "direct"
        else:
            # Try the old method for backward compatibility
            search = re.search(r'contextId=(.*?)&secret=(.*?)"', embed_page)
            if search:
                self.context_id, self.secret = search.group(1), search.group(2)
            else:
                print("Error: Could not find stream information in the embed page.")
                sys.exit(1)
        if name:
            self.file_name = f"{name}.mp4"
        else:
            file_name_unescaped = re.search(
                r'og:title" content="(.*?)"', embed_page
            ).group(1)
            file_name_escaped = unescape(file_name_unescaped)
            self.file_name = re.sub(r"\.[^.]*$.*", ".mp4", file_name_escaped)
            if not self.file_name.endswith(".mp4"):
                self.file_name += ".mp4"
        self.path = path if path else "~/Videos/Bunny CDN/"

    def prepare_dl(self) -> str:
        # If we have a direct stream URL, we don't need to do the DRM preparation
        if hasattr(self, 'direct_stream_url'):
            print("Direct stream URL found, skipping DRM preparation")
            self.session.close()
            return "direct"
            
        # Traditional DRM method
        def ping(time: float, paused: str, res: str):
            md5_hash = md5(
                f"{self.secret}_{self.context_id}_{time}_{paused}_{res}".encode("utf8")
            ).hexdigest()
            params = {
                "hash": md5_hash,
                "time": time,
                "paused": paused,
                "chosen_res": res,
            }
            self.session.get(
                f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/ping",
                params=params,
                headers=self.headers["ping|activate"],
            )

        def activate():
            self.session.get(
                f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/activate",
                headers=self.headers["ping|activate"],
            )

        def main_playlist():
            params = {"contextId": self.context_id, "secret": self.secret}
            response = self.session.get(
                f"https://iframe.mediadelivery.net/{self.guid}/playlist.drm",
                params=params,
                headers=self.headers["playlist"],
            )
            resolutions = re.findall(r"\s*(.*?)\s*/video\.drm", response.text)[::-1]
            if not resolutions:
                sys.exit(2)
            else:
                return resolutions[0]  # highest resolution, -1 for lowest

        def video_playlist():
            params = {"contextId": self.context_id}
            self.session.get(
                f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm",
                params=params,
                headers=self.headers["playlist"],
            )

        try:
            ping(time=0, paused="true", res="0")
            activate()
            resolution = main_playlist()
            video_playlist()
            for i in range(0, 29, 4):  # first 28 seconds, arbitrary (check issue#11)
                ping(
                    time=i + round(random(), 6),
                    paused="false",
                    res=resolution.split("x")[-1],
                )
            self.session.close()
            return resolution
        except Exception as e:
            print(f"Error during DRM preparation: {e}")
            self.session.close()
            sys.exit(1)

    def download(self):
        url = []
        # If we have a direct stream URL, use it directly
        if hasattr(self, 'direct_stream_url'):
            print("Using direct stream URL for download")
            url = [self.direct_stream_url]
        else:
            # Otherwise use the traditional DRM method
            resolution = self.prepare_dl()
            url = [
                f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm?contextId={self.context_id}"
            ]
        
        ydl_opts = {
            "http_headers": {
                "Referer": self.embed_url,
                "User-Agent": self.user_agent["user-agent"],
            },
            "concurrent_fragment_downloads": 10,
            "nocheckcertificate": True,
            "outtmpl": self.file_name,
            "restrictfilenames": True,
            "windowsfilenames": True,
            "nopart": True,
            "paths": {
                "home": self.path,
                "temp": f".{self.file_name}/",
            },
            "retries": float("inf"),
            "extractor_retries": float("inf"),
            "fragment_retries": float("inf"),
            "skip_unavailable_fragments": False,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(url)


if __name__ == "__main__":
    video = BunnyVideoDRM(
        # insert the referer between the quotes below (address of your webpage)
        referer="https://namasteserials.com/seriale/Las-fierbinti/880/48122",
        embed_url="https://iframe.mediadelivery.net/embed/167542/72589e01-ff19-4089-b79e-8494443be5be",
        # you can override file name, no extension
        name="",
        # you can override download path
        path=r"/Users/umberto/Desktop/bunny-cdn-drm-video-dl/Users/umberto/Desktop",
    )
    # video.session.close()
    video.download()