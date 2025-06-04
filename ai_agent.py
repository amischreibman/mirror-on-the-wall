import os  # ייבוא מודול לגישה למערכת ההפעלה
from dotenv import load_dotenv  # ייבוא פונקציה לטעינת משתני סביבה
import google.generativeai as genai  # ייבוא ספריית גוגל ג'מיני
from PIL import Image  # ייבוא ספריית Pillow לעבודה עם תמונות
import cv2  # ייבוא OpenCV להמרת תמונה
import numpy as np  # ייבוא NumPy לעבודה עם מערכים
import json  # ייבוא לדיבאג


class AIAgent:  # הגדרת מחלקה לסוכן הבינה המלאכותית
    def __init__(self):  # פונקציית אתחול למחלקה
        load_dotenv()  # טעינת משתני סביבה מקובץ .env
        api_key = os.getenv("GOOGLE_API_KEY")  # קבלת מפתח ה-API ממשתני הסביבה

        if not api_key:  # בדיקה אם מפתח ה-API נמצא
            raise ValueError("GOOGLE_API_KEY not found in .env file.")  # זריקת שגיאה אם המפתח חסר

        genai.configure(api_key=api_key)  # הגדרת מפתח ה-API עבור ג'מיני
        self.model = genai.GenerativeModel('gemini-2.0-flash')  # אתחול מודל ה-Vision החדיש (Flash) של ג'מיני

        # הגדרת ההנחיה (פרומפט) לסוכן הבינה המלאכותית
        # הפרומפט מעודכן להסיר תיאורי תנועה.
        self.prompt = """
        Analyze the image and identify any people present. For each person, provide the following details. Omit key-value pairs if details are not visible. If no people are identified, return an empty JSON array.

        Provide the answer as a JSON array of objects, where each object represents a person. Do not include any additional text outside the JSON array.

        For each person, describe any visible attribute with high detail. Focus solely on static visual elements and objects directly linked to the person, not temporary body movements or gestures. Pay close attention to accessories and unique features.

        Possible details and examples:
        - estimated_age_range: "20-30"
        - estimated_biological_sex: "male"
        - estimated_height: "175 cm"
        - general_body_structure: "slim"
        - skin_tone: "fair"
        - unique_scars_or_marks: "small scar above left eyebrow"
        - visible_body_hair: "light stubble on chin"
        - hair_color: "dark brown"
        - hair_length: "medium length, reaching shoulders"
        - hair_type: "wavy"
        - hairstyle: "braided ponytail"
        - eye_color: "hazel"
        - eye_wear: "black framed eyeglasses"
        - head_posture: "straight"
        - gaze_direction: "forward"
        - general_expression: "neutral"
        - upper_garment_type: "t-shirt"
        - upper_garment_color: "blue"
        - lower_garment_type: "jeans"
        - lower_garment_color: "black"
        - head_covering: "baseball cap"
        - footwear_type: "sneakers"
        - footwear_color: "white"
        - wearing_socks: "yes"
        - jewelry: "silver ring, gold necklace"
        - watch: "smartwatch on left wrist"
        - accompanying_technology: "smartphone"
        - held_objects: "coffee mug"
        """

        self.frame_count = 0  # מונה פריימים לדיבאג

    def _convert_opencv_frame_to_pil(self, frame):  # פונקציה פרטית להמרת פריים לפורמט PIL
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # המרת צבע מ-BGR ל-RGB
        pil_image = Image.fromarray(rgb_frame)  # יצירת אובייקט PIL Image ממערך NumPy
        return pil_image  # החזרת תמונת PIL

    def analyze_frame(self, frame):  # פונקציה לניתוח פריים וידאו
        self.frame_count += 1
        print(f"\n=== AI Analysis Frame #{self.frame_count} ===")

        try:
            pil_image = self._convert_opencv_frame_to_pil(frame)  # המרת הפריים לאובייקט PIL
            response = self.model.generate_content([self.prompt, pil_image], stream=False)  # שליחת בקשה למודל
            response.resolve()  # המתנה לתשובה מלאה

            json_text = response.text.strip()  # הסרת רווחים מיותרים
            print(f"Raw AI response length: {len(json_text)} chars")

            # ניסיון לנקות את התשובה כדי לוודא שהיא JSON תקין
            if json_text.startswith("```json") and json_text.endswith("```"):  # אם יש עטיפת JSON
                json_text = json_text[len("```json"):-len("```")].strip()  # הסרת העטיפה

            # אם התשובה עדיין לא נראית כמו JSON של מערך
            if not json_text.startswith("[") or not json_text.endswith("]"):
                start_index = json_text.find('[')  # חיפוש התחלת מערך
                end_index = json_text.rfind(']')  # חיפוש סיום מערך
                if start_index != -1 and end_index != -1 and end_index > start_index:  # אם נמצא מערך תקין
                    json_text = json_text[start_index: end_index + 1]  # חילוץ המערך
                else:
                    print(f"AI response not valid JSON array: {json_text[:200]}...")  # הודעה אם ה-JSON לא תקין
                    return "[]"  # החזרת מערך JSON ריק במקרה של תקלה

            # בדיקת תוכן ה-JSON לדיבאג
            try:
                parsed_json = json.loads(json_text)
                if parsed_json and len(parsed_json) > 0:
                    print(f"AI detected {len(parsed_json)} person(s)")
                    print("Fields detected in this frame:")
                    for person in parsed_json:
                        print(f"  - {list(person.keys())}")
                else:
                    print("AI detected no people")
            except Exception as e:
                print(f"Error parsing JSON for debug: {e}")

            return json_text  # החזרת הטקסט כ-JSON (סטרינג)
        except Exception as e:  # טיפול בשגיאות
            print(f"Error analyzing frame with AI: {e}")  # הדפסת הודעת שגיאה
            return "[]"  # החזרת מערך JSON ריק במקרה של שגיאה