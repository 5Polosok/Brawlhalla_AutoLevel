import pyautogui
import pydirectinput
import time
import os
import datetime
import requests
import threading
import cv2
import numpy as np
from dotenv import load_dotenv
import os

# === НАСТРОЙКИ ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_FOLDER = os.path.join(SCRIPT_DIR, 'images')
LEVELS_FOLDER = os.path.join(SCRIPT_DIR, 'levels')

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "")

if not os.path.exists(LEVELS_FOLDER):
    os.makedirs(LEVELS_FOLDER)

# -- Навигация --
BTN_CUSTOM_INACTIVE  = os.path.join(IMG_FOLDER, 'customgameroom_inactive.png')
BTN_CUSTOM_ACTIVE    = os.path.join(IMG_FOLDER, 'customgameroom_active.png')
BTN_CREATE_INACTIVE  = os.path.join(IMG_FOLDER, 'createroom_inactive.png')
BTN_CREATE_ACTIVE    = os.path.join(IMG_FOLDER, 'createroom_active.png')
BTN_PRIVATE_INACTIVE = os.path.join(IMG_FOLDER, 'privateroom_inactive.png')
BTN_PRIVATE_ACTIVE   = os.path.join(IMG_FOLDER, 'privateroom_active.png')

# -- Ошибки и Меню --
BTN_LEAVE_MATCH      = os.path.join(IMG_FOLDER, 'leavematch.png')
BTN_ERROR_OCCURED    = os.path.join(IMG_FOLDER, 'error_occured.png')

# -- Правила --
BTN_ADD_BOT         = os.path.join(IMG_FOLDER, 'bots.png')
BTN_GAMEMODE_INACT  = os.path.join(IMG_FOLDER, 'gamemode_inactive.png')
BTN_GAMEMODE_ACT    = os.path.join(IMG_FOLDER, 'gamemode_active.png')
BTN_DAMAGE_INACT    = os.path.join(IMG_FOLDER, 'damage_inactive.png')
BTN_MATCHTIME_INACT = os.path.join(IMG_FOLDER, 'matchtime_inactive.png')
BTN_LIVES_INACT     = os.path.join(IMG_FOLDER, 'lives_inactive.png')

# -- Lobby Settings --
BTN_SETTINGS_LOBBY  = os.path.join(IMG_FOLDER, 'settingslobby_inactive.png')
BTN_FRIENDS_INACT   = os.path.join(IMG_FOLDER, 'friends_inactive.png')
BTN_GUILD_INACT     = os.path.join(IMG_FOLDER, 'guildmates_inactive.png')
BTN_HANDICAPS_INACT = os.path.join(IMG_FOLDER, 'handicaps_inactive.png')

# -- Игроки --
BTN_BOT_EXIST       = os.path.join(IMG_FOLDER, 'bot_exist.png')
BTN_PLAYER          = os.path.join(IMG_FOLDER, 'player.png')
BTN_DIFF_BOT        = os.path.join(IMG_FOLDER, 'handicap_difficulty.png')

# -- Handicaps --
BTN_HANDICAP_TAKEN      = os.path.join(IMG_FOLDER, 'handicap_taken.png')
BTN_HANDICAP_DONE       = os.path.join(IMG_FOLDER, 'handicap_done.png')
BTN_HANDICAP_TAKEN_BOT  = os.path.join(IMG_FOLDER, 'handicap_taken_bot.png')
BTN_HANDICAP_DONE_BOT   = BTN_HANDICAP_DONE

# -- Бой --
BTN_CHAR_UNHOVER        = os.path.join(IMG_FOLDER, 'char_unhovered.png')
BTN_MAP_CHOOSING        = os.path.join(IMG_FOLDER, 'map_choosing.png')
BTN_CHECK_INGAME        = os.path.join(IMG_FOLDER, 'checkifingame.png')
BTN_NEXT_LEVEL          = os.path.join(IMG_FOLDER, 'next_afterlevel.png')
BTN_NEXT_AFTERMATCH     = os.path.join(IMG_FOLDER, 'next_aftermatch.png')
BTN_GAME_STILL_PROGRESS = os.path.join(IMG_FOLDER, 'gamestillprogress.png')

# === КОНФИГУРАЦИЯ ===
CONFIDENCE = 0.80
GRAYSCALE = True
BOT_EXIST_REGION = (0, 160, 520, 360)


