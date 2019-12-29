from crop_video_file import crop
import cv2

video_path = 'D:/hikaru/Videos/test.mp4'
video = cv2.VideoCapture(video_path)

w = video.get(cv2.CAP_PROP_FRAME_WIDTH)
h = video.get(cv2.CAP_PROP_FRAME_HEIGHT)

w_crop = int(w / 7)
h_crop = int(h / 9)
crop(video_path, w_crop * 3, h_crop * 6, w_crop, h_crop)
