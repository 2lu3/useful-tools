import os
import tkinter
import tkinter.filedialog
import tkinter.messagebox

from pydub import AudioSegment


def choose_audio_file():
    root = Tkinter.Tk()
    root.withdraw()
    fTyp = [("", "*")]
    iDir = os.path.abspath(os.path.dirname(__file__))
    tkinter.messagebox.showinfo("音声ファイルトリムツール", "ファイルを選択してください")
    file_path = tkinter.filedialog.askopenfilenames(
        filetypes=fTyp, initialdir=iDir)
    return file_path


def clip_audio_file(file_path, start_second, end_second):
    file_ext = os.path.splitext(os.path.basename(file_path))[0]
    # mp3ファイルの読み込み
    sound = AudioSegment.from_file(file_path, format=file_ext)

    return sound[start_second, end_second]


def main():
    file_path = choose_audio_file()
    clip_audio_file(file_path)


if __name__ == '__main__':
