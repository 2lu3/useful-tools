for %%f in (*.mp4) do (
ffmpeg -i "%%~nf".mp4 -vn -ac 2 -ar 44100 -ab 256k -acodec libmp3lame -f mp3 "%%~nf".mp3
)