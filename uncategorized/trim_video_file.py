# conda install moviepy

import os
import tkinter
import tkinter.filedialog
import tkinter.messagebox

from moviepy.editor import *


def get_file_path():
    root = tkinter.Tk()
    root.withdraw()
    fTyp = [("", "*")]
    iDir = os.path.abspath(os.path.dirname(__file__))
    tkinter.messagebox.showinfo("trim video file", "動画ファイルを選択してください")
    file_path = tkinter.filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)
    return file_path


def main(file_path, start_second, end_second):
    basename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
    dirname = os.path.dirname(file_path)
    video = VideoFileClip(file_path).subclip(start_second, end_second)
    # video.write_videofile(dirname + '/' + basename_without_ext + 'converted.mp4', fps=60)
    video.write_videofile(dirname + "/" + basename_without_ext + "converted.mp4")


if __name__ == "__main__":
    file_path = get_file_path()
    print(file_path)
    start_second = int(input("input start second\n"))
    end_second = int(input("input end second\n"))
    print(start_second, end_second)
    main(file_path, start_second, end_second)
