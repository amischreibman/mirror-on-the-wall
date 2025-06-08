import time

import cv2  # ייבוא ספריית OpenCV לתצוגה וציור
import sys  # הגדרת encoding לעברית
import random  # ייבוא מודול רנדום
from screeninfo import get_monitors  # ייבוא פונקציה למידע על מסכים
import numpy as np  # ייבוא ספריית NumPy ליצירת תמונות (רקעים)
import json  # ייבוא מודול לעבודה עם פורמט JSON
import os  # ייבוא מודול לגישה למערכת הקבצים
from datetime import datetime  # לדיבאג
from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display


class DisplayManager:  # הגדרת מחלקה לניהול תצוגה

    # === הגדרות שליטה לטקסט ===
    FADE_IN_TIME = 3.0  # זמן הופעה בשניות
    STABLE_TIME = 4.0  # זמן קבוע בשניות
    FADE_OUT_TIME = 1.0  # זמן היעלמות בשניות
    TOTAL_LIFETIME = 8.0  # סך זמן חיים בשניות
    CELL_COOLDOWN = 3.0  # זמן המתנה לפני שימוש חוזר בתא (שניות)

    # הגדרות גודל פונט
    MIN_FONT_SIZE = 14  # גודל פונט מינימלי
    MAX_FONT_SIZE = 25  # גודל פונט מקסימלי
    FONT_RANDOM_RANGE = 30  # טווח רנדומליות (יתווסף למינימום)

    # הגדרות צבע (RGB)
    COLOR_MIN_R = 0  # אדום מינימלי (0-255)
    COLOR_MAX_R = 50  # אדום מקסימלי (0-255)
    COLOR_MIN_G = 150  # ירוק מינימלי (0-255)
    COLOR_MAX_G = 255  # ירוק מקסימלי (0-255)
    COLOR_MIN_B = 0  # כחול מינימלי (0-255)
    COLOR_MAX_B = 100  # כחול מקסימלי (0-255)

    # הגדרות גריד
    GRID_COLS = 8  # מספר עמודות
    GRID_ROWS = 6  # מספר שורות

    def __init__(self, window_name='Mirror on the Wall'):  # פונקציית אתחול למחלקה
        self.window_name = window_name  # שמירת שם החלון
        self.screen_width = 0  # אתחול רוחב מסך
        self.screen_height = 0  # אתחול גובה מסך
        self._setup_screen_dimensions()  # קריאה לפונקציה לקבלת מימדי מסך
        self.show_json_overlay = False  # דגל לשליטה על הצגת שכבת הנתונים
        self.last_json_data = None  # שמירת נתונים אחרונים לדיבאג
        self.frame_count = 0  # מונה פריימים
        self.text_positions = {}  # מילון לשמירת מיקומי טקסטים עם זמנים
        self.show_grid = False  # דגל להצגת הגריד
        self.grid_cols = self.GRID_COLS
        self.grid_rows = self.GRID_ROWS
        self.occupied_cells = set()  # תאים תפוסים
        self.cell_last_used = {}  # מעקב אחרי זמן שימוש אחרון בכל תא



    def toggle_grid(self):
        self.show_grid = not self.show_grid
        print(f"Grid display: {'ON' if self.show_grid else 'OFF'}")

    def _setup_screen_dimensions(self):  # פונקציה פרטית לקבלת מימדי מסך
        monitor = get_monitors()[0]  # קבלת פרטי המסך הראשי
        self.screen_width = monitor.width  # רוחב המסך
        self.screen_height = monitor.height  # גובה המסך

    def setup_window(self):  # פונקציה להגדרת חלון התצוגה
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)  # יצירת חלון רגיל
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)  # הגדרת מסך מלא

    def toggle_json_overlay(self):  # פונקציה להחלפת מצב הצגת הנתונים
        self.show_json_overlay = not self.show_json_overlay  # היפוך הדגל
        print(f"JSON overlay toggled: {'ON' if self.show_json_overlay else 'OFF'}")

    def show_frame(self, frame, json_data_path):  # פונקציה להצגת פריים עם נתוני JSON

        self.frame_count += 1
        frame_height, frame_width, _ = frame.shape  # קבלת מימדי פריים
        frame = cv2.flip(frame, 1)  # הפיכת הפריים לראי (שיקוף אופקי)

        aspect_ratio_frame = frame_width / frame_height  # יחס רוחב/גובה של הפריים
        aspect_ratio_screen = self.screen_width / self.screen_height  # יחס רוחב/גובה של המסך

        if aspect_ratio_frame > aspect_ratio_screen:  # אם הפריים רחב יותר מהמסך יחסית
            new_width = self.screen_width  # רוחב חדש הוא רוחב המסך
            new_height = int(new_width / aspect_ratio_frame)  # גובה חדש מחושב לפי יחס
        else:  # אם הפריים גבוה יותר מהמסך יחסית
            new_height = self.screen_height  # גובה חדש הוא גובה המסך
            new_width = int(new_height * aspect_ratio_frame)  # רוחב חדש מחושב לפי יחס

        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)  # שינוי גודל הפריים

        full_screen_frame = np.zeros((self.screen_height, self.screen_width, 3),
                                     dtype=np.uint8)  # יצירת רקע שחור עם NumPy

        x_offset = (self.screen_width - new_width) // 2  # היסט X לריכוז
        y_offset = (self.screen_height - new_height) // 2  # היסט Y לריכוז

        full_screen_frame[y_offset:y_offset + new_height,
        x_offset:x_offset + new_width] = resized_frame  # הצבת פריים במרכז

        # --- הוספת שכבת נתוני JSON אם הדגל פעיל ---
        if self.show_json_overlay:  # בדיקה אם להציג שכבת נתונים
            # יצירת מסך שחור מלא
            black_screen = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)

            # קריאת נתוני ה-JSON העדכניים בכל פריים!
            data_lines = []  # רשימה לאחסון שורות הטקסט להצגה
            if os.path.exists(json_data_path):  # בדיקה אם קובץ ה-JSON קיים
                try:
                    with open(json_data_path, 'r', encoding='utf-8') as f:  # פתיחת קובץ לקריאה
                        json_data = json.load(f)  # טעינת הנתונים

                        if "sessions" in json_data and isinstance(json_data["sessions"], list):
                            if len(json_data["sessions"]) == 0:
                                data_lines.append("No sessions available")
                            else:
                                # הצג את הסשן האחרון (הפעיל) ללא כותרות
                                latest_session = json_data["sessions"][-1]
                                session_people = latest_session.get("session", [])

                                if len(session_people) > 0:
                                    for person_data in session_people:
                                        categories = person_data.get("categories", {})

                                        # הצגת כל קטגוריה ללא כותרות
                                        if categories:
                                            for category_name, items in categories.items():
                                                if items:  # רק אם יש פריטים בקטגוריה
                                                    # הוספת כל הפריטים בקטגוריה - כל פריט בנפרד
                                                    for item in items:
                                                        data_lines.append(item)
                        else:
                            data_lines.append("No session data available")
                except (IOError, json.JSONDecodeError) as e:  # טיפול בשגיאות
                    data_lines.append(f"Error reading JSON: {e}")  # הודעת שגיאה
            else:
                data_lines.append("JSON file not found")

            # הצגת הטקסט עם מיקומים קבועים וזמנים
            pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)

            current_time = time.time()

            try:
                font_base = ImageFont.load_default()
            except:
                font_base = None

            # נקה טקסטים שפג זמנם
            expired_keys = []
            for key, data in self.text_positions.items():
                if current_time - data['start_time'] > 8.0:  # 8 שניות
                    expired_keys.append(key)

            for key in expired_keys:
                # שחרר את התא ורשום זמן שחרור
                if key in self.text_positions and 'grid_cell' in self.text_positions[key]:
                    cell = self.text_positions[key]['grid_cell']
                    self.occupied_cells.discard(cell)
                    self.cell_last_used[cell] = current_time  # רשום זמן שחרור
                del self.text_positions[key]

            # הוסף טקסטים חדשים או עדכן קיימים
            for line in data_lines:
                if line.strip():
                    line_key = line.strip()

                    if line_key not in self.text_positions:
                        # טקסט חדש - בחר תא ריק בגריד
                        cell_width = self.screen_width // self.grid_cols
                        cell_height = self.screen_height // self.grid_rows

                        # מצא תא פנוי
                        # מצא תא פנוי (לא תפוס ולא בקירור)
                        available_cells = []
                        for row in range(self.grid_rows):
                            for col in range(self.grid_cols):
                                cell = (row, col)
                                if cell not in self.occupied_cells:
                                    # בדוק אם התא לא בתקופת קירור
                                    if cell not in self.cell_last_used or \
                                            (current_time - self.cell_last_used[cell]) >= self.CELL_COOLDOWN:
                                        available_cells.append(cell)

                        if available_cells:
                            chosen_cell = random.choice(available_cells)
                            self.occupied_cells.add(chosen_cell)

                            # חישוב מיקום ופונט מותאם לתא
                            row, col = chosen_cell
                            cell_x_start = col * cell_width
                            cell_y_start = row * cell_height

                            # התאמת גודל פונט לתא ולטקסט
                            max_font_size = min(cell_width // 15, cell_height // 8, 20)
                            min_font_size = 8

                            # בדיקת אורך הטקסט והתאמת הפונט
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

                            self.text_positions[line_key] = {
                                'x': x,
                                'y': y,
                                'font_size': font_size,
                                'start_time': current_time,
                                'grid_cell': chosen_cell,
                                'cell_width': cell_width - 10,
                                'cell_height': cell_height - 10
                            }

            # צייר את כל הטקסטים עם אפקטי זמן וסקייל - עדכון בתדירות גבוהה
            for line_text, data in self.text_positions.items():
                elapsed = current_time - data['start_time']

                # חישוב שקיפות לפי זמן
                if elapsed <= self.FADE_IN_TIME:
                    alpha = elapsed / self.FADE_IN_TIME
                elif elapsed <= (self.FADE_IN_TIME + self.STABLE_TIME):
                    alpha = 1.0
                elif elapsed <= self.TOTAL_LIFETIME:
                    alpha = 1.0 - ((elapsed - (self.FADE_IN_TIME + self.STABLE_TIME)) / self.FADE_OUT_TIME)
                else:
                    continue  # לא להציג

                scaled_font_size = data['font_size']

                # הגדרת פונט עם הגודל החדש
                try:
                    font = ImageFont.truetype("arial.ttf", max(data['font_size'], 6))
                except:
                    font = font_base

                # צבע עם שקיפות
                # השתמש בצבע קבוע שנשמר עם הטקסט
                if 'base_color' not in data:
                    # צבע חדש רק פעם אחת
                    data['base_color'] = (
                        random.randint(self.COLOR_MIN_R, self.COLOR_MAX_R),
                        random.randint(self.COLOR_MIN_G, self.COLOR_MAX_G),
                        random.randint(self.COLOR_MIN_B, self.COLOR_MAX_B)
                    )

                base_r, base_g, base_b = data['base_color']
                color = (int(base_r * alpha), int(base_g * alpha), int(base_b * alpha))

                # חלוקת הטקסט לשורות שמתאימות לתא
                try:
                    display_line = get_display(line_text)
                except:
                    display_line = line_text

                # חישוב כמה תווים נכנסים בשורה
                try:
                    # נסיון לחשב רוחב טקסט לדוגמה
                    sample_text = "A" * 10
                    bbox = draw.textbbox((0, 0), sample_text, font=font)
                    sample_width = bbox[2] - bbox[0]
                    chars_per_line = int((data['cell_width'] * 10) / sample_width) if sample_width > 0 else 20
                except:
                    chars_per_line = data['cell_width'] // max(data['font_size'] // 2, 4)

                chars_per_line = max(chars_per_line, 5)  # מינימום 5 תווים

                # חלוקה לשורות עם סדר הפוך
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

                # הפוך את סדר השורות - השורה האחרונה תהיה למעלה
                lines.reverse()

                # הצגת השורות
                # הצגת השורות ממורכזות
                line_height = data['font_size'] + 2
                for i, text_line in enumerate(lines):
                    y_position = data['y'] + i * line_height
                    if y_position + line_height <= data['y'] + data['cell_height']:  # בדיקה שלא חורג מהתא
                        # חישוב רוחב הטקסט לריכוז
                        try:
                            bbox = draw.textbbox((0, 0), text_line, font=font)
                            text_width = bbox[2] - bbox[0]
                        except:
                            text_width = len(text_line) * (data['font_size'] // 2)

                        # חישוב מיקום ממורכז
                        centered_x = data['x'] + (data['cell_width'] - text_width) // 2

                        draw.text((centered_x, y_position), text_line, fill=color, font=font)
                    else:
                        break  # עצור אם אין מקום

            # המרה חזרה ל-OpenCV
            full_screen_frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

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

        # --- סוף הוספת שכבת נתוני JSON ---

        cv2.imshow(self.window_name, full_screen_frame)  # הצגת הפריים המלא בחלון


