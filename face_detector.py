import cv2
import numpy as np


class FaceDetector:
    def __init__(self):
        # טעינת מודל Haar Cascade לזיהוי פנים (מגיע עם OpenCV)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # אלטרנטיבה: אם רוצים להשתמש ב-DNN (מדויק יותר אבל יותר כבד)
        # self.net = cv2.dnn.readNetFromTensorflow('opencv_face_detector_uint8.pb', 'opencv_face_detector.pbtxt')

    def detect_faces(self, frame):
        """
        מזהה פנים בפריים ומחזיר את מספר הפנים שזוהו
        """
        # המרה לגווני אפור לזיהוי מהיר יותר
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # זיהוי פנים
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,  # גורם קנה מידה
            minNeighbors=5,  # מספר שכנים מינימלי לאישור זיהוי
            minSize=(30, 30),  # גודל מינימלי לפנים
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        return len(faces), faces

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
            cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        return debug_frame