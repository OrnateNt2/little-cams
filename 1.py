import cv2
import numpy as np
import time
import datetime
import tkinter as tk
from tkinter import messagebox

def toggle_recording():
    global recording
    recording = not recording

def list_available_cameras(max_index=5):
    available = []
    for i in range(max_index):
        cap_test = cv2.VideoCapture(i)
        if cap_test.isOpened():
            available.append(i)
            cap_test.release()
    return available

root = tk.Tk()
root.withdraw()  
record_video = messagebox.askyesno("Запись видео", "Хотите записывать видео?")
root.destroy()

available_cams = list_available_cameras(5)
if not available_cams:
    print("Ошибка: не найдены доступные камеры")
    exit()
print("Доступные камеры:", available_cams)
try:
    cam_index = int(input("Введите номер камеры из списка: "))
except ValueError:
    cam_index = available_cams[0]
if cam_index not in available_cams:
    print("Указанная камера недоступна, используем камеру 0")
    cam_index = available_cams[0]

cap = cv2.VideoCapture(cam_index)
if not cap.isOpened():
    print("Ошибка: не удалось открыть камеру")
    exit()

frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30  # Если FPS не определяется, ставим 30

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
video_filename = f"video_{timestamp}.avi"
diff_filename = f"frame_diff_{timestamp}.avi"

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out_video = cv2.VideoWriter(video_filename, fourcc, fps, (frame_width, frame_height))
out_diff = cv2.VideoWriter(diff_filename, fourcc, fps, (frame_width, frame_height), isColor=False)

prev_time = time.time()
frame_count = 0
fps_display = 0

recording = False

def create_gui():
    gui = tk.Tk()
    gui.title("Управление записью")
    chk = tk.Checkbutton(gui, text="Записывать видео", command=toggle_recording)
    chk.pack(pady=10)
    gui.mainloop()

import threading
threading.Thread(target=create_gui, daemon=True).start()

ret, prev_frame = cap.read()
if not ret:
    print("Ошибка: не удалось захватить первый кадр")
    cap.release()
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Ошибка: не удалось захватить кадр")
        break

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    frame_diff = cv2.absdiff(gray_frame, gray_prev_frame)

    prev_frame = frame.copy()

    frame_count += 1
    current_time = time.time()
    elapsed_time = current_time - prev_time
    if elapsed_time > 1:
        fps_display = frame_count / elapsed_time
        frame_count = 0
        prev_time = current_time

    cv2.putText(frame, f"FPS: {fps_display:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Cam", frame)
    cv2.imshow("Difference", frame_diff)

    if recording:
        out_video.write(frame)
        out_diff.write(frame_diff)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out_video.release()
out_diff.release()
cv2.destroyAllWindows()
