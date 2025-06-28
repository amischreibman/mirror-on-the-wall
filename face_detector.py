import cv2
import numpy as np
import dlib


class FaceDetector:
    def __init__(self):
        # אתחול dlib עם מודלי OpenFace
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor('openface/models/dlib/shape_predictor_68_face_landmarks.dat')
        self.face_rec_model = dlib.face_recognition_model_v1(
            'openface/models/dlib/dlib_face_recognition_resnet_model_v1.dat')

        print("✅ OpenFace/dlib models initialized successfully")

    def detect_faces(self, frame):
        """
        מזהה פנים בפריים ומחזיר את מספר הפנים שזוהו
        תואם לממשק הקיים של הקוד
        """
        # המרה לגווני אפור
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # זיהוי פנים עם dlib
        faces = self.detector(gray)

        # המרה לפורמט OpenCV לתואמות עם הקוד הקיים
        opencv_faces = []
        for face in faces:
            x = face.left()
            y = face.top()
            w = face.width()
            h = face.height()
            opencv_faces.append((x, y, w, h))

        return len(opencv_faces), opencv_faces

    def detect_faces_with_landmarks(self, frame):
        """
        זיהוי פנים מתקדם עם landmarks ו-embeddings
        """
        # המרה לגווני אפור
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # זיהוי פנים
        faces = self.detector(gray)

        face_data = []
        for face in faces:
            # קבלת landmarks (68 נקודות)
            landmarks = self.predictor(gray, face)

            # קבלת embedding עם מודל OpenFace/dlib
            face_encoding = self.face_rec_model.compute_face_descriptor(frame, landmarks)

            # פרטי הפנים
            face_info = {
                'bbox': (face.left(), face.top(), face.width(), face.height()),
                'landmarks': landmarks,
                'encoding': np.array(face_encoding),
                'confidence': 1.0  # dlib לא מחזיר confidence, אז נשים 1.0
            }
            face_data.append(face_info)

        return len(face_data), face_data

    def has_people(self, frame):
        """
        בדיקה מהירה האם יש אנשים בפריים
        מחזיר True אם יש לפחות אדם אחד
        """
        face_count, _ = self.detect_faces(frame)
        return face_count > 0

    def draw_faces_debug(self, frame, faces):
        """
        מציירת מלבנים סביב הפנים שזוהו (לדיבאג)
        """
        debug_frame = frame.copy()
        for (x, y, w, h) in faces:
            cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # הוסף תווית
            cv2.putText(debug_frame, 'OpenFace/dlib', (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return debug_frame

    def draw_landmarks_debug(self, frame, landmarks):
        """
        מציירת את 68 הנקודות על הפנים
        """
        debug_frame = frame.copy()
        for i in range(68):
            x = landmarks.part(i).x
            y = landmarks.part(i).y
            cv2.circle(debug_frame, (x, y), 2, (0, 255, 255), -1)
        return debug_frame

    def get_face_encodings(self, frame):
        """
        מחזיר encodings של כל הפנים בפריים
        שימושי להשוואת פנים וזיהוי אנשים
        """
        _, face_data = self.detect_faces_with_landmarks(frame)
        encodings = []

        for face_info in face_data:
            encodings.append({
                'bbox': face_info['bbox'],
                'encoding': face_info['encoding']
            })

        return encodings

    def compare_faces(self, encoding1, encoding2, threshold=0.6):
        """
        השוואת שני encodings של פנים
        מחזיר True אם זה אותו אדם
        threshold נמוך יותר = דיוק גבוה יותר אבל פחות רגיש
        """
        if encoding1 is None or encoding2 is None:
            return False

        # חישוב מרחק אוקלידי
        distance = np.linalg.norm(encoding1 - encoding2)
        return distance < threshold

    def get_face_quality_score(self, frame, face_bbox):
        """
        מחזיר ציון איכות לפנים (0-1)
        בוצר על בסיס גודל, בהירות ופרונטליות
        """
        x, y, w, h = face_bbox
        face_roi = frame[y:y + h, x:x + w]

        # בדיקת גודל (פנים גדולות יותר = איכות טובה יותר)
        size_score = min(1.0, (w * h) / (100 * 100))  # נורמליזציה ל-100x100 פיקסלים

        # בדיקת בהירות (לא חשוך מדי ולא בהיר מדי)
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray_roi)
        brightness_score = 1.0 - abs(brightness - 128) / 128  # 128 זה בהירות אידיאלית

        # ציון כולל
        quality_score = (size_score + brightness_score) / 2
        return max(0.0, min(1.0, quality_score))