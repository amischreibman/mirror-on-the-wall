import time
import random


class TransitionManager:
    def __init__(self):
        self.transition_step_interval = 0.5  # חצי שנייה בין כל שלב

    def process_gradual_transition(self, display_manager, current_time):
        """מעבד מעבר הדרגתי בין מאגרים"""
        if not display_manager.in_transition:
            return

        # בדוק אם הגיע הזמן לשלב הבא
        if current_time - display_manager.last_transition_step_time >= self.transition_step_interval:

            # שלב ראשון: הכן רשימת טקסטים חדשים אם צריך
            if display_manager.transition_stage == 0:
                self.prepare_new_texts_for_transition(display_manager, current_time)
                display_manager.transition_stage = 1
                display_manager.last_transition_step_time = current_time
                return

            # שלב עיקרי: העלם ביטוי אחד והוסף אחד חדש
            if display_manager.texts_to_fade_out or (
                    hasattr(display_manager, 'texts_to_fade_in') and display_manager.texts_to_fade_in):

                # העלם ביטוי אחד אם יש
                if display_manager.texts_to_fade_out:
                    text_to_remove = display_manager.texts_to_fade_out.pop(0)
                    self.start_text_fade_out(display_manager, text_to_remove, current_time)

                # הוסף ביטוי חדש אחד אם יש
                if hasattr(display_manager, 'texts_to_fade_in') and display_manager.texts_to_fade_in:
                    new_text = display_manager.texts_to_fade_in.pop(0)
                    self.start_text_fade_in(display_manager, new_text, current_time)

                # עדכן זמן השלב הבא
                display_manager.last_transition_step_time = current_time

            # בדוק אם המעבר הסתיים
            if not display_manager.texts_to_fade_out and (
                    not hasattr(display_manager, 'texts_to_fade_in') or not display_manager.texts_to_fade_in):
                # המתן שנייה נוספת לפני סיום כדי לוודא שכל ה-fade out הסתיימו
                if current_time - display_manager.last_transition_step_time >= 1.5:
                    self.complete_transition(display_manager)

    def prepare_new_texts_for_transition(self, display_manager, current_time):
        """מכין רשימת טקסטים חדשים להופעה"""
        if display_manager.target_mode == "behavioral":
            # קבל נתונים התנהגותיים זמינים
            display_manager.texts_to_fade_in = self.get_prepared_behavioral_texts(display_manager)
        else:
            # קבל נתונים חזותיים זמינים
            display_manager.texts_to_fade_in = self.get_prepared_visual_texts(display_manager)

        if display_manager.texts_to_fade_in:
            random.shuffle(display_manager.texts_to_fade_in)  # סדר רנדומלי

        # גם הכן את רשימת ההעלמה בסדר רנדומלי אם לא הוכנה
        if not display_manager.texts_to_fade_out:
            if display_manager.display_mode == "visual":
                display_manager.texts_to_fade_out = list(display_manager.text_positions.keys()).copy()
            else:
                display_manager.texts_to_fade_out = list(display_manager.behavioral_text_positions.keys()).copy()

            if display_manager.texts_to_fade_out:
                random.shuffle(display_manager.texts_to_fade_out)

    def get_prepared_behavioral_texts(self, display_manager):
        """מחזיר רשימת טקסטים התנהגותיים מוכנה"""
        # זה יעבוד רק אם יש נתונים זמינים
        if hasattr(display_manager, '_cached_behavioral_data'):
            return display_manager._cached_behavioral_data.copy()
        return []

    def get_prepared_visual_texts(self, display_manager):
        """מחזיר רשימת טקסטים חזותיים מוכנה"""
        # זה יעבוד רק אם יש נתונים זמינים
        if hasattr(display_manager, '_cached_visual_data'):
            return display_manager._cached_visual_data.copy()
        return []

    def start_text_fade_out(self, display_manager, text_key, current_time):
        """מתחיל fade out לטקסט ספציפי"""
        if display_manager.display_mode == "visual" and text_key in display_manager.text_positions:
            # קבע זמן התחלה של fade out
            display_manager.text_positions[text_key]['fade_out_start'] = current_time
            display_manager.text_positions[text_key]['fade_out_duration'] = 1.0  # שנייה אחת
        elif display_manager.display_mode == "behavioral" and text_key in display_manager.behavioral_text_positions:
            # קבע זמן התחלה של fade out
            display_manager.behavioral_text_positions[text_key]['fade_out_start'] = current_time
            display_manager.behavioral_text_positions[text_key]['fade_out_duration'] = 1.0  # שנייה אחת

    def start_text_fade_in(self, display_manager, text_key, current_time):
        """מתחיל fade in לטקסט חדש"""
        if display_manager.target_mode == "behavioral":
            display_manager.text_renderer.add_new_text(display_manager, text_key, current_time,
                                                       display_manager.behavioral_text_positions,
                                                       display_manager.behavioral_occupied_cells,
                                                       display_manager.behavioral_cell_last_used, is_behavioral=True)
        else:
            display_manager.text_renderer.add_new_text(display_manager, text_key, current_time,
                                                       display_manager.text_positions,
                                                       display_manager.occupied_cells, display_manager.cell_last_used,
                                                       is_behavioral=False)

    def complete_transition(self, display_manager):
        """משלים את המעבר"""
        display_manager.display_mode = display_manager.target_mode
        display_manager.in_transition = False
        display_manager.transition_stage = 0

        # נקה טקסטים ישנים שסיימו fade out
        self.cleanup_faded_texts(display_manager)

        print(f"✅ TRANSITION COMPLETE: Now in {display_manager.display_mode} mode")

    def cleanup_faded_texts(self, display_manager):
        """מנקה טקסטים שסיימו fade out"""
        current_time = time.time()

        # נקה טקסטים חזותיים
        keys_to_remove = []
        for key, data in display_manager.text_positions.items():
            if 'fade_out_start' in data and current_time - data['fade_out_start'] > 1.0:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in display_manager.text_positions[key]:
                cell = display_manager.text_positions[key]['grid_cell']
                display_manager.occupied_cells.discard(cell)
                display_manager.cell_last_used[cell] = current_time
            del display_manager.text_positions[key]

        # נקה טקסטים התנהגותיים
        keys_to_remove = []
        for key, data in display_manager.behavioral_text_positions.items():
            if 'fade_out_start' in data and current_time - data['fade_out_start'] > 1.0:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in display_manager.behavioral_text_positions[key]:
                cell = display_manager.behavioral_text_positions[key]['grid_cell']
                display_manager.behavioral_occupied_cells.discard(cell)
                display_manager.behavioral_cell_last_used[cell] = current_time
            del display_manager.behavioral_text_positions[key]

    def cleanup_transition_texts(self, display_manager, current_time):
        """מנקה טקסטים שסיימו fade out במהלך מעבר"""
        # נקה טקסטים חזותיים
        keys_to_remove = []
        for key, data in display_manager.text_positions.items():
            if 'fade_out_start' in data:
                fade_elapsed = current_time - data['fade_out_start']
                if fade_elapsed > data.get('fade_out_duration', 1.0):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in display_manager.text_positions[key]:
                cell = display_manager.text_positions[key]['grid_cell']
                display_manager.occupied_cells.discard(cell)
                display_manager.cell_last_used[cell] = current_time
            del display_manager.text_positions[key]

        # נקה טקסטים התנהגותיים
        keys_to_remove = []
        for key, data in display_manager.behavioral_text_positions.items():
            if 'fade_out_start' in data:
                fade_elapsed = current_time - data['fade_out_start']
                if fade_elapsed > data.get('fade_out_duration', 1.0):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if 'grid_cell' in display_manager.behavioral_text_positions[key]:
                cell = display_manager.behavioral_text_positions[key]['grid_cell']
                display_manager.behavioral_occupied_cells.discard(cell)
                display_manager.behavioral_cell_last_used[cell] = current_time
            del display_manager.behavioral_text_positions[key]

    def display_transition_texts(self, display_manager, black_screen, json_data_path, behavioral_data_path):
        """הצגת טקסטים במהלך מעבר עם fade out/in"""
        from PIL import Image, ImageDraw, ImageFont
        import cv2
        import numpy as np

        pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        current_time = time.time()

        try:
            font_base = ImageFont.load_default()
        except:
            font_base = None

        # עדכן cache של נתונים אם צריך
        if not hasattr(display_manager, '_cached_behavioral_data'):
            data_lines = display_manager._get_behavioral_data_lines(behavioral_data_path)
            display_manager._cached_behavioral_data = [line.strip() for line in data_lines if line.strip()]

        if not hasattr(display_manager, '_cached_visual_data'):
            data_lines = display_manager._get_visual_data_lines(json_data_path)
            display_manager._cached_visual_data = [line.strip() for line in data_lines if line.strip()]

        # הצג טקסטים קיימים (כולל אלה במצב fade out)
        if display_manager.display_mode == "visual":
            display_manager.text_renderer.draw_transition_texts(display_manager, draw, font_base, current_time,
                                                                display_manager.text_positions, is_behavioral=False)
        else:
            display_manager.text_renderer.draw_transition_texts(display_manager, draw, font_base, current_time,
                                                                display_manager.behavioral_text_positions,
                                                                is_behavioral=True)

        # הצג טקסטים חדשים שנוספו
        if hasattr(display_manager, 'target_mode') and display_manager.target_mode == "behavioral":
            display_manager.text_renderer.draw_transition_texts(display_manager, draw, font_base, current_time,
                                                                display_manager.behavioral_text_positions,
                                                                is_behavioral=True)
        else:
            display_manager.text_renderer.draw_transition_texts(display_manager, draw, font_base, current_time,
                                                                display_manager.text_positions, is_behavioral=False)

        # נקה טקסטים שסיימו fade out
        self.cleanup_transition_texts(display_manager, current_time)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def trigger_scene_transition(self, display_manager):
        """מפעיל מעבר הדרגתי לסצנה חדשה"""
        if display_manager.in_transition:
            return

        current_time = time.time()
        display_manager.in_transition = True
        display_manager.transition_stage = 0
        display_manager.last_transition_step_time = current_time
        display_manager.target_mode = display_manager.display_mode  # נשאר באותו מצב

        # הכן רשימת כל הטקסטים להעלמה
        all_texts = []

        if display_manager.display_mode == "visual":
            all_texts.extend(list(display_manager.text_positions.keys()))
        else:
            all_texts.extend(list(display_manager.behavioral_text_positions.keys()))

        random.shuffle(all_texts)
        display_manager.texts_to_fade_out = all_texts
        display_manager.texts_to_fade_in = []  # יתמלא מאוחר יותר עם נתונים חדשים
        display_manager.scene_transition = True