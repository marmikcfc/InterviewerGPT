import random
import json
from interview_types import InterviewTypes

# Stimulating a question database 
with open('questions.json', 'r') as f:
    questions_db = json.load(f)

def get_question(interview_type):
    num = random.randint(0, 5)
    if interview_type == InterviewTypes.CODING_INTERVIEW:
        question = questions_db["coding"][num]
        return f"""Question: {question["question"]} 
        Explaination {question["explaination"]}
        """


#I'm doing well, thanks. How are you doing?