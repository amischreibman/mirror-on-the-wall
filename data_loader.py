import os
import json


class DataLoader:
    def __init__(self):
        pass

    def get_visual_data_lines(self, json_data_path):
        """קבלת נתונים חזותיים מהמאגר הראשון"""
        data_lines = []
        if os.path.exists(json_data_path):
            try:
                with open(json_data_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                    if "sessions" in json_data and isinstance(json_data["sessions"], list):
                        if len(json_data["sessions"]) == 0:
                            data_lines.append("No sessions available")
                        else:
                            latest_session = json_data["sessions"][-1]
                            session_people = latest_session.get("session", [])

                            if len(session_people) > 0:
                                for person_data in session_people:
                                    categories = person_data.get("categories", {})

                                    if categories:
                                        for category_name, items in categories.items():
                                            if items:
                                                for item in items:
                                                    data_lines.append(item)
                    else:
                        data_lines.append("No session data available")
            except (IOError, json.JSONDecodeError) as e:
                data_lines.append(f"Error reading JSON: {e}")
        else:
            data_lines.append("JSON file not found")

        return data_lines

    def get_behavioral_data_lines(self, display_manager, behavioral_data_path):
        """קבלת נתונים התנהגותיים מהמאגר השני"""
        data_lines = []
        if os.path.exists(behavioral_data_path):
            try:
                with open(behavioral_data_path, 'r', encoding='utf-8') as f:
                    behavioral_data = json.load(f)

                    if "sessions" in behavioral_data and isinstance(behavioral_data["sessions"], list):
                        if len(behavioral_data["sessions"]) == 0:
                            data_lines.append("No behavioral sessions available")
                        else:
                            # אסוף את כל המשפטים מכל הסשנים
                            all_insights = []
                            for session in behavioral_data["sessions"]:
                                insights = session.get("behavioral_analysis", [])
                                all_insights.extend(insights)

                            # הסר כפילויות
                            unique_insights = list(set(all_insights))
                            data_lines.extend(unique_insights)

                            # עדכן את המאגר למחזור
                            if unique_insights and len(unique_insights) > len(display_manager.behavioral_texts_pool):
                                display_manager.behavioral_texts_pool = unique_insights.copy()
                    else:
                        data_lines.append("No behavioral data available")
            except (IOError, json.JSONDecodeError) as e:
                data_lines.append(f"Error reading behavioral JSON: {e}")
        else:
            data_lines.append("Behavioral JSON file not found")

        return data_lines