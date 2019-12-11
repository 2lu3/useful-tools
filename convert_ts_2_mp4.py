import subprocess
import sys

def main(infile):
  outfile = 'video.mp4'
  print(infile)
  subprocess.run(['ffmpeg', '-i', infile, outfile], shell=True)

if __name__ == '__main__':
  file_path = input('please drag and drop video file what you want to convert to mp4\n')
  if file_path[0] != '"':
    file_path = '"' + file_path + '"'

  main(file_path)

