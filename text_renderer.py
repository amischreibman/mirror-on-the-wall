import random
import time
from PIL import ImageFont, ImageDraw
from bidi.algorithm import get_display


class TextRenderer:
    def __init__(self):
        # הגדרות קבועות
        self.FADE_IN_TIME = 3.0
        self.STABLE_TIME = 4.0
        self.FADE_OUT_TIME = 3.0
        self.TOTAL_LIFETIME = 8.0
        self.CELL_COOLDOWN = 3.0

        # הגדרות צבע למאגר הראשון (RGB)
        self.COLOR_MIN_R = 0
        self.COLOR_MAX_R = 50
        self.COLOR_MIN_G = 150
        self.COLOR_MAX_G = 255
        self.COLOR_MIN_B = 0
        self.COLOR_MAX_B = 100

        # הגדרות צבע למאגר השני (לבן)
        self.BEHAVIORAL_COLOR = (255, 255, 255)

        # הגדרות גודל פונט
        self.MIN_FONT_SIZE = 14
        self.MAX_FONT_SIZE = 25
        self.FONT_RANDOM_RANGE = 30

        # הגדרות זמן למאגר השני
        self.BEHAVIORAL_MIN_LIFETIME = 8.0
        self.BEHAVIORAL_MAX_LIFETIME = 8.0

    def cleanup_expired_texts(self, display_manager, current_time, text_positions, occupied_cells, cell_last_used,
                              is_behavioral=False):
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

    def add_new_text(self, display_manager, line_key, current_time, text_positions, occupied_cells, cell_last_used,
                     is_behavioral=False):
        """הוספת טקסט חדש"""
        # זמן חיים רנדומלי למאגר השני
        if is_behavioral:
            lifetime = random.uniform(self.BEHAVIORAL_MIN_LIFETIME, self.BEHAVIORAL_MAX_LIFETIME)
        else:
            lifetime = self.TOTAL_LIFETIME

        self.add_new_text_with_lifetime(display_manager, line_key, current_time, lifetime, text_positions,
                                        occupied_cells, cell_last_used, is_behavioral)

    def add_new_text_with_lifetime(self, display_manager, line_key, current_time, lifetime, text_positions,
                                   occupied_cells,
                                   cell_last_used, is_behavioral=False):
        """הוספת טקסט חדש עם זמן חיים מותאם אישית"""
        cell_width = display_manager.screen_width // display_manager.grid_cols
        cell_height = display_manager.screen_height // display_manager.grid_rows

        # מצא תא פנוי
        available_cells = []
        for row in range(display_manager.grid_rows):
            for col in range(display_manager.grid_cols):
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

    def draw_texts(self, display_manager, draw, font_base, current_time, text_positions, is_behavioral):
        """ציור טקסטים עם אפקטי זמן"""
        for line_text, data in text_positions.items():
            elapsed = current_time - data['start_time']

            # השתמש בזמן החיים הספציפי לכל טקסט
            lifetime = data.get('lifetime', self.TOTAL_LIFETIME if not is_behavioral else 10.0)

            # חישוב שקיפות לפי זמן
            if elapsed <= self.FADE_IN_TIME:
                alpha = elapsed / self.FADE_IN_TIME
            elif elapsed <= (lifetime - self.FADE_OUT_TIME):
                alpha = 1.0
            elif elapsed <= lifetime:
                alpha = 1.0 - ((elapsed - (lifetime - self.FADE_OUT_TIME)) / self.FADE_OUT_TIME)
            else:
                continue

            # הגדרת פונט - נסה קטרינה קודם
            try:
                # נסה כמה נתיבים אפשריים לפונט קטרינה
                font_paths = [
                    "Karantina-Bold.ttf",  # בתיקייה הראשית של הפרויקט
                    "Karantina-Light.ttf",
                    "Karantina-Regular.ttf",
                    "./Karantina-Bold.ttf",
                    "./Karantina-Light.ttf",
                    "./Karantina-Regular.ttf",
                    "C:/Windows/Fonts/Karantina-Regular.ttf",
                    "C:/Windows/Fonts/Karantina-Light.ttf",
                    "C:/Windows/Fonts/Karantina-Bold.ttf"
                ]

                font = None
                font_found = False
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, max(data['font_size'] + 10, 16))  # הגדלתי את הפונט
                        font_found = True
                        break
                    except Exception as e:
                        continue

                if not font_found:
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

            self.draw_single_text(display_manager, draw, font, display_line, data, color)

    def draw_transition_texts(self, display_manager, draw, font_base, current_time, text_positions, is_behavioral):
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

            try:
                font = ImageFont.truetype("Karantina-Bold.ttf", max(data['font_size'] + 10, 16))
            except:
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

            self.draw_single_text(display_manager, draw, font, display_line, data, color)

    def draw_single_text(self, display_manager, draw, font, display_line, data, color):
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