import asyncio
import evdev
from evdev import UInput, ecodes as e
import time
import threading

# --- НАЛАШТУВАННЯ ---
# Кнопка для увімкнення/вимкнення (за замовчуванням F9)
TOGGLE_KEY = e.KEY_F8
# Затримка між кліками в секундах
CLICK_INTERVAL = 0.05 

clicking = False

def clicker_thread(ui):
    """Потік, який безперервно клікає, якщо статус clicking == True"""
    global clicking
    while True:
        if clicking:
            # Натискання лівої кнопки миші
            ui.write(e.EV_KEY, e.BTN_LEFT, 1)
            ui.syn()
            time.sleep(0.01) # Коротка затримка утримання кнопки
            # Відпускання лівої кнопки миші
            ui.write(e.EV_KEY, e.BTN_LEFT, 0)
            ui.syn()
            time.sleep(CLICK_INTERVAL)
        else:
            time.sleep(0.05) # Чекаємо, щоб не навантажувати процесор

async def monitor_device(device):
    """Асинхронне прослуховування конкретної клавіатури"""
    global clicking
    try:
        async for event in device.async_read_loop():
            # Перевіряємо, чи це натискання (value == 1) нашої клавіші
            if event.type == e.EV_KEY and event.code == TOGGLE_KEY and event.value == 1:
                clicking = not clicking
                status = "🟢 УВІМКНЕНО" if clicking else "🔴 ВИМКНЕНО"
                print(f"Статус автоклікера: {status}")
    except Exception as ex:
        # Ігноруємо помилки відключення пристроїв
        pass

async def main():
    print("Ініціалізація автоклікера для Hyprland...")
    
    # Знаходимо всі пристрої вводу
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    # Фільтруємо ті, що мають клавіші (шукаємо наявність Enter, щоб відсіяти миші)
    keyboards = []
    for d in devices:
        caps = d.capabilities()
        if e.EV_KEY in caps and e.KEY_ENTER in caps[e.EV_KEY]:
            keyboards.append(d)
            
    if not keyboards:
        print("❌ Помилка: Не знайдено жодної клавіатури. Запустіть від імені root (sudo).")
        return

    print(f"Знайдено клавіатури: {len(keyboards)}")
    for k in keyboards:
        print(f" - {k.name}")

    # Створюємо віртуальну мишу для симуляції кліків
    capabilities = {
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
        e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL]
    }
    
    try:
        ui = UInput(capabilities, name="wayland-autoclicker-mouse")
    except evdev.uinput.UInputError:
        print("❌ Помилка: Неможливо створити віртуальний пристрій. Потрібні права root.")
        return

    # Запускаємо потік клікера
    t = threading.Thread(target=clicker_thread, args=(ui,), daemon=True)
    t.start()

    print("\n✅ Автоклікер успішно запущено!")
    print("======================================")
    print(f"Натисніть клавішу F9 для увімкнення/вимкнення.")
    print("Натисніть Ctrl+C у терміналі для виходу.")
    print("======================================\n")

    # Прослуховуємо всі знайдені клавіатури
    tasks = [monitor_device(k) for k in keyboards]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВихід з програми. До побачення!")
