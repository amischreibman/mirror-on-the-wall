import random
import os
import json
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np


class PromptGenerator:
    def __init__(self):
        self.prompt_char_interval = 0.05  # מרווח זמן בין תווים (50ms)

    def generate_image_prompt(self, display_manager):
        """יצירת פרומפט לתמונה מהנתונים שנאספו"""
        if display_manager.prompt_generated:
            return display_manager.prompt_text

        # איסוף כל הנתונים
        visual_data, behavioral_data = self.get_all_collected_data(display_manager)

        # תרגום טקסטים עבריים לאנגלית (מיפוי בסיסי)
        translations = {
            "זכר": "male", "נקבה": "female", "גבר": "man", "אישה": "woman",
            "צעיר": "young", "מבוגר": "adult", "זקן": "elderly", "ילד": "child",
            "גבוה": "tall", "נמוך": "short", "רזה": "slim", "שמן": "heavy",
            "חולצה": "shirt", "מכנסיים": "pants", "נעליים": "shoes", "משקפיים": "glasses",
            "שעון": "watch", "טבעת": "ring", "שרשרת": "necklace", "כובע": "hat",
            "שיער": "hair", "עיניים": "eyes", "חום": "brown", "שחור": "black",
            "לבן": "white", "כחול": "blue", "ירוק": "green", "אדום": "red",
            "מסוקרן": "curious", "עצוב": "sad", "שמח": "happy", "חושש": "anxious",
            "בטוח": "confident", "ביישן": "shy", "עצבני": "nervous", "רגוע": "calm"
        }

        # פונקציה לתרגום בסיסי
        def translate_text(text):
            for heb, eng in translations.items():
                if heb in text:
                    return eng
            return ""

        # בניית הפרומפט
        prompt_parts = []

        # תיאור ראשוני מורחב
        prompt_parts.append("Create a hyperrealistic portrait of a person")

        # הוספת פרטים דמוגרפיים מהנתונים החזותיים
        age_desc = "middle-aged"
        gender_desc = "person"
        appearance_desc = []
        clothing_desc = []
        accessories_desc = []

        for item in visual_data:
            trans = translate_text(item)
            if trans:
                if any(word in trans for word in ["male", "female", "man", "woman"]):
                    gender_desc = trans
                elif any(word in trans for word in ["young", "adult", "elderly", "child"]):
                    age_desc = trans
                elif any(word in trans for word in ["tall", "short", "slim", "heavy"]):
                    appearance_desc.append(trans)
                elif any(word in trans for word in ["shirt", "pants", "shoes"]):
                    clothing_desc.append(trans)
                elif any(word in trans for word in ["watch", "ring", "necklace", "glasses"]):
                    accessories_desc.append(trans)

        # בניית תיאור האדם
        prompt_parts.append(f"showing a {age_desc} {gender_desc}")

        # הוספת סיפור רקע מפורט
        backgrounds = [
            "from a middle-class suburban family with academic background",
            "raised in an artistic household surrounded by creativity",
            "coming from a traditional working-class neighborhood",
            "with multicultural heritage blending Eastern and Western values",
            "from an entrepreneurial family running small businesses"
        ]
        prompt_parts.append(random.choice(backgrounds))

        # תיאור סוציו-אקונומי
        socio_economic = [
            "displaying subtle signs of comfortable financial status",
            "showing modest lifestyle choices with practical priorities",
            "exhibiting refined taste within reasonable means",
            "presenting carefully curated professional appearance",
            "reflecting pragmatic approach to material possessions"
        ]
        prompt_parts.append(random.choice(socio_economic))

        # ביגוד ואביזרים
        if clothing_desc:
            prompt_parts.append(f"wearing {', '.join(clothing_desc[:2])}")
        else:
            prompt_parts.append("wearing casual contemporary clothing")

        if accessories_desc:
            prompt_parts.append(f"accessorized with {', '.join(accessories_desc[:2])}")

        # רגשות ותחושות מהנתונים ההתנהגותיים
        emotions = []
        for behavior in behavioral_data[:5]:
            trans = translate_text(behavior)
            if trans and trans not in emotions:
                emotions.append(trans)

        if emotions:
            prompt_parts.append(f"expressing {' mixed with '.join(emotions[:2])} emotions")
        else:
            prompt_parts.append("with complex emotional depth in their expression")

        # תחביבים ועניינים
        hobbies = [
            "passionate about photography and visual storytelling",
            "devoted to reading philosophy and contemporary literature",
            "enthusiastic about cooking fusion cuisine",
            "dedicated to urban gardening and sustainability",
            "interested in digital art and technology"
        ]
        prompt_parts.append(random.choice(hobbies))

        # תכונות חברתיות
        social_traits = [
            "naturally sociable with genuine warmth towards others",
            "selectively social preferring meaningful connections",
            "quietly charismatic with thoughtful presence",
            "energetically engaging in group dynamics",
            "diplomatically navigating social situations"
        ]
        prompt_parts.append(random.choice(social_traits))

        # רקע תרבותי
        cultural_backgrounds = [
            "with Mediterranean cultural influences evident in gestures",
            "showing subtle Middle Eastern heritage in facial features",
            "displaying European sensibilities in style choices",
            "reflecting cosmopolitan multicultural identity",
            "embodying blend of traditional and modern values"
        ]
        prompt_parts.append(random.choice(cultural_backgrounds))

        # הוספת אווירה ארטיסטית
        prompt_parts.append("captured in dramatic chiaroscuro lighting")
        prompt_parts.append("with background suggesting personal narrative")
        prompt_parts.append("photorealistic details revealing character depth")
        prompt_parts.append("8k resolution showing every nuanced expression")

        # בניית הפרומפט הסופי
        full_prompt = " ".join(prompt_parts)

        # וידוא 100 מילים בדיוק
        words = full_prompt.split()
        if len(words) > 100:
            words = words[:100]
        elif len(words) < 100:
            fillers = ["masterfully", "beautifully", "expertly", "carefully", "thoughtfully"]
            while len(words) < 100:
                words.insert(random.randint(0, len(words)), random.choice(fillers))

        display_manager.prompt_text = " ".join(words[:100])
        display_manager.prompt_generated = True

        return display_manager.prompt_text

    def display_prompt_with_typewriter(self, display_manager, black_screen, current_time):
        """הצגת הפרומפט עם אפקט הקלדה"""

        # יצירת הפרומפט אם עדיין לא נוצר
        if not display_manager.prompt_generated:
            self.generate_image_prompt(display_manager)
            display_manager.prompt_last_char_time = current_time

        # חישוב כמה תווים להציג
        if current_time - display_manager.prompt_last_char_time >= self.prompt_char_interval:
            if display_manager.prompt_display_index < len(display_manager.prompt_text):
                display_manager.prompt_display_index += 1
                display_manager.prompt_last_char_time = current_time

        # הטקסט להצגה (עד האינדקס הנוכחי)
        display_text = display_manager.prompt_text[:display_manager.prompt_display_index]

        # יצירת תמונת PIL לציור טקסט
        pil_image = Image.fromarray(cv2.cvtColor(black_screen, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # הגדרת פונט
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        # חישוב גודל הטקסט ומיקומו - יישור לשמאל
        margin = 100
        max_width = display_manager.screen_width - (2 * margin)

        # פיצול לשורות
        words = display_text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except:
                line_width = len(test_line) * 12  # הערכה

            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # חישוב גובה כולל
        line_height = 35
        total_height = len(lines) * line_height

        # מיקום התחלתי (מרכז אנכי, יישור שמאל)
        start_y = (display_manager.screen_height - total_height) // 2
        x_position = margin  # יישור לשמאל עם margin

        # ציור השורות
        for i, line in enumerate(lines):
            y = start_y + (i * line_height)

            # צבע לבן עם שקיפות בהתאם למצב
            opacity = int(255 * display_manager.prompt_opacity)
            color = (opacity, opacity, opacity)

            # ציור הטקסט מיושר לשמאל (רק אם יש שקיפות)
            if opacity > 0:
                draw.text((x_position, y), line, fill=color, font=font)

        # הוספת סמן הקלדה מהבהב
        if display_manager.prompt_display_index < len(display_manager.prompt_text):
            # הבהוב הסמן
            if int(current_time * 2) % 2 == 0:  # הבהוב כל חצי שנייה
                cursor = "_"
                if lines:
                    # מצא את המיקום של הסמן בסוף הטקסט הנוכחי
                    last_line = lines[-1]
                    y = start_y + ((len(lines) - 1) * line_height)

                    try:
                        bbox = draw.textbbox((0, 0), last_line, font=font)
                        cursor_x = x_position + bbox[2] - bbox[0] + 5
                    except:
                        cursor_x = x_position + len(last_line) * 12 + 5

                    opacity = int(255 * display_manager.prompt_opacity)
                    color = (opacity, opacity, opacity)
                    if opacity > 0:
                        draw.text((cursor_x, y), cursor, fill=color, font=font)

        # הוספת כותרת - גם מיושרת לשמאל
        title = "AI IMAGE GENERATION PROMPT:"
        title_font = font

        title_x = x_position
        title_y = start_y - 60

        opacity = int(255 * display_manager.prompt_opacity)
        if opacity > 0:
            title_color = (int(100 * display_manager.prompt_opacity),
                           int(255 * display_manager.prompt_opacity),
                           int(100 * display_manager.prompt_opacity))
            draw.text((title_x, title_y), title, fill=title_color, font=title_font)

        # המרה חזרה ל-OpenCV
        black_screen[:] = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def get_all_collected_data(self, display_manager):
        """איסוף כל הנתונים שנאספו מהמאגרים"""
        visual_data = []
        behavioral_data = []

        # איסוף נתונים חזותיים
        if display_manager.visual_data_path and os.path.exists(display_manager.visual_data_path):
            try:
                with open(display_manager.visual_data_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    sessions = json_data.get("sessions", [])

                    for session in sessions:
                        people = session.get("session", [])
                        for person in people:
                            categories = person.get("categories", {})
                            for category, items in categories.items():
                                visual_data.extend(items)
            except Exception as e:
                print(f"Error reading visual data: {e}")

        # איסוף נתונים התנהגותיים
        if display_manager.behavioral_data_path and os.path.exists(display_manager.behavioral_data_path):
            try:
                with open(display_manager.behavioral_data_path, 'r', encoding='utf-8') as f:
                    behavioral_json = json.load(f)
                    sessions = behavioral_json.get("sessions", [])

                    for session in sessions:
                        insights = session.get("behavioral_analysis", [])
                        behavioral_data.extend(insights)
            except Exception as e:
                print(f"Error reading behavioral data: {e}")

        # הסרת כפילויות
        visual_data = list(set(visual_data))
        behavioral_data = list(set(behavioral_data))

        return visual_data, behavioral_data