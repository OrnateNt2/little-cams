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
    ret = mvsdk.CameraImageProcess(hCamera, frame_buffer, img_rgb.ctypes.data_as(c_void_p), frame_info)
    if ret != mvsdk.CAMERA_STATUS_SUCCESS:
        raise Exception("Ошибка обработки изображения: " + str(ret))
    return img_rgb

# Инициализация камеры
device_list = mvsdk.CameraEnumerateDevice()
if len(device_list) < 1:
    messagebox.showerror("Ошибка", "Камера не найдена!")
    exit()

camera_info = device_list[0]
try:
    hCamera = mvsdk.CameraInit(camera_info)
except Exception as e:
    messagebox.showerror("Ошибка инициализации", str(e))
    exit()

# Запуск видеопотока
mvsdk.CameraPlay(hCamera)

# Глобальные переменные для расчёта FPS и состояния триггера
last_time = time.time()
fps = 0
trigger_enabled = False

# Основное окно приложения
root = tk.Tk()
root.title("Видео с камеры и панель управления")

# Разбиваем окно на два фрейма: для видео и для управления
video_frame = tk.Frame(root)
video_frame.pack(side=tk.LEFT, padx=10, pady=10)

control_frame = tk.Frame(root)
control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

# Холст для вывода видео
canvas_width = 640
canvas_height = 480
canvas = tk.Canvas(video_frame, width=canvas_width, height=canvas_height, bg="black")
canvas.pack()

# Текстовый виджет для отображения текущей информации о параметрах камеры
info_text = tk.Text(control_frame, width=35, height=10, state=tk.DISABLED)
info_text.pack(pady=5)

# Параметры, которые можно изменять: время экспозиции и аналоговое усиление
param_frame = tk.LabelFrame(control_frame, text="Изменяемые параметры")
param_frame.pack(pady=5, fill=tk.X)

tk.Label(param_frame, text="Экспозиция (us):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
entry_exposure = tk.Entry(param_frame, width=10)
entry_exposure.grid(row=0, column=1, padx=5, pady=2)

tk.Label(param_frame, text="Аналоговый gain:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
entry_gain = tk.Entry(param_frame, width=10)
entry_gain.grid(row=1, column=1, padx=5, pady=2)

def apply_settings():
    try:
        new_exposure = float(entry_exposure.get())
        ret1 = mvsdk.CameraSetExposureTime(hCamera, new_exposure)
        if ret1 != mvsdk.CAMERA_STATUS_SUCCESS:
            raise Exception(f"Ошибка установки экспозиции: {ret1}")
        new_gain = int(entry_gain.get())
        ret2 = mvsdk.CameraSetAnalogGain(hCamera, new_gain)
        if ret2 != mvsdk.CAMERA_STATUS_SUCCESS:
            raise Exception(f"Ошибка установки усиления: {ret2}")
        messagebox.showinfo("Успех", "Настройки изменены")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

btn_apply = tk.Button(param_frame, text="Применить настройки", command=apply_settings)
btn_apply.grid(row=2, column=0, columnspan=2, pady=5)

# Кнопка переключения аппаратного триггера
def toggle_trigger():
    global trigger_enabled
    trigger_enabled = not trigger_enabled
    mode = 1 if trigger_enabled else 0
    ret = mvsdk.CameraSetTriggerMode(hCamera, mode)
    if ret != mvsdk.CAMERA_STATUS_SUCCESS:
        messagebox.showerror("Ошибка", f"Не удалось установить режим триггера: {ret}")
        return
    btn_trigger.config(text="Выключить HW Trigger" if trigger_enabled else "Включить HW Trigger")

btn_trigger = tk.Button(control_frame, text="Включить HW Trigger", command=toggle_trigger)
btn_trigger.pack(pady=5, fill=tk.X)

# Кнопка загрузки файла настроек
def load_settings():
    filename = filedialog.askopenfilename(title="Выберите файл настроек",
                                          filetypes=[("Config files", "*.Config"), ("All files", "*.*")])
    if filename:
        ret = mvsdk.CameraReadParameterFromFile(hCamera, filename)
        if ret != mvsdk.CAMERA_STATUS_SUCCESS:
            messagebox.showerror("Ошибка", f"Не удалось загрузить настройки: {ret}")
        else:
            messagebox.showinfo("Успех", "Настройки успешно загружены")

btn_load = tk.Button(control_frame, text="Загрузить настройки", command=load_settings)
btn_load.pack(pady=5, fill=tk.X)

# Функция обновления текстового виджета с информацией о параметрах
def update_info():
    try:
        exposure = mvsdk.CameraGetExposureTime(hCamera)
        gain = mvsdk.CameraGetAnalogGain(hCamera)
        # Можно добавить получение других параметров, например: баланс белого, яркость, контраст и т.д.
        info = f"Экспозиция: {exposure} us\n" \
               f"Аналоговый gain: {gain}\n" \
               f"HW Trigger: {'Включен' if trigger_enabled else 'Выключен'}\n" \
               f"Разрешение: {canvas_width}x{canvas_height}\n" \
               f"FPS: {fps:.2f}\n"
        info_text.config(state=tk.NORMAL)
        info_text.delete('1.0', tk.END)
        info_text.insert(tk.END, info)
        info_text.config(state=tk.DISABLED)
    except Exception as e:
        print("Ошибка обновления информации:", e)
    root.after(1000, update_info)

# Функция обновления кадра и отображения видео
def update_frame():
    global last_time, fps
    try:
        frame_buffer, frame_info = mvsdk.CameraGetImageBuffer(hCamera, 1000)
        img = convert_frame(hCamera, frame_buffer, frame_info)
        mvsdk.CameraReleaseImageBuffer(hCamera, frame_buffer)
        
        current_time = time.time()
        delta = current_time - last_time
        fps = 1.0 / delta if delta > 0 else 0
        last_time = current_time

        # Наложение текстовой информации на кадр (FPS, разрешение, экспозиция)
        cv2.putText(img, f"FPS: {fps:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f"{frame_info.iWidth}x{frame_info.iHeight}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        try:
            exp_time = mvsdk.CameraGetExposureTime(hCamera)
            cv2.putText(img, f"Exp: {exp_time}us", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except Exception:
            pass

        im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=im)
        canvas.imgtk = imgtk  # чтобы изображение не удалялось сборщиком мусора
        canvas.create_image(0, 0, anchor="nw", image=imgtk)
    except Exception as e:
        print("Ошибка при обновлении кадра:", e)
    root.after(10, update_frame)

# Запускаем периодическое обновление видео и информации
root.after(10, update_frame)
root.after(1000, update_info)
root.mainloop()

# При завершении работы освобождаем ресурсы камеры
mvsdk.CameraUnInit(hCamera)
