import re
from typing import Any, Dict

import cv2
import numpy as np
import pyaudio
import PySimpleGUI as sg
from chardet.universaldetector import UniversalDetector


class Main:

    def load_video(self, path: str):
        self.cap = cv2.VideoCapture(path)

        self.ret, self.f_frame = self.cap.read()

        if self.ret:
            # 読み込み可能なとき

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            # 動画情報の取得
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

            # フレーム関係
            self.frame_count = 0
            self.start_frame = 0
            self.end_frame = self.total_count

            # 再生の一時停止フラグ
            self.stop_flg = False
            cv2.namedWindow("Movie")
        else:
            # 読み込みできないとき
            sg.Popup("読み込みできない動画ファイルです")

    def load_caption(self, path: str):
        detector = UniversalDetector()
        with open(path, mode="rb") as f:
            for line in f:
                if line == b"":
                    break
                detector.feed(line)
                if detector.done:
                    break
        encoding_info = detector.result
        with open(path, encoding=encoding_info["encoding"]) as f:
            self.captions = re.split("[,，、.．。\n]", f.read())
        # 空白の要素を削除
        self.captions = list(filter(None, self.captions))
        print(self.captions)

    def display_file_read(self):
        layout = [
            [sg.Text("簡単字幕結合")],
            [sg.Text("動画ファイル"), sg.InputText(), sg.FileBrowse(key="video_file")],
            [
                sg.Text("字幕ファイル"),
                sg.InputText(),
                sg.FilesBrowse(key="caption_file"),
            ],
            [sg.Button("次へ", key="next")],
        ]

        window: Any = sg.Window("メイン", layout)

        while True:
            event, values = window.read()
            if event == sg.WINDOW_CLOSED:
                break
            elif event == "next":
                if values["video_file"] == "":
                    sg.popup("動画ファイルを指定してください")
                    event = ""
                elif values["caption_file"] == "":
                    sg.popup("字幕ファイルを指定してください")
                    event = ""
                else:
                    self.load_video(values["video_file"])
                    self.load_caption(values["caption_file"])
                    break
        window.close()

    def display_main(self):
        layout = [
            [
                sg.Slider(
                    (0, self.total_count - 1),
                    0,
                    1,
                    orientation="h",
                    size=(50, 15),
                    key="-PROGRESS SLIDER-",
                    enable_events=True,
                )
            ],
            [
                sg.Button("<<<", size=(5, 1)),
                sg.Button("<<", size=(5, 1)),
                sg.Button("<", size=(5, 1)),
                sg.Button("Play / Stop", size=(9, 1)),
                sg.Button("Reset", size=(7, 1)),
                sg.Button(">", size=(5, 1)),
                sg.Button(">>", size=(5, 1)),
                sg.Button(">>>", size=(5, 1)),
            ],
            [
                sg.Text("Speed", size=(6, 1)),
                sg.Slider(
                    (0, 240),
                    10,
                    10,
                    orientation="h",
                    size=(19.4, 15),
                    key="-SPEED SLIDER-",
                    enable_events=True,
                ),
            ],
            [sg.HorizontalSeparator()],
            [sg.Listbox(self.captions, size=(30, len(self.captions)), key="-CAPTION-")],
        ]

        window: Any = sg.Window("簡単字幕作成ツール", layout, location=(0, 0))

        self.event: str
        values: Dict[str, int]
        self.event, values = window.read(timeout=0)

        try:
            while True:
                self.event, values = window.read(timeout=values["-SPEED SLIDER-"])

                if self.event != "__TIMEOUT__":
                    print(self.event)

                # ウィンドウの閉じるボタンが押されたら終了
                if self.event == sg.WIN_CLOSED:
                    break

                # 動画の再読み込み
                # スタートフレームを設定していると動く
                if self.event == "Reset":
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_count = self.start_frame
                    window["-PROGRESS SLIDER-"].update(self.frame_count)

                    # Progress sliderへの変更を反映させるためにcontinue
                    continue

                # フレーム操作 ################################################
                # スライダを直接変更した場合は優先する
                if self.event == "-PROGRESS SLIDER-":
                    # フレームカウントをプログレスバーに合わせる
                    self.frame_count = int(values["-PROGRESS SLIDER-"])
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)
                    if values["-PROGRESS SLIDER-"] > values["-END FRAME SLIDER-"]:
                        window["-END FRAME SLIDER-"].update(values["-PROGRESS SLIDER-"])

                if self.event == "<<<":
                    self.frame_count = np.maximum(0, self.frame_count - 150)
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                if self.event == "<<":
                    self.frame_count = np.maximum(0, self.frame_count - 30)
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                if self.event == "<":
                    self.frame_count = np.maximum(0, self.frame_count - 1)
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                if self.event == ">":
                    self.frame_count = self.frame_count + 1
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                if self.event == ">>":
                    self.frame_count = self.frame_count + 30
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                if self.event == ">>>":
                    self.frame_count = self.frame_count + 150
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                # カウンタがエンドフレーム以上になった場合、スタートフレームから再開
                if self.frame_count >= self.end_frame:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_count = self.start_frame
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    continue

                # ストップボタンで動画の読込を一時停止
                if self.event == "Play / Stop":
                    self.stop_flg = not self.stop_flg

                # ストップフラグが立っており、eventが発生した場合以外はcountinueで
                # 操作を停止しておく

                # ストップボタンが押された場合は動画の処理を止めるが、何らかの
                # eventが発生した場合は画像の更新のみ行う
                # mouse操作を行っている場合も同様
                if self.stop_flg and self.event == "__TIMEOUT__":
                    window["-PROGRESS SLIDER-"].update(self.frame_count)
                    continue

                # フレームの読込 ##############################################
                self.ret, self.frame = self.cap.read()

                self.frame = cv2.resize(self.frame, dsize=(640, 360))
                self.valid_frame = int(self.frame_count - self.start_frame)
                # 最後のフレームが終わった場合self.start_frameから再開
                if not self.ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_count = self.start_frame
                    continue

                # 以降にフレームに対する処理を記述 ##################################
                # frame全体に対する処理をはじめに実施 ##############################
                # フレーム数と経過秒数の表示
                cv2.putText(
                    self.frame,
                    str("framecount: {0:.0f}".format(self.frame_count)),
                    (15, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (240, 230, 0),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    self.frame,
                    str("time: {0:.1f} sec".format(self.frame_count / self.fps)),
                    (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (240, 230, 0),
                    1,
                    cv2.LINE_AA,
                )

                # 画像を表示
                cv2.imshow("Movie", self.frame)

                if self.stop_flg:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)

                else:
                    self.frame_count += 1
                    window["-PROGRESS SLIDER-"].update(self.frame_count + 1)

        finally:
            cv2.destroyWindow("Movie")
            self.cap.release()
            window.close()

    def run(self):
        self.display_file_read()
        self.display_main()


if __name__ == "__main__":
    Main().run()
