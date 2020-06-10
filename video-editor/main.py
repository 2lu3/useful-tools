# video-editor.py
#
# 機能：任意の場所で複数箇所のトリミングをして、自由に結合できる
#
# コマンド一覧
# trim a b (c) : aからbまでトリミング。cという名前で保存する(省略可)
# rename a b : トリミングしたaをbという名前に変更
# concat a b (c) : aの後にbを連結する。cという名前で保存する(省略可)
# del a : aを削除する
# show : トリミングしたファイル一覧
# play a : aを再生

import os
import tkinter as tk
from glob import glob
from subprocess import PIPE, Popen

from controller import Controller
from video import Video
from view import MainView


class VideoEditor:
    def __init__(self):
        self.video_list = []
        self.selected_video = None

    def to_filename(self, name):
        if "." not in name:
            return name + ".mp4"
        else:
            return name

    def to_name(self, filename):
        if "." in filename:
            return os.path.splitext(os.path.basename(filename))[0]
        else:
            return filename

    # 最初の動画をロード
    def load_video(self, path, name=None):
        if name is None:
            name = self.to_name(path)
        video = Video(name)
        self.video_list.append(video)

    # トリミングし、別ファイルとして保存
    def trim(self, index, start, end, name=None):
        # 名前を指定されていない場合
        if name is None:
            name = "video_" + str(len(self.video_list))

        # 保存先Video
        new_video = Video(name)

        # トリミングし、別ファイルに保存
        time = end - start
        command = f"ffmpeg -ss {start} -i {self.video_list[index].path} -t {time} {new_video.path}"
        proc = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        result = proc.communicate()
        print(result[0])
        print(result[1])

        # video_listに変更を反映
        self.video_list.append(new_video)

    # 別名に変更
    def rename(self, index, new_name):
        # 新しいVideoを作成
        new_video = Video(new_name)

        # ファイル名を変更
        os.rename(self.video_list[index].path, new_video.path)

        # 古いデータを削除
        self.video_list.pop(index)

        # video_listに変更を反映
        self.video_list.append(new_video)

    # 結合する
    def concat(self, index, name):
        # 名前を指定されていない場合
        if name is None:
            name = "video_" + str(len(self.video_list))

        # 保存先Video
        new_video = Video(name)

        with open("temp.txt", "w") as f:
            for i in index:
                f.write("file ")
                f.write(self.video_list[int(i)].path)
                f.write("\n")
        command = f"ffmpeg -f concat -i temp.txt -c copy {new_video.path}"
        proc = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        result = proc.communicate()
        print(result[0])
        print(result[1])

    # 動画を列挙
    def show_all_videos(self):
        video_list = [video.name for video in self.video_list]
        print("")
        print("動画一覧")
        for i, name in enumerate(video_list):
            print(i, name)
        print("")

    # 削除
    def remove(self, index):
        os.remove(self.video_list[index].path)
        self.video_list.pop(index)

    def input_order(self):
        def input_command():
            for i, command in enumerate(commands):
                print(i, command)
            order = input("コマンドを入力して下さい\n")
            if order.isdecimal():  # 数字で入力された場合
                order = commands[int(order)]
            return order

        def choose_target_video():
            print("動画を選んで下さい(数字で)")
            return input()

        def enter_new_name():
            print("新しい名前を入力して下さい")
            name = input()
            if name == "":
                name = None
            return name

        order = input_command()

        if order == "exit":  # exit
            exit()

        self.show_all_videos()
        if order == "info":
            return None, None

        index = choose_target_video()
        if order == "0":  # trim
            print("開始位置を入力してください")
            start = int(input())
            print("終了位置を入力して下さい")
            end = int(input())
            name = enter_new_name()
            return "trim", [int(index), start, end, name]
        elif order == "1":  # rename
            name = enter_new_name()
            return "rename", [int(index), name]
        elif order == "2":  # concat
            name = enter_new_name()
            index = index.split(" ")
            return "concat", [index, name]
        elif order == "3":  # del
            return "del", [int(index)]
        elif order == "4":  # show
            pass
        elif order == "5":  # play
            return "play", [int(index)]
        else:
            print("this function is coming soon")


commands = [
    "select" "trim",
    "rename",
    "concat",
    "del",
    "info",
    "play",
    "show",
    "exit",
]


video_editor = VideoEditor()
video_list = glob("./output/*.mp4")
for path in video_list:
    video_editor.load_video(path)


class TkinterUi:
    def __init__(self):
        root = tk.Tk()
        root.title("video-editor")
        root.geometry()
        root.mainloop()


def main():
    app = tk.Tk()
    app.title("video-editor")

    main_video = Video("main")
    view = MainView(app, main_video)
    controller = Controller(app, main_video, view)

    app.mainloop()


if __name__ == "__main__":
    main()
