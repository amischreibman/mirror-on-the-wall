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


class DisplayManager:
    # === הגדרות שליטה לטקסט ===
    FADE_IN_TIME = 3.0
    STABLE_TIME = 4.0
    FADE_OUT_TIME = 1.0
    TOTAL_LIFETIME = 8.0
    CELL_COOLDOWN = 3.0

    # הגדרות זמן למאגר השני (התנהגותי)
    BEHAVIORAL_MIN_LIFETIME = 6.0  # מינימום 6 שניות
    BEHAVIORAL_MAX_LIFETIME = 12.0  # מקסימום 12 שניות

    # הגדרות גודל פונט
    MIN_FONT_SIZE = 14
    MAX_FONT_SIZE = 25
    FONT_RANDOM_RANGE = 30

    # הגדרות צבע למאגר הראשון (RGB)
    COLOR_MIN_R = 0
    COLOR_MAX_R = 50
    COLOR_MIN_G = 150
    COLOR_MAX_G = 255
    COLOR_MIN_B = 0
    COLOR_MAX_B = 100

    # הגדרות צבע למאגר השני (לבן)
    BEHAVIORAL_COLOR = (255, 255, 255)  # לבן

    # הגדרות גריד
    GRID_COLS = 4
    GRID_ROWS = 4

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
        self.grid_cols = self.GRID_COLS
        self.grid_rows = self.GRID_ROWS
        self.occupied_cells = set()
        self.cell_last_used = {}
        self.target_mode = "visual"  # מצב יעד למעבר
        self.scene_transition = False  # האם זה מעבר סצנה
        self.show_timer = False
        self.show_info = False
        self.start_time = time.time()
        self.current_active_persons = []  # רשימת אנשים פעילים נוכחית

        # הוספת משתנים למאגר השני
        self.display_mode = "visual"  # "visual" או "behavioral"
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
        self.transition_step_interval = 0.5  # חצי שניה בין כל שלב

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        print(f"Grid display: {'ON' if self.show_grid else 'OFF'}")

    def toggle_timer(self):
        self.show_timer = not self.show_timer
        print(f"Timer display: {'ON' if self.show_timer else 'OFF'}")

    def toggle_info(self):
        self.show_info = not self.show_info
        print(f"Info display: {'ON' if self.show_info else 'OFF'}")

    def toggle_display_mode(self):
        """מחליף בין מאגר חזותי למאגר התנהגותי עם מעבר הדרגתי"""
        if self.in_transition:
            return  # מונע מעבר נוסף במהלך מעבר קיים

        current_time = time.time()
        self.mode_transition_time = current_time
        self.last_transition_step_time = current_time
        self.in_transition = True
        self.transition_stage = 0

        if self.display_mode == "visual":
            print("Starting gradual transition to BEHAVIORAL analysis mode")
            # הכן רשימת טקסטים להעלמה מהמאגר החזותי
            self.texts_to_fade_out = list(self.text_positions.keys()).copy()
            random.shuffle(self.texts_to_fade_out)  # סדר רנדומלי
            self.target_mode = "behavioral"
        else:
            print("Starting gradual transition to VISUAL description mode")
            # הכן רשימת טקסטים להעלמה מהמאגר ההתנהגותי
            self.texts_to_fade_out = list(self.behavioral_text_positions.keys()).copy()
            random.shuffle(self.texts_to_fade_out)  # סדר רנדומלי
            self.target_mode = "visual"

    def trigger_scene_transition(self):
        """מפעיל מעבר הדרגתי לסצנה חדשה"""
        if self.in_transition:
            return

        current_time = time.time()
        self.in_transition = True
        self.transition_stage = 0
        self.last_transition_step_time = current_time
        self.target_mode = self.display_mode  # נשאר באותו מצב

        # הכן רשימת כל הטקסטים להעלמה
        all_texts = []

        if self.display_mode == "visual":
            all_texts.extend(list(self.text_positions.keys()))
        else:
            all_texts.extend(list(self.behavioral_text_positions.keys()))

        random.shuffle(all_texts)
        self.texts_to_fade_out = all_texts
        self.texts_to_fade_in = []  # יתמלא מאוחר יותר עם נתונים חדשים
        self.scene_transition = True

        print(f"Scene transition started - fading out {len(all_texts)} texts")

    def _process_gradual_transition(self, current_time):
        """מעבד מעבר הדרגתי בין מאגרים"""
        if not self.in_transition:
            return

        # בדוק אם הגיע הזמן לשלב הבא
        if current_time - self.last_transition_step_time >= self.transition_step_interval:

            # שלב ראשון: הכן רשימת טקסטים חדשים אם צריך
            if self.transition_stage == 0:
                self._prepare_new_texts_for_transition(current_time)
                self.transition_stage = 1
                self.last_transition_step_time = current_time
                return

            # שלב עיקרי: העלם ביטוי אחד והוסף אחד חדש
            if self.texts_to_fade_out or (hasattr(self, 'texts_to_fade_in') and self.texts_to_fade_in):

                # העלם ביטוי אחד אם יש
                if self.texts_to_fade_out:
                    text_to_remove = self.texts_to_fade_out.pop(0)
                    self._start_text_fade_out(text_to_remove, current_time)
                    print(f"Fading out text #{len(self.texts_to_fade_out)} remaining")

                # הוסף ביטוי חדש אחד אם יש
                if hasattr(self, 'texts_to_fade_in') and self.texts_to_fade_in:
                    new_text = self.texts_to_fade_in.pop(0)
                    self._start_text_fade_in(new_text, current_time)
                    print(f"Fading in new text, {len(self.texts_to_fade_in)} remaining")

                # עדכן זמן השלב הבא
                self.last_transition_step_time = current_time

            # בדוק אם המעבר הסתיים
            if not self.texts_to_fade_out and (not hasattr(self, 'texts_to_fade_in') or not self.texts_to_fade_in):
                # המתן שנייה נוספת לפני סיום כדי לוודא שכל ה-fade out הסתיימו
                if current_time - self.last_transition_step_time >= 1.5:
                    self._complete_transition()

    def _prepare_new_texts_for_transition(self, current_time):
        """מכין רשימת טקסטים חדשים להופעה"""
        if self.target_mode == "behavioral":
            # קבל נתונים התנהגותיים זמינים
            self.texts_to_fade_in = self._get_prepared_behavioral_texts()
        else:
            # קבל נתונים חזותיים זמינים
            self.texts_to_fade_in = self._get_prepared_visual_texts()

        if self.texts_to_fade_in:
            random.shuffle(self.texts_to_fade_in)  # סדר רנדומלי
            print(f"Prepared {len(self.texts_to_fade_in)} texts for fade in")

        # גם הכן את רשימת ההעלמה בסדר רנדומלי אם לא הוכנה
        if not self.texts_to_fade_out:
            if self.display_mode == "visual":
                self.texts_to_fade_out = list(self.text_positions.keys()).copy()
            else:
                self.texts_to_fade_out = list(self.behavioral_text_positions.keys()).copy()

            if self.texts_to_fade_out:
                random.shuffle(self.texts_to_fade_out)
                print(f"Prepared {len(self.texts_to_fade_out)} texts for fade out")

    def _get_prepared_behavioral_texts(self):
        """מחזיר רשימת טקסטים התנהגותיים מוכנה"""
        # זה יעבוד רק אם יש נתונים זמינים
        if hasattr(self, '_cached_behavioral_data'):
            return self._cached_behavioral_data.copy()
        return []

    def _get_prepared_visual_texts(self):
        """מחזיר רשימת טקסטים חזותיים מוכנה"""
        # זה יעבוד רק אם יש נתונים זמינים
        if hasattr(self, '_cached_visual_data'):
            return self._cached_visual_data.copy()
        return []

    def _start_text_fade_out(self, text_key, current_time):
        """מתחיל fade out לטקסט ספציפי"""
        if self.display_mode == "visual" and text_key in self.text_positions:
            # קבע זמן התחלה של fade out
            self.text_positions[text_key]['fade_out_start'] = current_time
            self.text_positions[text_key]['fade_out_duration'] = 1.0  # שנייה אחת
            print(f"Starting fade out for visual text: {text_key[:30]}...")
        elif self.display_mode == "behavioral" and text_key in self.behavioral_text_positions:
            # קבע זמן התחלה של fade out
            self.behavioral_text_positions[text_key]['fade_out_start'] = current_time
            self.behavioral_text_positions[text_key]['fade_out_duration'] = 1.0  # שנייה אחת
            print(f"Starting fade out for behavioral text: {text_key[:30]}...")

    def _start_text_fade_in(self, text_key, current_time):
        """מתחיל fade in לטקסט חדש"""
        if self.target_mode == "behavioral":
            self._add_new_text(text_key, current_time, self.behavioral_text_positions,
                               self.behavioral_occupied_cells, self.behavioral_cell_last_used, is_behavioral=True)
            print(f"Starting fade in for behavioral text: {text_key[:30]}...")
        else:
            self._add_new_text(text_key, current_time, self.text_positions,
                               self.occupied_cells, self.cell_last_used, is_behavioral=False)
            print(f"Starting fade in for visual text: {text_key[:30]}...")

    def _complete_transition(self):
        """משלים את המעבר"""
        self.display_mode = self.target_mode
        self.in_transition = False
        self.transition_stage = 0

        # נקה טקסטים ישנים שסיימו fade out
        self._cleanup_faded_texts()

        print(f"Transition completed to {self.display_mode} mode")

    def _cleanup_faded_texts(self):
        """מנקה טקסטים שסיימו fade out"""
        current_time = time.time()

        # נקה טקסטים חזותיים
        keys_to_remove = []
        for key, data in self.text_positions.items():
            if 'fade_out_start' in data and current_time - data['fade_out_start'] > 1.0:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in self.text_positions[key]:
                cell = self.text_positions[key]['grid_cell']
                self.occupied_cells.discard(cell)
                self.cell_last_used[cell] = current_time
            del self.text_positions[key]

        # נקה טקסטים התנהגותיים
        keys_to_remove = []
        for key, data in self.behavioral_text_positions.items():
            if 'fade_out_start' in data and current_time - data['fade_out_start'] > 1.0:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in self.behavioral_text_positions[key]:
                cell = self.behavioral_text_positions[key]['grid_cell']
                self.behavioral_occupied_cells.discard(cell)
                self.behavioral_cell_last_used[cell] = current_time
            del self.behavioral_text_positions[key]

    def _setup_screen_dimensions(self):
        monitor = get_monitors()[0]
        self.screen_width = monitor.width
        self.screen_height = monitor.height

    def setup_window(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def toggle_json_overlay(self):
        self.show_json_overlay = not self.show_json_overlay
        print(f"JSON overlay toggled: {'ON' if self.show_json_overlay else 'OFF'}")

    def show_frame(self, frame, json_data_path, behavioral_data_path, active_persons=None):
        """הצגת פריים עם נתוני JSON ונתונים התנהגותיים"""

        self.frame_count += 1
        # שמירת רשימת האנשים הפעילים
        self.current_active_persons = active_persons if active_persons else []

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

            # עיבוד מעבר הדרגתי
            current_time = time.time()
            self._process_gradual_transition(current_time)

            if self.display_mode == "visual" and not self.in_transition:
                data_lines = self._get_visual_data_lines(json_data_path)
                self._display_visual_texts(black_screen, data_lines)
            elif self.display_mode == "behavioral" and not self.in_transition:
                data_lines = self._get_behavioral_data_lines(behavioral_data_path)
                self._display_behavioral_texts(black_screen, data_lines)
            elif self.in_transition:
                # במהלך מעבר - הצג את שני הסוגים עם fade out/in
                self._display_transition_texts(black_screen, json_data_path, behavioral_data_path)

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

        cv2.imshow(self.window_name, full_screen_frame)

    def _get_visual_data_lines(self, json_data_path):
        """קבלת נתונים חזותיים מהמאגר הראשון"""
        data_lines = []
        if os.path.exists(json_data_path):
            try:
                with open(json_data_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                    if "sessions" in json_data and isinstance(json_data["sessions"], list):
                        if len(json_data["sessions"]) == 0:
                            data_lines.append("No sessions available")
                        else:
                            latest_session = json_data["sessions"][-1]
                            session_people = latest_session.get("session", [])

                            if len(session_people) > 0:
                                for person_data in session_people:
                                    categories = person_data.get("categories", {})

                                    if categories:
                                        for category_name, items in categories.items():
                                            if items:
                                                for item in items:
                                                    data_lines.append(item)
                    else:
                        data_lines.append("No session data available")
            except (IOError, json.JSONDecodeError) as e:
                data_lines.append(f"Error reading JSON: {e}")
        else:
            data_lines.append("JSON file not found")

        return data_lines

    def _get_behavioral_data_lines(self, behavioral_data_path):
        """קבלת נתונים התנהגותיים מהמאגר השני"""
        data_lines = []
        if os.path.exists(behavioral_data_path):
            try:
                with open(behavioral_data_path, 'r', encoding='utf-8') as f:
                    behavioral_data = json.load(f)

                    if "sessions" in behavioral_data and isinstance(behavioral_data["sessions"], list):
                        if len(behavioral_data["sessions"]) == 0:
                            data_lines.append("No behavioral sessions available")
                        else:
                            # אסוף את כל המשפטים מכל הסשנים
                            all_insights = []
                            for session in behavioral_data["sessions"]:
                                insights = session.get("behavioral_analysis", [])
                                all_insights.extend(insights)

                            # הסר כפילויות
                            unique_insights = list(set(all_insights))
                            data_lines.extend(unique_insights)
                    else:
                        data_lines.append("No behavioral data available")
            except (IOError, json.JSONDecodeError) as e:
                data_lines.append(f"Error reading behavioral JSON: {e}")
        else:
            data_lines.append("Behavioral JSON file not found")

        return data_lines

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
        self._cleanup_expired_texts(current_time, self.text_positions, self.occupied_cells, self.cell_last_used,
                                    is_behavioral=False)

        # הוסף טקסטים חדשים או עדכן קיימים
        for line in data_lines:
            if line.strip():
                line_key = line.strip()
                if line_key not in self.text_positions:
                    self._add_new_text(line_key, current_time, self.text_positions, self.occupied_cells,
                                       self.cell_last_used, is_behavioral=False)

        # צייר את כל הטקסטים עם צבעים של המאגר הראשון
        self._draw_texts(draw, font_base, current_time, self.text_positions, is_behavioral=False)

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
        self._cleanup_expired_texts(current_time, self.behavioral_text_positions,
                                    self.behavioral_occupied_cells, self.behavioral_cell_last_used, is_behavioral=True)

        # הוסף טקסטים חדשים או עדכן קיימים
        for line in data_lines:
            if line.strip():
                line_key = line.strip()
                if line_key not in self.behavioral_text_positions:
                    self._add_new_text(line_key, current_time, self.behavioral_text_positions,
                                       self.behavioral_occupied_cells, self.behavioral_cell_last_used,
                                       is_behavioral=True)

        # צייר את כל הטקסטים עם צבע לבן
        self._draw_texts(draw, font_base, current_time, self.behavioral_text_positions, is_behavioral=True)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def _display_transition_texts(self, black_screen, json_data_path, behavioral_data_path):
        """הצגת טקסטים במהלך מעבר עם fade out/in"""
        pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        current_time = time.time()

        try:
            font_base = ImageFont.load_default()
        except:
            font_base = None

        # עדכן cache של נתונים אם צריך
        if not hasattr(self, '_cached_behavioral_data'):
            data_lines = self._get_behavioral_data_lines(behavioral_data_path)
            self._cached_behavioral_data = [line.strip() for line in data_lines if line.strip()]

        if not hasattr(self, '_cached_visual_data'):
            data_lines = self._get_visual_data_lines(json_data_path)
            self._cached_visual_data = [line.strip() for line in data_lines if line.strip()]

        # הצג טקסטים קיימים (כולל אלה במצב fade out)
        if self.display_mode == "visual":
            self._draw_transition_texts(draw, font_base, current_time, self.text_positions, is_behavioral=False)
        else:
            self._draw_transition_texts(draw, font_base, current_time, self.behavioral_text_positions,
                                        is_behavioral=True)

        # הצג טקסטים חדשים שנוספו
        if hasattr(self, 'target_mode') and self.target_mode == "behavioral":
            self._draw_transition_texts(draw, font_base, current_time, self.behavioral_text_positions,
                                        is_behavioral=True)
        else:
            self._draw_transition_texts(draw, font_base, current_time, self.text_positions, is_behavioral=False)

        # נקה טקסטים שסיימו fade out
        self._cleanup_transition_texts(current_time)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def _cleanup_transition_texts(self, current_time):
        """מנקה טקסטים שסיימו fade out במהלך מעבר"""
        # נקה טקסטים חזותיים
        keys_to_remove = []
        for key, data in self.text_positions.items():
            if 'fade_out_start' in data:
                fade_elapsed = current_time - data['fade_out_start']
                if fade_elapsed > data.get('fade_out_duration', 1.0):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in self.text_positions[key]:
                cell = self.text_positions[key]['grid_cell']
                self.occupied_cells.discard(cell)
                self.cell_last_used[cell] = current_time
            del self.text_positions[key]

        # נקה טקסטים התנהגותיים
        keys_to_remove = []
        for key, data in self.behavioral_text_positions.items():
            if 'fade_out_start' in data:
                fade_elapsed = current_time - data['fade_out_start']
                if fade_elapsed > data.get('fade_out_duration', 1.0):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in self.behavioral_text_positions[key]:
                cell = self.behavioral_text_positions[key]['grid_cell']
                self.behavioral_occupied_cells.discard(cell)
                self.behavioral_cell_last_used[cell] = current_time
            del self.behavioral_text_positions[key]

    def _cleanup_expired_texts(self, current_time, text_positions, occupied_cells, cell_last_used, is_behavioral=False):
        """ניקוי טקסטים שפג זמנם"""
        expired_keys = []
        for key, data in text_positions.items():
            # השתמש בזמן החיים הספציפי לכל טקסט
            lifetime = data.get('lifetime', self.TOTAL_LIFETIME if not is_behavioral else 8.0)
            if current_time - data['start_time'] > lifetime:
                expired_keys.append(key)

        for key in expired_keys:
            if key in text_positions and 'grid_cell' in text_positions[key]:
                cell = text_positions[key]['grid_cell']
                occupied_cells.discard(cell)
                cell_last_used[cell] = current_time
            del text_positions[key]

    def _add_new_text(self, line_key, current_time, text_positions, occupied_cells, cell_last_used,
                      is_behavioral=False):
        """הוספת טקסט חדש"""
        cell_width = self.screen_width // self.grid_cols
        cell_height = self.screen_height // self.grid_rows

        # מצא תא פנוי
        available_cells = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                cell = (row, col)
                if cell not in occupied_cells:
                    if cell not in cell_last_used or \
                            (current_time - cell_last_used[cell]) >= self.CELL_COOLDOWN:
                        available_cells.append(cell)

        if available_cells:
            chosen_cell = random.choice(available_cells)
            occupied_cells.add(chosen_cell)

            row, col = chosen_cell
            cell_x_start = col * cell_width
            cell_y_start = row * cell_height

            max_font_size = min(cell_width // 15, cell_height // 8, 20)
            min_font_size = 8

            text_length = len(line_key)
            if text_length > 50:
                font_size = min_font_size
            elif text_length > 30:
                font_size = min(max_font_size // 2, 12)
            else:
                font_size = random.randint(self.MIN_FONT_SIZE,
                                           self.MIN_FONT_SIZE + self.FONT_RANDOM_RANGE)
            x = cell_x_start + 5
            y = cell_y_start + 15

            # זמן חיים רנדומלי למאגר השני
            if is_behavioral:
                lifetime = random.uniform(self.BEHAVIORAL_MIN_LIFETIME, self.BEHAVIORAL_MAX_LIFETIME)
            else:
                lifetime = self.TOTAL_LIFETIME

            text_positions[line_key] = {
                'x': x,
                'y': y,
                'font_size': font_size,
                'start_time': current_time,
                'grid_cell': chosen_cell,
                'cell_width': cell_width - 10,
                'cell_height': cell_height - 10,
                'lifetime': lifetime
            }

    def _draw_texts(self, draw, font_base, current_time, text_positions, is_behavioral):
        """ציור טקסטים עם אפקטי זמן"""
        for line_text, data in text_positions.items():
            elapsed = current_time - data['start_time']

            # השתמש בזמן החיים הספציפי לכל טקסט
            lifetime = data.get('lifetime', self.TOTAL_LIFETIME if not is_behavioral else 8.0)

            # חישוב שקיפות לפי זמן
            if elapsed <= self.FADE_IN_TIME:
                alpha = elapsed / self.FADE_IN_TIME
            elif elapsed <= (lifetime - self.FADE_OUT_TIME):
                alpha = 1.0
            elif elapsed <= lifetime:
                alpha = 1.0 - ((elapsed - (lifetime - self.FADE_OUT_TIME)) / self.FADE_OUT_TIME)
            else:
                continue

            # הגדרת פונט
            try:
                font = ImageFont.truetype("arial.ttf", max(data['font_size'], 6))
            except:
                font = font_base

            # צבע לפי סוג המאגר
            if is_behavioral:
                # מאגר התנהגותי - לבן
                base_r, base_g, base_b = self.BEHAVIORAL_COLOR
                color = (int(base_r * alpha), int(base_g * alpha), int(base_b * alpha))
            else:
                # מאגר חזותי - צבע מקורי
                if 'base_color' not in data:
                    data['base_color'] = (
                        random.randint(self.COLOR_MIN_R, self.COLOR_MAX_R),
                        random.randint(self.COLOR_MIN_G, self.COLOR_MAX_G),
                        random.randint(self.COLOR_MIN_B, self.COLOR_MAX_B)
                    )
                base_r, base_g, base_b = data['base_color']
                color = (int(base_r * alpha), int(base_g * alpha), int(base_b * alpha))

            # הצגת הטקסט
            try:
                display_line = get_display(line_text)
            except:
                display_line = line_text

            self._draw_single_text(draw, font, display_line, data, color)

    def _draw_transition_texts(self, draw, font_base, current_time, text_positions, is_behavioral):
        """ציור טקסטים במהלך מעבר עם fade out/in"""
        for line_text, data in text_positions.items():
            elapsed = current_time - data['start_time']
            alpha = 1.0  # שקיפות ברירת מחדל

            # בדוק אם הטקסט במצב fade out
            if 'fade_out_start' in data:
                fade_out_elapsed = current_time - data['fade_out_start']
                fade_duration = data.get('fade_out_duration', 1.0)
                if fade_out_elapsed <= fade_duration:
                    alpha = 1.0 - (fade_out_elapsed / fade_duration)
                else:
                    continue  # הטקסט נעלם לגמרי
            else:
                # השתמש בזמן החיים הספציפי לכל טקסט
                lifetime = data.get('lifetime', self.TOTAL_LIFETIME if not is_behavioral else 8.0)

                # חישוב שקיפות רגיל לטקסטים חדשים
                if elapsed <= self.FADE_IN_TIME:
                    alpha = elapsed / self.FADE_IN_TIME
                elif elapsed <= (lifetime - self.FADE_OUT_TIME):
                    alpha = 1.0
                elif elapsed <= lifetime:
                    alpha = 1.0 - ((elapsed - (lifetime - self.FADE_OUT_TIME)) / self.FADE_OUT_TIME)
                else:
                    continue

            # וודא שהשקיפות תקינה
            alpha = max(0.0, min(1.0, alpha))

            if alpha <= 0.01:  # כמעט שקוף
                continue

            # הגדרת פונט
            try:
                font = ImageFont.truetype("arial.ttf", max(data['font_size'], 6))
            except:
                font = font_base

            # צבע לפי סוג המאגר
            if is_behavioral:
                base_r, base_g, base_b = self.BEHAVIORAL_COLOR
                color = (int(base_r * alpha), int(base_g * alpha), int(base_b * alpha))
            else:
                if 'base_color' not in data:
                    data['base_color'] = (
                        random.randint(self.COLOR_MIN_R, self.COLOR_MAX_R),
                        random.randint(self.COLOR_MIN_G, self.COLOR_MAX_G),
                        random.randint(self.COLOR_MIN_B, self.COLOR_MAX_B)
                    )
                base_r, base_g, base_b = data['base_color']
                color = (int(base_r * alpha), int(base_g * alpha), int(base_b * alpha))

            # הצגת הטקסט
            try:
                display_line = get_display(line_text)
            except:
                display_line = line_text

            self._draw_single_text(draw, font, display_line, data, color)

    def _draw_single_text(self, draw, font, display_line, data, color):
        """ציור טקסט בודד על המסך"""
        try:
            sample_text = "A" * 10
            bbox = draw.textbbox((0, 0), sample_text, font=font)
            sample_width = bbox[2] - bbox[0]
            chars_per_line = int((data['cell_width'] * 10) / sample_width) if sample_width > 0 else 20
        except:
            chars_per_line = data['cell_width'] // max(data['font_size'] // 2, 4)

        chars_per_line = max(chars_per_line, 5)

        words = display_line.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= chars_per_line:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        lines.reverse()

        line_height = data['font_size'] + 2
        for i, text_line in enumerate(lines):
            y_position = data['y'] + i * line_height
            if y_position + line_height <= data['y'] + data['cell_height']:
                try:
                    bbox = draw.textbbox((0, 0), text_line, font=font)
                    text_width = bbox[2] - bbox[0]
                except:
                    text_width = len(text_line) * (data['font_size'] // 2)

                centered_x = data['x'] + (data['cell_width'] - text_width) // 2
                draw.text((centered_x, y_position), text_line, fill=color, font=font)
            else:
                break