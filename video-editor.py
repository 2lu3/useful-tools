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
from glob import glob
from subprocess import PIPE, Popen


class Video:
    def __init__(self, name, output_path="output/"):
        self.output_root = output_path
        self.rename(name)

    def rename(self, new_name):
        self.name = new_name
        self.filename = self.name + ".mp4"
        self.path = self.output_root + self.filename

    def remove(self):
        os.remove(self.path)


class VideoEditor:
    def __init__(self):
        self.video_list = []

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
    def show(self):
        return [video.name for video in self.video_list]

    # 削除
    def remove(self, index):
        os.remove(self.video_list[index].path)
        self.video_list.pop(index)


commands = [
    "trim name start end (save_name)",
    "rename old_name new_name",
    "concat name1, name2 (save_name)",
    "del name",
    "show",
    "play name",
    "exit",
]


video_editor = VideoEditor()
video_list = glob("./output/*.mp4")
for path in video_list:
    video_editor.load_video(path)


def show_all_videos():
    video_list = video_editor.show()
    print("")
    print("動画一覧")
    for i, name in enumerate(video_list):
        print(i, name)
    print("")


def input_order():
    for i, command in enumerate(commands):
        print(i, command)

    order = input("コマンドを入力して下さい(数字で)\n")

    if order == "6" or order == "exit":  # exit
        return "exit", None

    show_all_videos()
    if order == "4" or order == "show":
        return None, None

    print("動画を選んで下さい(数字で)")
    index = input()
    if order == "0":  # trim
        print("開始位置を入力してください")
        start = int(input())
        print("終了位置を入力して下さい")
        end = int(input())
        print("新しい名前を入力して下さい")
        name = input()
        if name == "":
            name = None
        return "trim", [int(index), start, end, name]
    elif order == "1":  # rename
        print("新しい名前を入力して下さい")
        name = input()
        if name == "":
            name = None
        return "rename", [int(index), name]
    elif order == "2":  # concat
        print("新しい名前を入力して下さい")
        name = input()
        if name == "":
            name = None
        index = index.split(" ")
        return "concat", [index, name]
    elif order == "3":  # del
        return "del", [int(index)]
    elif order == "4":  # show
        pass
    elif order == "5":  # play
        return "play", [int(index)]


def main():
    while True:
        order, option = input_order()

        if order == "trim":
            video_editor.trim(option[0], option[1], option[2], option[3])
        elif order == "rename":
            video_editor.rename(option[0], option[1])
        elif order == "concat":
            video_editor.concat(option[0], option[1])
        elif order == "del":
            video_editor.remove(option[0])
        elif order == "show":
            show_all_videos()
        elif order == "play":
            print("自分でやれ")
        elif order == "exit":
            exit()

        print("")
        print("")
        print("")


if __name__ == "__main__":
    main()
