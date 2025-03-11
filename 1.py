import cv2
import numpy as np
import time

#  0 или 1
cap = cv2.VideoCapture(0)  

if not cap.isOpened():
    print("Ошибка: не удалось открыть камеру")
    exit()

prev_time = time.time()
frame_count = 0
fps = 0

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
        fps = frame_count / elapsed_time
        frame_count = 0
        prev_time = current_time

    cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Webcam", frame)
    cv2.imshow("Frame Difference", frame_diff)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
