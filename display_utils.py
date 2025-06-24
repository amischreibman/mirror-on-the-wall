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
        self.visual_duration = 30.0  # כמות שניות למצב חזותי (ירוק)
        self.behavioral_duration = 20.0  #  כמות שניות למצב התנהגותי (לבן)
        self.prompt_duration = 20.0  # כמות שניות למצב פרומפט
        self.prompt_text = ""  # הטקסט של הפרומפט
        self.prompt_display_index = 0  # אינדקס לאפקט הקלדה
        self.prompt_last_char_time = 0  # זמן אחרון שהוספנו תו
        self.prompt_generated = False  # האם הפרומפט כבר נוצר
        self.visual_data_path = None  # נתיב לנתונים חזותיים
        self.behavioral_data_path = None  # נתיב לנתונים התנהגותיים
        self.all_behavioral_added = False  # האם כל המשפטים הוספו
        self.prompt_transition_time = None  # זמן המעבר לפרומפט

        # משתנים למעקב אחרי מצב הפרומפט כשיש אנשים
        self.prompt_active = False  # האם הפרומפט פעיל כרגע
        self.prompt_fade_out_start = None  # זמן התחלת fade out
        self.prompt_fade_out_duration = 3.0  # משך fade out בשניות
        self.prompt_fade_in_start = None  # זמן התחלת fade in
        self.prompt_fade_in_duration = 0.5  # משך fade in בשניות
        self.prompt_opacity = 0.0  # שקיפות נוכחית של הפרומפט (0-1)
        self.last_people_count = 0  # מספר האנשים האחרון שזוהה
        self.people_positions = []  # מיקומי האנשים (ימין, שמאל, מרכז וכו')

        # זמנים מוחלטים מתחילת היישום
        self.app_start_time = time.time()  # זמן התחלת היישום
        self.visual_start_time = 0  # שניה 0
        self.visual_fadeout_start_time = 25  # שניה 25 - תחילת fade out
        self.visual_fadeout_started = False
        self.behavioral_start_time = 30  # שניה 30
        self.prompt_start_time = 60  # שניה 60 (דקה)
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

    def calculate_people_positions(self, active_persons):
        """מחשב את המיקומים היחסיים של האנשים במסך"""
        if not active_persons:
            return []

        positions = []
        num_people = len(active_persons)

        if num_people == 1:
            positions.append("במרכז")
        elif num_people == 2:
            positions = ["בצד ימין", "בצד שמאל"]
        elif num_people == 3:
            positions = ["בצד ימין", "במרכז", "בצד שמאל"]
        elif num_people == 4:
            positions = ["בצד ימין", "בין ימין למרכז", "בין מרכז לשמאל", "בצד שמאל"]
        else:
            # יותר מ-4 אנשים
            for i in range(num_people):
                positions.append(f"אדם {i + 1}")

        return positions

    def update_prompt_opacity(self, current_time, has_people):
        """מעדכן את שקיפות הפרומפט בהתאם למצב האנשים"""
        if has_people:
            # יש אנשים - הפרומפט צריך להיות מוצג
            if not self.prompt_active:
                # התחל fade in
                if self.prompt_fade_in_start is None:
                    self.prompt_fade_in_start = current_time
                    self.prompt_fade_out_start = None  # בטל fade out אם היה

                # חשב שקיפות fade in
                fade_in_elapsed = current_time - self.prompt_fade_in_start
                if fade_in_elapsed >= self.prompt_fade_in_duration:
                    self.prompt_opacity = 1.0
                    self.prompt_active = True
                    self.prompt_fade_in_start = None
                else:
                    self.prompt_opacity = fade_in_elapsed / self.prompt_fade_in_duration
            else:
                # הפרומפט כבר פעיל
                self.prompt_opacity = 1.0
        else:
            # אין אנשים - הפרומפט צריך להיעלם
            if self.prompt_active:
                # התחל fade out
                if self.prompt_fade_out_start is None:
                    self.prompt_fade_out_start = current_time
                    self.prompt_fade_in_start = None  # בטל fade in אם היה

                # חשב שקיפות fade out
                fade_out_elapsed = current_time - self.prompt_fade_out_start
                if fade_out_elapsed >= self.prompt_fade_out_duration:
                    self.prompt_opacity = 0.0
                    self.prompt_active = False
                    self.prompt_fade_out_start = None
                    # איפוס הפרומפט
                    self.prompt_generated = False
                    self.prompt_display_index = 0
                    self.prompt_text = ""
                else:
                    self.prompt_opacity = 1.0 - (fade_out_elapsed / self.prompt_fade_out_duration)

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

        # למצב prompt - עבור אחרי 15 שניות
        elif self.display_mode == "prompt":
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

        # 🔍 דיבאג - מעקב אחרי שינויי מצב
        if self.frame_count % 30 == 0:  # כל שנייה בערך
            time_since_start = time.time() - self.app_start_time
            print(f"🎭 מצב נוכחי: '{self.display_mode}' בשניה {int(time_since_start)}")

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
                # חישוב זמן מתחילת היישום
                time_since_start = current_time - self.app_start_time

                # בדיקה אם יש אנשים מול המצלמה
                has_people = len(self.current_active_persons) > 0

                # עדכון שקיפות הפרומפט
                self.update_prompt_opacity(current_time, has_people)

                # עדכון מיקומי אנשים אם השתנה
                if len(self.current_active_persons) != self.last_people_count:
                    self.people_positions = self.calculate_people_positions(self.current_active_persons)
                    self.last_people_count = len(self.current_active_persons)
                    # אם יש אנשים והפרומפט פעיל, צריך לעדכן אותו
                    if has_people and self.prompt_active:
                        self.prompt_generated = False  # יגרום ליצירת פרומפט חדש

                # הפעלת behavioral mode אחרי 30 שניות
                if time_since_start >= self.behavioral_start_time and "behavioral_started" not in self.__dict__:
                    print(f"🔄 מעבר אוטומטי: הפעלת מצב התנהגותי בשניה {int(time_since_start)}")
                    self.behavioral_started = True
                    # לא משנים את display_mode - רק מוסיפים טקסטים לבנים

                # התחל fade out של טקסטים ירוקים אחרי 25 שניות
                if time_since_start >= self.visual_fadeout_start_time and not self.visual_fadeout_started:
                    print(f"🌅 מתחיל fade out של טקסטים ירוקים בשניה {int(time_since_start)}")
                    self._start_visual_fadeout(current_time)
                    self.visual_fadeout_started = True

                # 🔍 דיבאג - בדיקת תנאי פרומפט כל 5 שניות
                if self.frame_count % 150 == 0:  # כל 5 שניות בערך
                    print(f"🔍 בדיקת פרומפט: עבר {int(time_since_start)} שניות מתחילת ההרצה")
                    print(
                        f"🔍 האם עברה דקה? {time_since_start >= self.prompt_start_time} (צריך לעבור {self.prompt_start_time} שניות)")
                    print(f"🔍 מצב נוכחי: '{self.display_mode}'")
                    print(f"🔍 האם המצב לא פרומפט? {self.display_mode != 'prompt'}")
                    print(
                        f"🔍 שני התנאים מתקיימים? {time_since_start >= self.prompt_start_time and self.display_mode != 'prompt'}")
                    print("=" * 50)

                # הפעלת prompt mode אחרי 60 שניות (דקה)
                if time_since_start >= self.prompt_start_time and self.display_mode != "prompt":
                    print(f"🎯 מעבר אוטומטי: עובר למצב פרומפט בשניה {int(time_since_start)}")
                    self.display_mode = "prompt"
                    self.auto_mode_timer = current_time
                    self.prompt_generated = False
                    self.prompt_display_index = 0

                # למצב prompt - הצג רק אם יש אנשים
                if self.display_mode == "prompt":
                    if not has_people:
                        # אין אנשים - בדוק אם הפרומפט כבר נעלם
                        if self.prompt_opacity <= 0.0:
                            # הפרומפט נעלם לגמרי - נשאר במצב prompt אבל לא מציג
                            pass
                        # אחרת - הפרומפט עדיין בתהליך fade out
                    else:
                        # יש אנשים - הפרומפט נשאר מוצג
                        # וודא שהפרומפט פעיל
                        if not self.prompt_active:
                            self.prompt_active = True
                            self.prompt_opacity = 1.0

            # עיבוד מעבר הדרגתי
            self.transition_manager.process_gradual_transition(self, current_time)

            if self.display_mode == "visual" and not self.in_transition:
                # הצג טקסטים ירוקים רק עד שניה 30
                time_since_start = current_time - self.app_start_time
                if time_since_start < 30:  # רק ב-30 השניות הראשונות
                    data_lines = self.data_loader.get_visual_data_lines(json_data_path)
                    self._display_visual_texts(black_screen, data_lines)
                else:
                    # אחרי 30 שניות - רק צייר את הקיימים, אל תוסיף חדשים
                    pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_image)
                    try:
                        font_base = ImageFont.load_default()
                    except:
                        font_base = None
                    self.text_renderer.draw_texts(self, draw, font_base, current_time, self.text_positions,
                                                  is_behavioral=False)
                    black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

                # הוסף גם טקסטים לבנים אם הדגל מופעל
                if hasattr(self, 'behavioral_started') and self.behavioral_started:
                    # צייר טקסטים לבנים על אותו מסך
                    pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_image)
                    try:
                        font_base = ImageFont.load_default()
                    except:
                        font_base = None

                    # צייר את הטקסטים הלבנים
                    current_time = time.time()
                    self.text_renderer.draw_texts(self, draw, font_base, current_time,
                                                  self.behavioral_text_positions, is_behavioral=True)

                    # החזר ל-OpenCV
                    black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            elif self.display_mode == "behavioral" and not self.in_transition:
                data_lines = self.data_loader.get_behavioral_data_lines(self, behavioral_data_path)
                self._display_behavioral_texts(black_screen, data_lines)

            elif self.display_mode == "prompt":
                print(f"🎬 מציג פרומפט: has_people={has_people}, opacity={self.prompt_opacity:.2f}")

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

            # הוסף מידע על המצב הנוכחי והזמן מתחילת היישום
            time_since_start = current_time - self.app_start_time
            info_lines.append(f"Mode: {self.display_mode}")
            info_lines.append(f"Time since start: {int(time_since_start)}s")

            # הצג באיזה שלבים אנחנו
            if hasattr(self, 'behavioral_started') and self.behavioral_started:
                info_lines.append("Behavioral: Active")

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
        if self.show_json_overlay and hasattr(self, 'behavioral_started') and self.behavioral_started:
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

    def _start_visual_fadeout(self, current_time):
        """מתחיל fade out לכל המילים הירוקות בזו אחר זו"""
        text_keys = list(self.text_positions.keys())
        random.shuffle(text_keys)  # סדר רנדומלי

        for i, text_key in enumerate(text_keys):
            if text_key in self.text_positions and 'fade_out_start' not in self.text_positions[text_key]:
                # כל מילה מתחילה fade out עם הפרש של 0.5 שניות
                self.text_positions[text_key]['fade_out_start'] = current_time + (i * 0.5)
                self.text_positions[text_key]['fade_out_duration'] = 2.0  # 2 שניות fade out

        print(f"🌅 Starting fade out for {len(text_keys)} visual texts")

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
                    lifetime = 12.0

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