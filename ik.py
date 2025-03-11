import tkinter as tk
from tkinter import filedialog, messagebox
import time
import numpy as np
import cv2
from PIL import Image, ImageTk
import mvsdk
from ctypes import c_void_p

# Функция для преобразования кадра из формата SDK в RGB-изображение
def convert_frame(hCamera, frame_buffer, frame_info):
    width = frame_info.iWidth
    height = frame_info.iHeight
    # Создаём пустой массив для изображения формата RGB24
    img_rgb = np.empty((height, width, 3), dtype=np.uint8)
    # Преобразуем полученный кадр в RGB-формат
    ret = mvsdk.CameraImageProcess(hCamera, frame_buffer, img_rgb.ctypes.data_as(c_void_p), frame_info)
    if ret != mvsdk.CAMERA_STATUS_SUCCESS:
        raise Exception("Ошибка обработки изображения: " + str(ret))
    return img_rgb

# Инициализация камеры
device_list = mvsdk.CameraEnumerateDevice()
if len(device_list) < 1:
    messagebox.showerror("Ошибка", "Камера не найдена!")
    exit()

# Используем первую обнаруженную камеру
camera_info = device_list[0]
try:
    hCamera = mvsdk.CameraInit(camera_info)
except Exception as e:
    messagebox.showerror("Ошибка инициализации", str(e))
    exit()

# Запускаем видеопоток
mvsdk.CameraPlay(hCamera)

# Глобальные переменные для расчёта FPS и состояния триггера
last_time = time.time()
fps = 0
trigger_enabled = False

# Создаём окно приложения
root = tk.Tk()
root.title("Просмотр видео с камеры")

# Задаём размер холста (его можно адаптировать под разрешение камеры)
canvas_width = 640
canvas_height = 480
canvas = tk.Canvas(root, width=canvas_width, height=canvas_height)
canvas.pack()

# Функция обновления кадра и отображения информации на видео
def update_frame():
    global last_time, fps
    try:
        # Получаем кадр с камеры (время ожидания – 1000 мс)
        frame_buffer, frame_info = mvsdk.CameraGetImageBuffer(hCamera, 1000)
        img = convert_frame(hCamera, frame_buffer, frame_info)
        mvsdk.CameraReleaseImageBuffer(hCamera, frame_buffer)
        
        # Вычисляем FPS
        current_time = time.time()
        delta = current_time - last_time
        fps = 1.0 / delta if delta > 0 else 0
        last_time = current_time

        # Накладываем на изображение текстовую информацию:
        # 1. FPS
        cv2.putText(img, f"FPS: {fps:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # 2. Разрешение
        cv2.putText(img, f"{frame_info.iWidth}x{frame_info.iHeight}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # 3. Экспозиция (если поддерживается)
        try:
            exp_time = mvsdk.CameraGetExposureTime(hCamera)
            cv2.putText(img, f"Exp: {exp_time}us", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except Exception:
            pass

        # Преобразуем изображение для отображения в Tkinter (конвертируем BGR->RGB)
        im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=im)
        canvas.imgtk = imgtk  # сохраняем ссылку, чтобы изображение не сбрасывалось сборщиком мусора
        canvas.create_image(0, 0, anchor="nw", image=imgtk)
    except Exception as e:
        print("Ошибка при обновлении кадра:", e)
    root.after(10, update_frame)

# Функция для переключения режима аппаратного триггера
def toggle_trigger():
    global trigger_enabled
    trigger_enabled = not trigger_enabled
    # Предположим, что значение 1 включает аппаратный триггер, а 0 – выключает
    mode = 1 if trigger_enabled else 0
    ret = mvsdk.CameraSetTriggerMode(hCamera, mode)
    if ret != mvsdk.CAMERA_STATUS_SUCCESS:
        messagebox.showerror("Ошибка", f"Не удалось установить режим триггера: {ret}")
        return
    btn_trigger.config(text="Выключить HW Trigger" if trigger_enabled else "Включить HW Trigger")

# Функция загрузки файла настроек
def load_settings():
    filename = filedialog.askopenfilename(title="Выберите файл настроек",
                                          filetypes=[("Config files", "*.Config"), ("All files", "*.*")])
    if filename:
        ret = mvsdk.CameraReadParameterFromFile(hCamera, filename)
        if ret != mvsdk.CAMERA_STATUS_SUCCESS:
            messagebox.showerror("Ошибка", f"Не удалось загрузить настройки: {ret}")
        else:
            messagebox.showinfo("Успех", "Настройки успешно загружены.")

# Кнопки управления
btn_trigger = tk.Button(root, text="Включить HW Trigger", command=toggle_trigger)
btn_trigger.pack(side=tk.LEFT, padx=10, pady=10)

btn_load = tk.Button(root, text="Загрузить настройки", command=load_settings)
btn_load.pack(side=tk.LEFT, padx=10, pady=10)

# Пример дополнительной полезной информации, которую можно вывести:
# - Текущие параметры экспозиции, усиления и баланса белого
# - Серийный номер камеры и версию драйвера (например, через mvsdk.CameraGetInformation)
# - Статистика захвата: общее количество кадров, потерянные кадры, ошибочные кадры (через CameraGetFrameStatistic)
# - Текущее время и дату
# - Состояние подключения камеры, а также температуру (если поддерживается аппаратно)
# Эти данные можно либо отобразить в отдельном текстовом виджете, либо наложить на изображение как дополнительные подписи.

# Запуск цикла обновления кадров
root.after(10, update_frame)
root.mainloop()

# При завершении работы освобождаем ресурсы камеры
mvsdk.CameraUnInit(hCamera)
