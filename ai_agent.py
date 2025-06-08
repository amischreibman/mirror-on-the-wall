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
        self.prompt = """
        in each session, in condition that at least one person is in the frame, analyze the image and identify any people present. For each session give a serial number counting the sessions, "002" for example, and for each image count how many people are visible inside the camera's frame, and for each person provide a serial 4 digits random numbers as "person_id" and also provide the following details.
        If one person identify, provide the answer as a JSON array of objects and strings, where each object represents a session. Do not include any additional text outside the JSON array.
        Example for a JSON array:
{
  "session_id": "008",
  "session": [
    {
      "person_id": 1023,
      "descriptions": [
        "Appears to be between 20 and 30 years old",
        "Male",
        "Approximately 175 cm tall",
        "Slim body structure",
        "Fair skin tone",
        "Has a small scar above the left eyebrow",
        "Light stubble on chin",
        "Dark brown, wavy hair of medium length, reaching the shoulders tied back in a braided ponytail"
      ]
    }
  ]
}

            For each person, describe any visible element you able to see in frame, with high details and add them to the description array. Focus solely on static visual elements and objects directly linked to the person, or part of his body or face. STRICTLY IGNORE: temporary body movements, gestures, poses, facial expressions, hand positions, head positions, eye directions, any temporary actions or movements. ONLY describe permanent physical features and static visible objects.
            CRITICAL RULES:
1. NEVER describe background objects, furniture, walls, or environment. Only describe the PERSON.
2. Maximum 5 descriptions per category. If you already have 5 items in a category, replace the oldest one.
3. Focus ONLY on the person's body, face, clothing, and accessories that are ON the person.
4. DO NOT describe chairs, walls, shelves, or any background elements.
.IMPORTANT: Never use action verbs in descriptions. Instead of "לובש חולצה לבנה" write "חולצה לבנה". Instead of "עוטה" write only the item name. NO VERBS - only nouns and adjectives describing what you see. Pay close attention to accessories and unique features.
            NEVER describe what you DON'T see. Only describe what you CAN see. Never write "ללא משקפיים" or "אין תכשיטים" - only write about items that are actually visible.
Pay special attention to accessories like watches, jewelry, glasses when hands or body parts become visible.
            Possible details and examples:
                    -Appears to be between 20 and 30 years old
                    -Male
                    -Approximately 175 cm tall
                    -Slim body structure
                    -bright skin tone
                    -Has a small scar above the left eyebrow
                    -Light stubble on chin
                    -Dark brown, wavy hair of medium length, reaching the shoulders
                    -Hair is tied back in a braided ponytail
                    -Wearing black framed eyeglasses
                    -Hazel eyes
                    -Head is held straight
                    -Looking forward
                    -Facial expression is neutral
                    -Wearing a blue t-shirt
                    -Wearing black jeans
                    -Wearing a baseball cap
                    -Wearing white sneakers
                    -Wearing white socks
                    -Wearing a silver ring
                    -Wearing a gold necklace
                    -Wearing a smartwatch on the left wrist
                    -Holding a smartphone
                    -Holding a coffee mug in the right hand
                when you looking for something but it is not visible, you ignore it until you see it, if and when you will see it inside the frame for sure
                do not mention the categories, just make a list of descriptions. if see something that you already provided for the person with the same user_id serial number, then do not repeat it again. just add only new things you see with this person.
                if more then one person stand in front of camera in the frame, make 2 different persons separately inside the session array.
                 Example for 3 people in the frame:
                 {
  "session_id": "008",
  "session": [
    {
      "person_id": 1023,
      "descriptions": [
        "Appears to be between 20 and 30 years old",
        "Male",
        "Approximately 175 cm tall",
        "Slim body structure",
        "Fair skin tone",
        "Has a small scar above the left eyebrow",
        "Light stubble on chin",
        "Dark brown, wavy hair of medium length, reaching the shoulders tied back in a braided ponytail"
      ]
    },
    {
      "person_id": 2045,
      "descriptions": [
        "Appears to be between 40 and 50 years old",
        "Female",
        "Approximately 162 cm tall",
        "Curvy body structure",
        "Medium olive skin tone",
        "No visible scars or marks",
        "Shoulder-length straight auburn hair",
        "Wearing red lipstick and pearl earrings",
        "Wearing a white blouse and gray trousers",
        "Holding a tablet in her left hand"
      ]
    },
    {
      "person_id": 3198,
      "descriptions": [
        "Appears to be in late teens",
        "Non-binary",
        "Approximately 180 cm tall",
        "Athletic body structure",
        "Light brown skin tone",
        "Freckles across the nose",
        "Short buzzcut dyed light blue",
        "Wearing a black hoodie with a neon green logo",
        "Wearing ripped blue jeans",
        "Carrying a skateboard and wearing wireless headphones"
      ]
    }
  ]
}
                 only if no person is in the frame, then just start a new session array with that person alone, using the same person id, and same list of visual descriptions already made. 
                If no people are identified in the frame, then return None.
                all descriptions that you send in your answers, need to be in Hebrew language only!,
                for example, the session:
                    {
                      "session_id": "008",
                      "session": [
                        {
                          "person_id": 1023,
                          "descriptions": [
                            "Appears to be between 20 and 30 years old",
                            "Male",
                            "Approximately 175 cm tall",
                            "Slim body structure",
                            "Fair skin tone",
                            "Has a small scar above the left eyebrow",
                            "Light stubble on chin",
                            "Dark brown, wavy hair of medium length, reaching the shoulders tied back in a braided ponytail"
                          ]
                        }
                      ]
                    }
                    will be send as a Hebrew description like this:
                    {
  "session_id": "008",
  "session": [
    {
      "person_id": 1023,
      "descriptions": [
        "בערך בגיל שבין 20 ל-30",
        "זכר",
        "הגובה המשוער הוא 175 ס״מ",
        "מבנה הגוף נראה רזה",
        "גוון העור בצבע בהיר",
        "נצפתה צלקת קטנה מעל הגבה השמאלית",
        "זקן קטן על הסנטר",
        "שיער חום כהה, גלי, באורך בינוני עד הכתפיים, אסוף בצמה לאחור"
      ]
    }
  ]
}                
IMPORTANT RULES:
1. NEVER repeat descriptions you already gave for the same person_id
2. If you see something NEW about a person (like a watch that wasn't visible before), add only that NEW item
3. If you want to CORRECT a previous description (like age), REPLACE it, don't add both
4. NEVER describe temporary gestures, movements, or poses (like "hand on chin", "looking up", "pointing")
5. Only describe PERMANENT visual features and STATIC objects that are visible
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