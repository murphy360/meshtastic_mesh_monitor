import os
from google import genai
from google.genai import types # type: ignore

class GeminiInterface:
    def __init__(self, project_id: str, location: str, model: str):
        self.project_id = project_id
        self.location = location
        self.model = model
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        gemini_client = genai.Client(api_key=gemini_api_key)
        who = "You are a an AI named DPMM (Don't Panic Mesh Monitor). You have a background in radio communications, have a quirky sense of humor, love history and previously worked in the United States Navy."
        what = "You are tasked with monitoring a meshtastic mesh network.  Public messages have certain "
        public_chat = gemini_client.chats.create(
        model='gemini-2.0-flash-001',
        config=types.GenerateContentConfig(
            system_instruction="You are tasked with monitoring a meshtastic mesh network. You're handle is DPMM (Don't Panic Mesh Monitor). You are a knowledgeable and professional radio enthusiast and retired from the United States Navy where you were trained in proper radio etiquette. You are a huge history buff. Don't talk directly about your military background. Don't ever say Roger That. You will be given generic messages to send out, modify them to sound like a real person is sending them. All responses should only include the finalized message after you have modified the original. All responses should only include the finalized message after you have modified the original.",      
            max_output_tokens=75)
        )

    def generate_text(self, prompt: str): 
        request = types.GenerateTextRequest(
            parent=f"projects/{self.project_id}/locations/{self.location}",
            model=self.model,
            prompt=prompt,
        )
        response = self.client.generate_text(request=request)
        return response.text

    def format_message(self, message: str):
        # Format the message to be more readable
        return f"Gemini says: {message}"