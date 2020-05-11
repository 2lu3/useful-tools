import os
from subprocess import Popen

out_dir = "tmp2/"
os.makedirs(out_dir, exist_ok=True)
url = "https://www.youtube.com/playlist?list=PLU6riFzY66rpQ0hdQLvEz-b_WYohJP5G1"
video_number = 146
video_per_channel = 1


command_option = (
    "youtube-dl -f bestvideo[ext=mp4]+bestaudio[ext=m4a] -o " + out_dir + "%(title)s"
)

for i in range(round(video_number / video_per_channel)):
    start = i * video_per_channel + 1
    end = start + video_per_channel - 1
    if end >= video_number:
        end = video_number
    command = (
        command_option
        + " "
        + url
        + " --playlist-start "
        + str(start)
        + " --playlist-end "
        + str(end)
    )
    print(command)
    if end == video_number:
        Popen(command, shell=True)
    else:
        command += " -q"
        Popen(command)
