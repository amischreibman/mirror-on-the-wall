import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import cv2
import numpy as np


class BehavioralAnalyzer:
    """מחלקה לניתוח התנהגותי ופרשנות של אנשים במצלמה"""

    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # הגדרת הפרומפט לניתוח התנהגותי
        self.prompt = """
        אתה אנליסט התנהגותי מומחה. נתח את התמונה שלפניך ובמידה ויש בה אדם או יותר, צור בין 15 ל-40 משפטים קצרים (עד 8 מילים כל אחד) המתארים:

        התמקד אך ורק באדם/אנשים בתמונה - התעלם לחלוטין מהרקע, החדר, התאורה או כל אלמנט סביבתי.

        1. ניתוח התנהגות ומבט של האדם
        2. הסקת מסקנות מתנועות פנים של האדם
        3. פרשנות של כיוון מבט ותנודות של האדם
        4. ניתוח תנועות גוף ותנועות ידיים של האדם
        5. מסקנות מביגוד ואביזרים שעל האדם עצמו
        6. ניתוח של אינטראקציות בין אנשים (אם יש כמה אנשים)
        7. הסקת מסקנות על מצב רגשי, כלכלי, או חברתי של האדם

        חשוב: אל תתאר אף פעם את הרקע, החדר, הקירות, התאורה, הרהיטים או כל דבר שאינו חלק מהאדם עצמו.

        דוגמאות למשפטים (רק על האדם):
        "מבט מסוקרן לכיוון המצלמה"
        "שעון חכם על היד מעיד על מצב כלכלי אמיד"
        "ביגוד מרושל, ייתכן שרווקה"
        "תנודת גבות מעידה על פליאה"
        "מסדרת את השיער, נראה כי החזות חשובה"
        "חיוך באזור הפה וחשש בעיניים"
        "מחזיקה סמארטפון ביד, נראה כי מצלמת"
        "שני גברים עם הבדלי גילאים, ייתכן קרבה משפחתית"
        "עונד טבעת זהובה על האצבע, ככל הנראה נשוי"
        "תנועת יד עצבנית מעידה על חוסר נוחות"
        "עמידה זקופה מעידה על ביטחון עצמי"
        "מבט נמוך, ייתכן ביישנות או עצב"

        אסורים לחלוטין:
        - תיאור רקע, חדר, קירות, תאורה
        - תיאור רהיטים או חפצים שאינם על האדם
        - תיאור מיקום או סביבה
        - כל דבר שאינו קשור ישירות לאדם עצמו

        רק תיאור האדם והתנהגותו!

        החזר את התוצאה כ-JSON עם המבנה הבא:
        {
          "session_id": "מספר סשן בעל 3 ספרות",
          "behavioral_analysis": [
            "משפט 1",
            "משפט 2",
            "משפט 3"
          ]
        }

        אם אין אנשים בתמונה, החזר:
        {
          "session_id": "000",
          "behavioral_analysis": []
        }

        כל המשפטים חייבים להיות בעברית בלבד!
        """

        self.frame_count = 0

    def _convert_opencv_frame_to_pil(self, frame):
        """המרת פריים מ-OpenCV ל-PIL"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        return pil_image

    def analyze_behavior(self, frame):
        """ניתוח התנהגותי של פריים"""
        self.frame_count += 1
        print(f"\n=== Behavioral Analysis Frame #{self.frame_count} ===")

        try:
            pil_image = self._convert_opencv_frame_to_pil(frame)
            response = self.model.generate_content([self.prompt, pil_image], stream=False)
            response.resolve()

            json_text = response.text.strip()
            print(f"Raw behavioral analysis response length: {len(json_text)} chars")

            # ניקוי התשובה
            if json_text.startswith("```json") and json_text.endswith("```"):
                json_text = json_text[len("```json"):-len("```")].strip()

            # חיפוש JSON תקין
            start_index = json_text.find('{')
            end_index = json_text.rfind('}')
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_text = json_text[start_index: end_index + 1]
            else:
                print(f"Behavioral analysis not valid JSON: {json_text[:200]}...")
                return "{}"

            # בדיקת תוכן ה-JSON לדיבאג
            try:
                parsed_json = json.loads(json_text)
                behavioral_items = parsed_json.get("behavioral_analysis", [])
                if behavioral_items and len(behavioral_items) > 0:
                    print(f"Behavioral analysis detected {len(behavioral_items)} insights")
                else:
                    print("No behavioral insights detected")
            except Exception as e:
                print(f"Error parsing behavioral JSON for debug: {e}")

            return json_text

        except Exception as e:
            print(f"Error analyzing behavior: {e}")
            return "{}"