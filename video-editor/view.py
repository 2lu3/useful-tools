import tkinter as tk
from tkinter import filedialog


class View:
    def __init__(self, app, video):
        self.master = app
        self.video = video

        # アプリ内のウィジェットを作成
        self.create_widgets()

    def create_widgets(self):
        # キャンバスのサイズ
        canvas_width = 500
        canvas_height = 300

        # キャンバスとボタンを配置するフレームの作成と配置
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack()

        # キャンバスを配置するフレームの作成と配置
        self.canvas_frame = tk.Frame(self.main_frame)
        self.canvas_frame.grid(column=1, row=1)

        # ユーザー操作用フレームの作成と配置
        self.operation_frame = tk.Frame(self.main_frame)
        self.operation_frame.grid(column=2, row=1)

        # キャンバスの作成と配置
        self.canvas = tk.Canvas(
            self.canvas_frame, width=canvas_width, height=canvas_height, bg="#EEEEEE",
        )
        self.canvas.pack()

        # ファイル読み込みボタンの作成と配置
        self.load_button = tk.Button(self.operation_frame, text="動画選択")
        self.load_button.pack()

    def draw_image(self):
        # 画像をキャンパスに描画
        image = self.video.get_image()

        # キャンバス上の画像の左上座標を決定
        sx = (self.canvas.winfo_width() - image.width()) // 2
        sy = (self.canvas.winfo_height() - image.height()) // 2

        # キャンバスに描画済みの画像を削除
        objs = self.canvas.find_withtag("image")
        for obj in objs:
            self.canvas.delete(obj)

        # 画像をキャンバスの中央に描画
        self.canvas.create_image(sx, sy, image=image, anchor=tk.NW, tag="image")

    def select_open_file(self, file_types):
        file_path = filedialog.askopenfilename(initialdir=".", filetypes=file_types,)
        return file_path

    def draw_play_button(self):
        # 再生ボタンを描画

        # キャンバスのサイズ取得
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        # 円の直径を決定
        if width > height:
            diameter = height
        else:
            diameter = width

        # 端からの距離を計算
        distance = diameter / 10

        # 円の線の太さを計算
        thickness = distance

        # 円の描画位置を決定
        sx = (width - diameter) // 2 + distance
        sy = (height - diameter) // 2 + distance

        ex = width - (width - diameter) // 2 - distance
        ey = height - (height - diameter) // 2 - distance

        # 丸を描画
        self.canvas.create_oval(
            sx, sy,
            ex, ey,
            outline="white",
            width=thickness,
            tag="oval"
        )

        # 頂点座標を計算
        x1 = sx + distance * 3
        y1 = sy + distance * 2
        x2 = sx + distance * 3
        y2 = ey - distance * 2
        x3 = ex - distance * 2
        y3 = height // 2

        # 三角を描画
        self.canvas.create_polygon(
            x1, y1,
            x2, y2,
            x3, y3,
            fill="white",
            tag="triangle"
        )

    def delete_play_button(self):
        self.canvas.delete("oval")
        self.canvas.delete("triangle")

