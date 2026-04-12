import urllib.request
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

url = "https://assets.mixkit.co/videos/download/mixkit-portrait-of-a-woman-talking-to-the-camera-14300.mp4"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

print("Downloading video from Mixkit...")
try:
    with urllib.request.urlopen(req) as response:
        with open("avatar_video.mp4", "wb") as f:
            f.write(response.read())
    print("Download complete: avatar_video.mp4")
except Exception as e:
    print(f"Failed to download: {e}")
