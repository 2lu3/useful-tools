class Controller:
    def __init__(self, app, video, view):
        self.master = app
        self.video = video
        self.view = view

        # 動画再生中かどうかの管理
        self.playing = False

        # フレーム進行する間隔
        self.frame_timer = 0

        # 描画する間隔
        self.draw_timer = 50

        self.set_events()

    def set_events(self):
        "受け付けるイベントを設定する"

        # キャンバス上のマウス押し下げ開始イベント受付
        self.view.canvas.bind("<Button-1>", self.button_press)

        # 動画選択ボタン押し下げイベント受付
        self.view.load_button["command"] = self.push_load_button

    def draw(self):
        '一定間隔で画像等を描画'

        # 再度タイマー設定
        self.master.after(self.draw_timer, self.draw)

        # 動画再生中の場合
        if self.playing:
            # フレームの画像を作成
            self.video.create_image(
                (
                    self.view.canvas.winfo_width(),
                    self.view.canvas.winfo_height()
                )
            )

            # 動画１フレーム分をキャンバスに描画
            self.view.draw_image()

    def frame(self):
        '一定間隔でフレームを進める'

        # 再度タイマー設定
        self.master.after(self.frame_timer, self.frame)

        # 動画再生中の場合
        if self.playing:
            # 動画を１フレーム進める
            ret = self.video.advance_frame()

            # フレームが進められない場合
            if not ret:
                # フレームを最初に戻す
                self.video.reverse_video()
                self.video.advance_frame()

    def push_load_button(self):
        '動画選択ボタンが押された時の処理'

        file_types = [
            ("MOVファイル", "*.mov"),
            ("MP4ファイル", "*.mp4"),
        ]

        # ファイル選択画面表示
        file_path = self.view.select_open_file(file_types)

        if len(file_path) != 0:

            # 動画オブジェクト生成
            self.video.load_video(file_path)

            # 最初のフレームを表示
            self.video.advance_frame()
            self.video.create_image(
                (
                    self.view.canvas.winfo_width(),
                    self.view.canvas.winfo_height()
                )
            )
            self.video.reverse_video()
            self.view.draw_image()

            # 再生ボタンの表示
            self.view.delete_play_button()
            self.view.draw_play_button()

            # FPSに合わせてフレームを進める間隔を決定
            fps = self.video.get_fps()
            self.frame_timer = int(1 / fps * 1000 + 0.5)

            # フレーム進行用のタイマースタート
            self.master.after(self.frame_timer, self.frame)

            # 画像の描画用のタイマーセット
            self.master.after(self.draw_timer, self.draw)

    def button_press(self, event):
        'マウスボタン押された時の処理'

        # 動画の再生/停止を切り替える
        if not self.playing:
            self.playing = True

            # 再生ボタンの削除
            self.view.delete_play_button()
        else:
            self.playing = False
            
            # 再生ボタンの描画
            self.view.draw_play_button()
