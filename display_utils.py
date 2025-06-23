import time
import cv2
import sys
import random
from screeninfo import get_monitors
import numpy as np
import json
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display
from text_renderer import TextRenderer
from transition_manager import TransitionManager
from prompt_generator import PromptGenerator
from data_loader import DataLoader


class DisplayManager:
    def __init__(self, window_name='Mirror on the Wall'):
        self.window_name = window_name
        self.screen_width = 0
        self.screen_height = 0
        self._setup_screen_dimensions()
        self.show_json_overlay = False
        self.last_json_data = None
        self.frame_count = 0
        self.text_positions = {}
        self.show_grid = False
        self.grid_cols = 4
        self.grid_rows = 4
        self.occupied_cells = set()
        self.cell_last_used = {}
        self.target_mode = "visual"  # מצב יעד למעבר
        self.scene_transition = False  # האם זה מעבר סצנה
        self.show_timer = False
        self.show_info = False
        self.start_time = time.time()
        self.current_active_persons = []  # רשימת אנשים פעילים נוכחית

        # הוספת משתנים למאגר השני
        self.display_mode = "visual"  # "visual" או "behavioral" או "prompt"
        self.behavioral_text_positions = {}
        self.behavioral_occupied_cells = set()
        self.behavioral_cell_last_used = {}
        self.mode_transition_time = None
        self.transition_duration = 2.0  # שניות למעבר

        # מעבר הדרגתי
        self.in_transition = False
        self.transition_stage = 0  # שלב במעבר
        self.texts_to_fade_out = []  # רשימת טקסטים להעלמה
        self.texts_to_fade_in = []  # רשימת טקסטים להופעה
        self.last_transition_step_time = 0

        # מחזור טקסטים התנהגותיים
        self.behavioral_cycle_enabled = True
        self.last_behavioral_text_add = 0
        self.behavioral_add_interval = 0.3  # מהיר יותר - 0.3 שניות
        self.behavioral_texts_pool = []  # מאגר הטקסטים למחזור
        self.behavioral_pool_index = 0  # אינדקס נוכחי במאגר
        self.min_active_behavioral_texts = 10  # מינימום טקסטים פעילים
        self.max_active_behavioral_texts = 10  # מקסימום טקסטים פעילים

        # גישה ישירה לנתונים התנהגותיים
        self.behavioral_data_saver_ref = None

        # משתנים חדשים לטיימר אוטומטי ומצב פרומפט
        self.auto_mode_timer = time.time()  # טיימר למעבר אוטומטי
        # זמנים שונים לכל מצב - מעודכנים לסה"כ 60 שניות
        self.visual_duration = 30.0  # 30 שניות למצב חזותי (ירוק)
        self.behavioral_duration = 15.0  # 15 שניות למצב התנהגותי (לבן)
        self.prompt_duration = 15.0  # 15 שניות למצב פרומפט
        self.prompt_text = ""  # הטקסט של הפרומפט
        self.prompt_display_index = 0  # אינדקס לאפקט הקלדה
        self.prompt_last_char_time = 0  # זמן אחרון שהוספנו תו
        self.prompt_generated = False  # האם הפרומפט כבר נוצר
        self.visual_data_path = None  # נתיב לנתונים חזותיים
        self.behavioral_data_path = None  # נתיב לנתונים התנהגותיים
        self.all_behavioral_added = False  # האם כל המשפטים הוספו
        self.prompt_transition_time = None  # זמן המעבר לפרומפט
        # איתחול משתנים למעקב אחרי מצב behavioral
        self.behavioral_fadeout_started = False  # האם התחיל fade out

        # יצירת מופעים של המחלקות החדשות
        self.text_renderer = TextRenderer()
        self.transition_manager = TransitionManager()
        self.prompt_generator = PromptGenerator()
        self.data_loader = DataLoader()

    def set_behavioral_data_saver(self, behavioral_data_saver):
        """קובע הפניה לשומר הנתונים ההתנהגותיים"""
        self.behavioral_data_saver_ref = behavioral_data_saver

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def toggle_timer(self):
        self.show_timer = not self.show_timer

    def toggle_info(self):
        self.show_info = not self.show_info

    def toggle_display_mode(self):
        """מחליף בין מאגר חזותי למאגר התנהגותי עם מעבר הדרגתי"""
        print(f"🔄 MODE SWITCH: {self.display_mode} → ", end="")

        if self.in_transition:
            print("(blocked - in transition)")
            return  # מונע מעבר נוסף במהלך מעבר קיים

        # אם במצב פרומפט - חזור למצב חזותי
        if self.display_mode == "prompt":
            self.display_mode = "visual"
            self.auto_mode_timer = time.time()
            self.prompt_generated = False
            self.prompt_display_index = 0
            self.prompt_text = ""
            print("visual (restarting cycle)")
            return

        current_time = time.time()
        self.mode_transition_time = current_time
        self.last_transition_step_time = current_time
        self.in_transition = True
        self.transition_stage = 0

        if self.display_mode == "visual":
            self.target_mode = "behavioral"
            print("behavioral")
            # הכן רשימת טקסטים להעלמה מהמאגר החזותי
            self.texts_to_fade_out = list(self.text_positions.keys()).copy()
            random.shuffle(self.texts_to_fade_out)  # סדר רנדומלי
        else:
            self.target_mode = "visual"
            print("visual")
            # הכן רשימת טקסטים להעלמה מהמאגר ההתנהגותי
            self.texts_to_fade_out = list(self.behavioral_text_positions.keys()).copy()
            random.shuffle(self.texts_to_fade_out)  # סדר רנדומלי

        # איפוס הטיימר האוטומטי
        self.auto_mode_timer = current_time

    def toggle_json_overlay(self):
        self.show_json_overlay = not self.show_json_overlay
        print(f"📊 OVERLAY: {'ON' if self.show_json_overlay else 'OFF'}")

    def _setup_screen_dimensions(self):
        monitor = get_monitors()[0]
        self.screen_width = monitor.width
        self.screen_height = monitor.height

    def setup_window(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def show_frame(self, frame, json_data_path, behavioral_data_path, active_persons=None):
        """הצגת פריים עם נתוני JSON ונתונים התנהגותיים"""

        self.frame_count += 1
        # שמירת רשימת האנשים הפעילים
        self.current_active_persons = active_persons if active_persons else []

        # שמירת נתיבי הקבצים
        self.visual_data_path = json_data_path
        self.behavioral_data_path = behavioral_data_path

        frame_height, frame_width, _ = frame.shape
        frame = cv2.flip(frame, 1)

        aspect_ratio_frame = frame_width / frame_height
        aspect_ratio_screen = self.screen_width / self.screen_height

        if aspect_ratio_frame > aspect_ratio_screen:
            new_width = self.screen_width
            new_height = int(new_width / aspect_ratio_frame)
        else:
            new_height = self.screen_height
            new_width = int(new_height * aspect_ratio_frame)

        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        full_screen_frame = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)

        x_offset = (self.screen_width - new_width) // 2
        y_offset = (self.screen_height - new_height) // 2

        full_screen_frame[y_offset:y_offset + new_height,
        x_offset:x_offset + new_width] = resized_frame

        # --- הוספת שכבת נתוני JSON אם הדגל פעיל ---
        if self.show_json_overlay:
            black_screen = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)

            # בדיקת טיימר אוטומטי למעבר בין מצבים
            current_time = time.time()

            # בדיקת טיימר אוטומטי למעבר בין מצבים אם לא במעבר כרגע
            if not self.in_transition:
                time_in_mode = current_time - self.auto_mode_timer

                # למצב visual - עבור אחרי 30 שניות
                if self.display_mode == "visual":
                    if time_in_mode >= self.visual_duration:
                        # מעבר אוטומטי ל-behavioral אחרי 30 שניות
                        print("🔄 AUTO MODE SWITCH: visual → behavioral (after 30s)")
                        self.toggle_display_mode()
                        self.auto_mode_timer = current_time

                # למצב behavioral - עבור אחרי 15 שניות
                elif self.display_mode == "behavioral":
                    # בדוק אם צריך להתחיל fade out (5 שניות לפני הסוף)
                    if time_in_mode >= (self.behavioral_duration - 5.0) and not self.behavioral_fadeout_started:
                        self._start_behavioral_fadeout(current_time)
                        self.behavioral_fadeout_started = True

                    # מעבר אוטומטי ל-prompt אחרי 15 שניות
                    if time_in_mode >= self.behavioral_duration:
                        print("🔄 AUTO MODE SWITCH: behavioral → prompt (after 15s)")
                        self.display_mode = "prompt"
                        self.auto_mode_timer = current_time
                        self.prompt_generated = False
                        self.prompt_display_index = 0
                        # נקה את כל המשפטים הלבנים
                        self.behavioral_text_positions.clear()
                        self.behavioral_occupied_cells.clear()
                        if hasattr(self, 'behavioral_fadeout_started'):
                            delattr(self, 'behavioral_fadeout_started')

                # למצב prompt - עבור אחרי 15 שניות
                elif self.display_mode == "prompt":
                    if time_in_mode >= self.prompt_duration:
                        # חזרה למצב חזותי אחרי 15 שניות
                        print("🔄 AUTO MODE SWITCH: prompt → visual (after 15s)")
                        self.display_mode = "visual"
                        self.auto_mode_timer = current_time
                        self.prompt_generated = False
                        self.prompt_display_index = 0
                        self.prompt_text = ""

            # עיבוד מעבר הדרגתי
            self.transition_manager.process_gradual_transition(self, current_time)

            # בדיקה מיוחדת למעבר לפרומפט כשאין משפטים לבנים
            if self.display_mode == "behavioral" and not self.in_transition:
                # ספור כמה משפטים פעילים יש
                active_behavioral_count = 0
                for text_key, data in self.behavioral_text_positions.items():
                    elapsed = current_time - data['start_time']
                    if elapsed < data.get('lifetime', 8.0):
                        active_behavioral_count += 1

                # בדוק אם כל המשפטים הוספו
                all_added = getattr(self, 'behavioral_pool_index', 0) >= len(self.behavioral_texts_pool)

                # דיבאג כל 30 פריימים
                if self.frame_count % 30 == 0:
                    print(
                        f"📊 Behavioral: active={active_behavioral_count}, added={getattr(self, 'behavioral_pool_index', 0)}/{len(self.behavioral_texts_pool)}, all_added={all_added}")

                # מעבר לפרומפט אם אין משפטים פעילים וכל המשפטים הוספו
                if all_added and active_behavioral_count == 0 and len(self.behavioral_texts_pool) > 0:
                    print(f"🎬 All behavioral texts gone!")
                    print("🔄 IMMEDIATE TRANSITION: behavioral → prompt")
                    self.display_mode = "prompt"
                    self.auto_mode_timer = current_time
                    self.prompt_generated = False
                    self.prompt_display_index = 0
                    self.behavioral_text_positions.clear()
                    self.behavioral_occupied_cells.clear()
                    self.behavioral_pool_index = 0  # איפוס האינדקס
                    if hasattr(self, 'behavioral_fadeout_started'):
                        delattr(self, 'behavioral_fadeout_started')

            if self.display_mode == "visual" and not self.in_transition:
                data_lines = self.data_loader.get_visual_data_lines(json_data_path)
                self._display_visual_texts(black_screen, data_lines)
            elif self.display_mode == "behavioral" and not self.in_transition:
                data_lines = self.data_loader.get_behavioral_data_lines(self, behavioral_data_path)
                self._display_behavioral_texts(black_screen, data_lines)
            elif self.display_mode == "prompt":
                # הצגת הפרומפט עם אפקט הקלדה
                self.prompt_generator.display_prompt_with_typewriter(self, black_screen, current_time)
            elif self.in_transition:
                # במהלך מעבר - הצג את שני הסוגים עם fade out/in
                self.transition_manager.display_transition_texts(self, black_screen, json_data_path,
                                                                 behavioral_data_path)

            full_screen_frame = black_screen

        # הצגת גריד אם מופעל
        if self.show_grid:
            cell_width = self.screen_width // self.grid_cols
            cell_height = self.screen_height // self.grid_rows

            for i in range(1, self.grid_cols):
                x = i * cell_width
                cv2.line(full_screen_frame, (x, 0), (x, self.screen_height), (50, 50, 50), 1)

            for i in range(1, self.grid_rows):
                y = i * cell_height
                cv2.line(full_screen_frame, (0, y), (self.screen_width, y), (50, 50, 50), 1)

        # הצגת טיימר
        if self.show_timer:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            timer_text = f"{minutes:02d}:{seconds:02d}"
            cv2.putText(full_screen_frame, timer_text, (self.screen_width - 150, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

        # הצגת מידע
        if self.show_info:
            info_lines = []

            # קבל מידע על הסצנה הנוכחית
            current_scene_id = "001"  # ברירת מחדל

            # קרא את הנתונים מהקובץ
            if os.path.exists(json_data_path):
                try:
                    with open(json_data_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        sessions = json_data.get("sessions", [])
                        if sessions:
                            latest_session = sessions[-1]
                            current_scene_id = latest_session.get("session_id", "001")
                except:
                    pass

            # הוסף את המידע לתצוגה
            info_lines.append(f"Scene: {current_scene_id}")

            # מספר אנשים פעילים
            if hasattr(self, 'current_active_persons') and self.current_active_persons:
                info_lines.append(f"Persons in frame: {len(self.current_active_persons)}")
                person_ids_str = ", ".join([str(pid) for pid in self.current_active_persons])
                info_lines.append(f"Person IDs: {person_ids_str}")
            else:
                info_lines.append(f"Persons in frame: 0")

            # הוסף מידע על המצב הנוכחי והזמן שנותר
            # קבע את משך הזמן לפי המצב הנוכחי
            if self.display_mode == "visual":
                mode_duration = self.visual_duration
            elif self.display_mode == "behavioral":
                mode_duration = self.behavioral_duration
            elif self.display_mode == "prompt":
                mode_duration = self.prompt_duration
            else:
                mode_duration = 30.0

            time_in_mode = current_time - self.auto_mode_timer
            time_remaining = max(0, mode_duration - time_in_mode)
            info_lines.append(f"Mode: {self.display_mode}")
            info_lines.append(f"Time left: {int(time_remaining)}s")

            # הצג את המידע
            y_offset = 100
            for line in info_lines:
                # רקע שחור מאחורי הטקסט
                text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
                cv2.rectangle(full_screen_frame,
                              (self.screen_width - 350, y_offset - 25),
                              (self.screen_width - 350 + text_size[0] + 10, y_offset + 5),
                              (0, 0, 0), -1)

                # הטקסט עצמו
                cv2.putText(full_screen_frame, line, (self.screen_width - 340, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
                y_offset += 35

        # --- נהל מחזור טקסטים התנהגותיים תמיד ---
        if self.show_json_overlay and self.display_mode == "behavioral":
            current_time = time.time()
            # קבל נתונים זמינים
            available_data = []
            if self.behavioral_data_saver_ref:
                available_data = self.behavioral_data_saver_ref.get_persistent_insights()

            # נהל את המחזור
            self._manage_behavioral_cycle(current_time, available_data)

        cv2.imshow(self.window_name, full_screen_frame)

    def _get_visual_data_lines(self, json_data_path):
        """קבלת נתונים חזותיים מהמאגר הראשון"""
        return self.data_loader.get_visual_data_lines(json_data_path)

    def _get_behavioral_data_lines(self, behavioral_data_path):
        """קבלת נתונים התנהגותיים מהמאגר השני"""
        return self.data_loader.get_behavioral_data_lines(self, behavioral_data_path)

    def _display_visual_texts(self, black_screen, data_lines):
        """הצגת טקסטים חזותיים (המאגר הראשון)"""
        pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        current_time = time.time()

        try:
            font_base = ImageFont.load_default()
        except:
            font_base = None

        # נקה טקסטים שפג זמנם
        self.text_renderer.cleanup_expired_texts(self, current_time, self.text_positions, self.occupied_cells,
                                                 self.cell_last_used,
                                                 is_behavioral=False)

        # הוסף טקסטים חדשים או עדכן קיימים
        for line in data_lines:
            if line.strip():
                line_key = line.strip()
                if line_key not in self.text_positions:
                    self.text_renderer.add_new_text(self, line_key, current_time, self.text_positions,
                                                    self.occupied_cells,
                                                    self.cell_last_used, is_behavioral=False)

        # צייר את כל הטקסטים עם צבעים של המאגר הראשון
        self.text_renderer.draw_texts(self, draw, font_base, current_time, self.text_positions, is_behavioral=False)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def _display_behavioral_texts(self, black_screen, data_lines):
        """הצגת טקסטים התנהגותיים (המאגר השני)"""
        pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        current_time = time.time()

        try:
            font_base = ImageFont.load_default()
        except:
            font_base = None

        # נקה טקסטים שפג זמנם
        self.text_renderer.cleanup_expired_texts(self, current_time, self.behavioral_text_positions,
                                                 self.behavioral_occupied_cells, self.behavioral_cell_last_used,
                                                 is_behavioral=True)

        # עדכן את המאגר אם יש נתונים חדשים
        if data_lines and len(data_lines) > len(self.behavioral_texts_pool):
            self.behavioral_texts_pool = [line.strip() for line in data_lines if line.strip()]

        # צייר את כל הטקסטים עם צבע לבן
        self.text_renderer.draw_texts(self, draw, font_base, current_time, self.behavioral_text_positions,
                                      is_behavioral=True)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def _start_behavioral_fadeout(self, current_time):
        """מתחיל fade out לכל המשפטים הלבנים"""
        for text_key in self.behavioral_text_positions:
            if 'fade_out_start' not in self.behavioral_text_positions[text_key]:
                self.behavioral_text_positions[text_key]['fade_out_start'] = current_time
                self.behavioral_text_positions[text_key]['fade_out_duration'] = 2.0  # 2 שניות fade out
        print(f"🌅 Starting fade out for {len(self.behavioral_text_positions)} behavioral texts")

    def _manage_behavioral_cycle(self, current_time, data_lines):
        """מנהל מחזור של טקסטים התנהגותיים"""
        if not self.behavioral_cycle_enabled:
            return

        # עדכן את מאגר הטקסטים מהנתונים הזמינים
        if data_lines and len(data_lines) > 0:
            quality_texts = [line.strip() for line in data_lines if line.strip() and len(line.strip()) > 5]
            if len(quality_texts) > len(self.behavioral_texts_pool):
                self.behavioral_texts_pool = quality_texts
                print(f"📝 POOL UPDATED: {len(self.behavioral_texts_pool)} texts")

        # אם אין מאגר טקסטים - נסה לטעון מהקובץ
        if not self.behavioral_texts_pool and self.behavioral_data_saver_ref:
            available_insights = self.behavioral_data_saver_ref.get_persistent_insights()
            if available_insights:
                self.behavioral_texts_pool = available_insights
                print(f"📝 POOL LOADED: {len(self.behavioral_texts_pool)} texts from cache")

        # ספור טקסטים פעילים
        active_count = len(self.behavioral_text_positions)

        # תנאים להוספת טקסט חדש
        time_since_last_add = current_time - self.last_behavioral_text_add

        # הוסף משפט חדש כל שנייה
        add_interval = 1.0

        should_add_text = False

        # אין טקסטים פעילים - הוסף מיד
        if active_count == 0 and self.behavioral_texts_pool and self.behavioral_pool_index < len(
                self.behavioral_texts_pool):
            should_add_text = True
            print("🚀 NO ACTIVE TEXTS - Adding immediately")

        # הוסף עד שנגמר המאגר
        elif (time_since_last_add >= add_interval and
              self.behavioral_texts_pool and
              self.behavioral_pool_index < len(self.behavioral_texts_pool)):
            should_add_text = True
            print(f"⚡ ADDING TEXT ({self.behavioral_pool_index + 1}/{len(self.behavioral_texts_pool)})")

        if should_add_text:
            # קח טקסט חדש
            if self.behavioral_pool_index < len(self.behavioral_texts_pool):
                text_to_add = self.behavioral_texts_pool[self.behavioral_pool_index]

                if text_to_add not in self.behavioral_text_positions:
                    # זמן חיים של 8 שניות בדיוק
                    lifetime = 8.0

                    self.text_renderer.add_new_text_with_lifetime(self, text_to_add, current_time, lifetime,
                                                                  self.behavioral_text_positions,
                                                                  self.behavioral_occupied_cells,
                                                                  self.behavioral_cell_last_used,
                                                                  is_behavioral=True)
                    self.last_behavioral_text_add = current_time
                    self.behavioral_pool_index += 1
                    print(f"➕ ADD TEXT #{self.behavioral_pool_index} (active: {active_count + 1})")
                else:
                    self.behavioral_pool_index += 1