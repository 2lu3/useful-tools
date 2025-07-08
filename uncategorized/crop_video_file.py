from moviepy.editor import *
import subprocess
import os, tkinter, tkinter.filedialog
import ffmpeg

class Test():
  def __init__(self)
  
  pass

def get_file_path():
  root = tkinter.Tk()
  root.withdraw()
  fTyp = [("", "*")]
  iDir = os.path.abspath(os.path.dirname(__file__))
  file_path = tkinter.filedialog.askopenfilename(filetypes = fTyp, initialdir = iDir)
  return file_path

def crop(file_path, Xs, Ys, Xl, Yl):
  basename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
  dir_name = os.path.dirname(file_path)
  out_name = dir_name + '/' + basename_without_ext + '_converted.mp4'

  command = f"ffmpeg -i {file_path} -vf crop={Xl}:{Yl}:{Xs}:{Ys} {out_name}"
  print(command)
  subprocess.run([command], shell=True)
  return out_name
  # 取り出したい静止画のファイル名を指定
  stream = ffmpeg.input(file_path)
  # sample.mp4に切り取りたい動画を入れる
  stream = ffmpeg.crop(stream, Xs, Ys, Xl, Yl)
  stream = ffmpeg.output(stream, out_name)
  ffmpeg.run(stream, overwrite_output=True)
  return out_name

if __name__ == '__main__':

  file_path = get_file_path()
  print(file_path)
  print('左上を原点とします')
  X_start = int(input('左のx座標\n'))
  X_length = int(input('右のx座標\n')) - X_start
  Y_start = int(input('上のy座標\n'))
  Y_length = int(input('下のy座標\n')) - Y_start
  print(X_start, X_length, Y_start, Y_length)
  crop(file_path, X_start, Y_start, X_length, Y_length)
