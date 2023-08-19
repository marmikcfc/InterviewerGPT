""" Created by gpt 4. So, be careful before using it. """
from weaviate import Client

class WeaviateMemory:
    def __init__(self, weaviate_url, interview_id):
        self.client = Client(weaviate_url)
        self.interview_id = interview_id
        self.transcript = []

    def add_interaction(self, user_input, model_response):
        # Add interaction to local transcript
        self.transcript.append({
            "userInput": user_input,
            "modelResponse": model_response
        })

        # Save or update interview transcript in Weaviate
        interview = self.client.get_object_by_id(self.interview_id, "Interview")
        if interview:
            # Update existing interview transcript
            interview["transcript"].append({
                "userInput": user_input,
                "modelResponse": model_response
            })
            self.client.update_object(self.interview_id, interview, "Interview")
        else:
            # Create new interview transcript
            interview_data = {
                "interview_id": self.interview_id,
                "transcript": self.transcript
            }
            self.client.create_object(interview_data, "Interview")

    def get_history(self):
        # Retrieve chat history from Weaviate
        interview = self.client.get_object_by_id(self.interview_id, "Interview")
        return interview["transcript"] if interview else []

    def reset(self):
        # Clear local transcript
        self.transcript.clear()
        # Optionally, you can also delete the interview transcript from Weaviate:
        # self.client.delete_object(self.interview_id, "Interview")
