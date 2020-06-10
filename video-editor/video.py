import os
import cv2
import time
from PIL import Image, ImageTk


class Video:
    def __init__(self, name, path=None):
        # 動画名称
        self.name = name

        # 動画path
        self.path = path

        # 動画オブジェクト
        self.video = None

        # 読み込んだフレーム数
        self.frames = None

        # PIL画像
        self.image = None

        # Tkinter画像オブジェクト参照用
        self.image_tk = None

    def load_video(self, path=None):
        if path is not None:
            self.path = path
        self.video = cv2.VideoCapture(self.path)

    def advance_frame(self):
        # 1フレーム読み込む
        ret, self.frame = self.video.read()
        return ret

    def reverse_video(self):
        self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def create_image(self, size):
        # 画像を作成
        t1 = time.time()

        frame = self.frame

        # 指定サイズに
        frame = cv2.resize(frame, size)

        # 形式変換
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.image = Image.fromarray(rgb_image)

        t2 = time.time()
        print(f"経過時間:{t2-t1}")

    def get_image(self):
        self.image_tk = ImageTk.PhotoImage(self.image)
        return self.image_tk

    def get_fps(self):
        return self.video.get(cv2.CAP_PROP_FPS)

    def rename(self, name):
        self.name = name

    def remove(self):
        os.remove(self.path)