class AutoExpBot:
    def __init__(self):
        # === СТАТИСТИКА ===
        self.match_count = 0
        self.start_time = None
        self.match_start_time = None

        # локальные флаги
        self.setup_done_once = False

    # === ФУНКЦИИ ===

    @staticmethod
    def format_time(seconds: float) -> str:
        seconds = max(0, float(seconds))
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}ч {minutes}м {secs}с"
        if minutes > 0:
            return f"{minutes}м {secs}с"
        return f"{secs}с"

    def send_webhook(self, image_path: str):
        if not WEBHOOK_URL:
            return

        def _send():
            try:
                match_duration = time.time() - self.match_start_time if self.match_start_time else 0
                total_duration = time.time() - self.start_time if self.start_time else 0
                match_time_str = self.format_time(match_duration)
                total_time_str = self.format_time(total_duration)
                avg_time = (total_duration / self.match_count) if self.match_count > 0 else 0
                avg_time_str = self.format_time(avg_time)

                content = f"""**Level Up:** `{os.path.basename(image_path)}`
**Матч:** `#{self.match_count}`
**⏱️ Матч:** {match_time_str}
**📊 Всего:** {total_time_str} 
**⏳ Средняя:** {avg_time_str}"""

                with open(image_path, 'rb') as f:
                    files = {"file": f}
                    requests.post(WEBHOOK_URL, data={"content": content}, files=files, timeout=20)
                    print(f"   [Webhook] ✓ Отправлено: матч #{self.match_count}")
            except Exception as e:
                print(f"   [Webhook Error] {e}")

        threading.Thread(target=_send, daemon=True).start()

    # === УМНЫЙ ПОИСК С РЕСАЙЗОМ ===
    def locate_box(self, image_path, region=None, confidence=None):
        if not image_path or not os.path.exists(image_path):
            return None

        conf = confidence or CONFIDENCE

        try:
            box = pyautogui.locateOnScreen(image_path, confidence=conf, grayscale=GRAYSCALE, region=region)
            if box:
                return box
        except Exception:
            pass

        BASE_WIDTH = 1920
        screen_w, screen_h = pyautogui.size()

        if screen_w == BASE_WIDTH:
            return None

        scale = screen_w / BASE_WIDTH

        try:
            template = cv2.imread(image_path, 0 if GRAYSCALE else 1)
            if template is None:
                return None

            new_w = int(template.shape[1] * scale)
            new_h = int(template.shape[0] * scale)
            if new_w < 5 or new_h < 5:
                return None

            resized_template = cv2.resize(template, (new_w, new_h))

            screenshot = pyautogui.screenshot(region=region)
            screen_img = np.array(screenshot)
            screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_RGB2GRAY)

            if GRAYSCALE and len(screen_img.shape) == 3:
                screen_for_match = screen_gray
            else:
                screen_for_match = screen_img

            res = cv2.matchTemplate(screen_for_match, resized_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if max_val >= conf:
                found_x, found_y = max_loc
                if region:
                    found_x += region[0]
                    found_y += region[1]
                return pyautogui.Box(found_x, found_y, new_w, new_h)

        except Exception:
            pass

        return None

    def find_and_click(self, image_path, region=None, move_delay=0.08, confidence=None):
        box = self.locate_box(image_path, region=region, confidence=confidence)
        if not box:
            return False
        x, y = pyautogui.center(box)
        pydirectinput.moveTo(x, y)
        time.sleep(move_delay)
        pydirectinput.click()
        return True

    def click_image_multiple(self, image_path, times=1, region=None, delay=0.15, confidence=None):
        box = self.locate_box(image_path, region=region, confidence=confidence)
        if not box:
            return False
        x, y = pyautogui.center(box)
        pydirectinput.moveTo(x, y)
        time.sleep(0.10)
        for _ in range(times):
            pydirectinput.click()
            time.sleep(delay)
        return True

    def find_hover_press_keys(self, image_path, key_to_press, press_times=1, delay=0.18):
        box = self.locate_box(image_path)
        if not box:
            print(f"   [DEBUG] find_hover_press_keys: Не нашел {os.path.basename(image_path)}")
            return False
        x, y = pyautogui.center(box)
        pydirectinput.moveTo(x, y)
        time.sleep(0.15)
        for _ in range(press_times):
            pydirectinput.press(key_to_press)
            time.sleep(delay)
        return True

    def wait_for_image(self, image_path, timeout=20, region=None, check_interval=0.4, confidence=None):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.locate_box(image_path, region=region, confidence=confidence):
                return True
            time.sleep(check_interval)
        return False

    def press_escape_reliable(self):
        print("   > Нажимаю ESC (Усиленный метод)...")

        sw, sh = pyautogui.size()
        pydirectinput.moveTo(sw // 2, sh // 2)
        pydirectinput.click()
        time.sleep(0.2)

        pyautogui.keyDown('esc')
        time.sleep(0.1)
        pyautogui.keyUp('esc')

        time.sleep(0.5)

        pydirectinput.keyDown('esc')
        time.sleep(0.15)
        pydirectinput.keyUp('esc')

        time.sleep(1.0)

    # === ЛОГИКА ОШИБОК И ОЖИДАНИЯ ===

    def wait_for_next_level(self):
        """Бесконечный цикл ожидания конца матча (кнопки Next Level)."""
        print("> Запущен цикл ожидания конца матча (Next Level)...")
        while True:
            time.sleep(0.15)
            if self.locate_box(BTN_NEXT_LEVEL, confidence=0.85):
                print("> Бой окончен (найден Next Level)")
                return True

    def check_global_errors(self):
        # 1. Error Occurred -> Рестарт лобби
        if self.locate_box(BTN_ERROR_OCCURED, confidence=0.85):
            print("! [ERROR OCCURED] Найдена критическая ошибка -> Жму C и перезапускаю лобби")
            pydirectinput.press('c')
            time.sleep(1.0)
            return "RESET_LOBBY"

        # 2. Game Still Progress -> Обработка
        if self.locate_box(BTN_GAME_STILL_PROGRESS, confidence=0.85):
            print("! [GAME STILL PROGRESS] Обнаружено -> Жму C")
            pydirectinput.press('c')
            time.sleep(0.8)
            if self.locate_box(BTN_CHECK_INGAME, confidence=0.80):
                print("! [CHECK INGAME] Мы все еще в матче -> Жду завершения (Next Level)")
                self.wait_for_next_level()
            return "HANDLED"

        return None

    # === ОСНОВНАЯ ЛОГИКА ===

    def bot_exist_present(self):
        return bool(self.locate_box(BTN_BOT_EXIST, region=BOT_EXIST_REGION))

    def full_setup_new_lobby(self):
        print("--- SETUP: NEW LOBBY ---")
        if self.check_global_errors() == "RESET_LOBBY":
            return False

        if self.find_and_click(BTN_CUSTOM_INACTIVE, move_delay=0.05):
            time.sleep(0.2)
            return False
        self.find_and_click(BTN_CUSTOM_ACTIVE, move_delay=0.05)
        time.sleep(0.2)

        if self.check_global_errors() == "RESET_LOBBY":
            return False

        self.find_and_click(BTN_CREATE_INACTIVE) or self.find_and_click(BTN_CREATE_ACTIVE)
        time.sleep(0.2)
        self.find_and_click(BTN_PRIVATE_INACTIVE) or self.find_and_click(BTN_PRIVATE_ACTIVE)
        time.sleep(0.8)

        # 1. Добавление бота
        self.find_and_click(BTN_ADD_BOT)
        time.sleep(0.2)
        pydirectinput.press('x')
        time.sleep(0.5)

        # 2. Правила
        if not self.find_hover_press_keys(BTN_GAMEMODE_INACT, 'a', 6):
            self.find_hover_press_keys(BTN_GAMEMODE_ACT, 'a', 6)
        self.find_hover_press_keys(BTN_DAMAGE_INACT, 'a', 6)
        self.find_hover_press_keys(BTN_MATCHTIME_INACT, 'd', 5)
        self.find_hover_press_keys(BTN_LIVES_INACT, 'a', 3)
        time.sleep(0.3)

        # 3. Настройки лобби
        if self.find_and_click(BTN_SETTINGS_LOBBY):
            print("   > Настройки лобби открыты, жду 1.5 сек...")
            time.sleep(1.5)

            self.find_hover_press_keys(BTN_FRIENDS_INACT, 'd', 1)
            time.sleep(0.3)
            self.find_hover_press_keys(BTN_GUILD_INACT, 'd', 1)
            time.sleep(0.3)

            if not self.find_hover_press_keys(BTN_HANDICAPS_INACT, 'd', 1):
                print("   ! Handicaps не найден с первого раза, пробую снова...")
                time.sleep(0.5)
                self.find_hover_press_keys(BTN_HANDICAPS_INACT, 'd', 1)

            time.sleep(0.2)
            pydirectinput.press('x')
            time.sleep(0.5)

        # 4. Handicaps БОТА
        bot_found = self.find_and_click(BTN_BOT_EXIST, region=None, move_delay=0.1, confidence=0.75)
        if bot_found:
            print("   > Бот найден, ждем меню...")
            time.sleep(1.2)
            self.click_image_multiple(BTN_DIFF_BOT, 1, delay=0.15, confidence=0.80)
            time.sleep(0.2)
            self.click_image_multiple(BTN_HANDICAP_TAKEN_BOT, 6, delay=0.12, confidence=0.90)
            time.sleep(0.15)
            self.click_image_multiple(BTN_HANDICAP_DONE_BOT, 5, delay=0.12, confidence=0.90)
            time.sleep(0.3)
        else:
            print("   ! БОТ НЕ НАЙДЕН")

        # 5. Handicaps ИГРОКА
        if self.find_and_click(BTN_PLAYER):
            print("   > Игрок найден, ждем меню...")
            time.sleep(0.8)
            if not self.locate_box(BTN_HANDICAP_TAKEN, confidence=0.90):
                self.find_and_click(BTN_PLAYER)
                time.sleep(0.8)
            self.click_image_multiple(BTN_HANDICAP_TAKEN, 5, delay=0.12, confidence=0.90)
            time.sleep(0.15)
            self.click_image_multiple(BTN_HANDICAP_DONE, 6, delay=0.12, confidence=0.90)
            time.sleep(0.3)

        return True

    def start_match_cycle(self):
        print("--- START MATCH ---")
        self.match_start_time = time.time()
        time.sleep(0.6)

        if self.check_global_errors() == "RESET_LOBBY":
            return False

        char_ok = (
            self.click_image_multiple(BTN_CHAR_UNHOVER, 2, delay=0.12)
        )
        if not char_ok:
            print("! Персонаж не найден")
            return False

        time.sleep(1.2)
        pydirectinput.press('c')
        time.sleep(0.8)

        if not self.find_and_click(BTN_MAP_CHOOSING):
            print("! Карта не найдена")
            return False

        checkifrejoined = False

        print("> Жду загрузку боя...")
        ingame_detected = False
        for _ in range(30):
            if self.locate_box(BTN_CHECK_INGAME, confidence=0.80):
                print("> ОБНАРУЖЕН CHECK_INGAME: Матч начался!")
                ingame_detected = True
                break
            time.sleep(0.5)

        if not ingame_detected:
            print("> Тайм-аут ожидания checkifingame, пробую нажимать ESC наугад...")

        time.sleep(1.0)
        print("> БОЙ НАЧАЛСЯ (Logic started)")
        time.sleep(5.0)

        # === ЛОГИКА ВЫХОДА ИЗ МАТЧА ===
        if not checkifrejoined:
            self.press_escape_reliable()

            if self.find_and_click(BTN_LEAVE_MATCH, confidence=0.80):
                print("   > Leave Match нажат.")
                checkifrejoined = True
                time.sleep(3.0)

                if self.locate_box(BTN_GAME_STILL_PROGRESS, confidence=0.85):
                    print("   ! Game Still Progress (после выхода) -> Жму C")
                    pydirectinput.press('c')

                print("   > Жду 3 секунды...")
                time.sleep(3.0)
            else:
                print("   ! Leave Match не найден (возможно меню не открылось).")

        self.wait_for_next_level()

        self.match_count += 1
        time.sleep(1.5)
        self.find_and_click(BTN_NEXT_AFTERMATCH)
        time.sleep(0.1)
        print("> Жду уровень (3.5 сек)...")
        time.sleep(3.5)

        try:
            sw, sh = pyautogui.size()
            region_crop = (int(sw * 0.20), int(sh * 0.14), int(sw * 0.57), int(sh * 0.41))

            ts = datetime.datetime.now().strftime('%H-%M-%S')
            img_path = os.path.join(LEVELS_FOLDER, f"level_{ts}.png")
            pyautogui.screenshot(img_path, region=region_crop)
            print("> Скриншот сохранен")
            self.send_webhook(img_path)
        except Exception as e:
            print(f"! Ошибка скриншота: {e}")

        print("> Выход в лобби...")
        pydirectinput.press('c')
        time.sleep(0.5)
        self.find_and_click(BTN_NEXT_LEVEL)

        time.sleep(0.8)
        self.wait_for_image(BTN_BOT_EXIST, timeout=30, region=BOT_EXIST_REGION)
        time.sleep(0.5)
        return True

    def main_loop(self):
        print("[START] Бот запущен [v37.0 - Auto Resize Edition]\n")
        self.start_time = time.time()
        self.setup_done_once = False

        while True:
            status = self.check_global_errors()
            if status == "RESET_LOBBY":
                print("! Сброс статуса настройки (RESTART LOBBY)")
                self.setup_done_once = False
                time.sleep(1.0)
                continue

            if not self.setup_done_once:
                if self.full_setup_new_lobby():
                    self.setup_done_once = True
                    self.start_match_cycle()
                else:
                    self.setup_done_once = False
                time.sleep(0.5)
                continue

            if self.bot_exist_present():
                result = self.start_match_cycle()
                if result is False:
                    self.setup_done_once = False
                time.sleep(0.5)
                continue

            self.setup_done_once = False
            time.sleep(0.5)


if __name__ == "__main__":
    bot = AutoExpBot()
    try:
        bot.main_loop()
    except KeyboardInterrupt:
        total_time = time.time() - bot.start_time if bot.start_time else 0
        print(f"\n[STOP] Всего матчей: {bot.match_count}, Время работы: {bot.format_time(total_time)}")