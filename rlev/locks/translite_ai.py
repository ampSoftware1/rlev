import openai
import os

client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # המפתח נשמר במשתנה סביבה

def transliterate_hebrew_name(name):
    prompt = f""" תעתק את שם הפרטי הבא מעברית לאנגלית. אל תתרגם את המשמעות, רק תכתוב איך היית כותב את השם באנגלית כמו שנהוג בדרכון בפלט אל תכלול שום דבר חוץ מאת השם עצמו ותו לא: 
שם: {name}
תעתיק באנגלית:"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

def translate_hospital_department(department_name):
    prompt = f"""תרגם את שם המחלקה הבאה בבית חולים מעברית לאנגלית. הקפד לשמור על מונחים מקצועיים והקשר רפואי נא לכלול בפלט את התרגום בלבד ותו לא:
שם המחלקה: {department_name}
תרגום באנגלית:"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


