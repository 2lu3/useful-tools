import os
from subprocess import Popen
from time import sleep

out_dir = "output/"
os.makedirs(out_dir, exist_ok=True)


command_option = ()


def ask_url():
    url = input("ダウンロードしたいURLを貼り付けて下さい\n")
    if "playlist" in url:
        video_num_in_playlist = int(input("プレイリスト入っている動画の数を入力して下さい\n"))
        video_per_channel = int(input("1スレッドあたりいくつ動画をダウンロードするか\n"))
        return url, video_num_in_playlist, video_per_channel
    else:
        return url, None, None


def download_one_video(url):
    command = (
        "youtube-dl -f bestvideo[ext=mp4]+bestaudio[ext=m4a] -o \""
        + out_dir
        + "%(title)s\" "
        + url
    )
    print(command)
    Popen(command, shell=True)


def download_playlist(url, video_number, video_per_channel):
    for i in range(round(video_number / video_per_channel)):
        start = i * video_per_channel + 1
        end = start + video_per_channel - 1
        if end >= video_number:
            end = video_number
        command = (
            "youtube-dl -f bestvideo[ext=mp4]+bestaudio[ext=m4a] -o \""
            + out_dir
            + "%(title)s\" "
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
            Popen(command, shell=True)


def main():
    url, video_num_in_playlist, video_per_channel = ask_url()
    if "playlist" in url:
        download_playlist(url, video_num_in_playlist, video_per_channel)
    else:
        download_one_video(url)

    sleep(3)
    _ = input("donwloading")


if __name__ == "__main__":
    main()
