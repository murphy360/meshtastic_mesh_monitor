import os
import logging
from google import genai
from google.genai import types # type: ignore
from typing import Dict, Optional

class GeminiInterface:
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            logging.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Base system instruction for all chats
        self.base_system_instruction = (
            "You are an AI named DPMM (Don't Panic Mesh Monitor). "
            "You are a knowledgeable and professional radio enthusiast with a background in the United States Navy "
            "where you were trained in proper radio etiquette. "
            "You are a huge history buff. Don't talk directly about your military background. "
            "Don't ever say 'Roger That'. "
            "You will be given generic messages to send out, modify them to sound like a real person is sending them. "
            "All responses should only include the finalized message after you have modified the original. "
            "All responses should be less than 450 characters or they will not be transmitted or received."
        )
        
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.public_chat = self._create_public_chat()
        self.admin_chat = self._create_admin_chat()
        self.private_chats: Dict[str, any] = {}  # Dictionary to store private chats
        
    def _create_public_chat(self):
        """Create a chat for public channel communications"""
        public_instruction = self.base_system_instruction + (
            " You are tasked with monitoring a meshtastic mesh network and responding on a public channel. "
            "Your messages will be visible to all nodes in the network."
        )
        
        return self.gemini_client.chats.create(
            model='gemini-2.0-flash-001',
            config=types.GenerateContentConfig(
                system_instruction=public_instruction,
                max_output_tokens=75
            )
        )
    
    def _create_admin_chat(self):
        """Create a chat for admin channel communications"""
        admin_instruction = self.base_system_instruction + (
            " You are tasked with monitoring a meshtastic mesh network and are currently working directly "
            "with administrators on a private admin channel. Be more technical and detailed in your responses "
            "to administrators, as they need accurate information."
        )
        
        return self.gemini_client.chats.create(
            model='gemini-2.0-flash-001',
            config=types.GenerateContentConfig(
                system_instruction=admin_instruction,
                max_output_tokens=75
            )
        )
    
    def get_or_create_private_chat(self, node_short_name: str):
        """Get an existing private chat or create a new one for direct communications with a node"""
        if node_short_name not in self.private_chats:
            logging.info(f"Creating new private chat with {node_short_name}")
            
            private_instruction = self.base_system_instruction + (
                f" You are currently in a private conversation with {node_short_name}. "
                f"Personalize your responses appropriately for this direct communication."
            )
            
            self.private_chats[node_short_name] = self.gemini_client.chats.create(
                model='gemini-2.0-flash-001',
                config=types.GenerateContentConfig(
                    system_instruction=private_instruction,
                    max_output_tokens=75
                )
            )
        return self.private_chats[node_short_name]
    
    def generate_response(self, message: str, channel_id: int, node_short_name: Optional[str] = None) -> str:
        """
        Generate a response using the appropriate chat model based on the channel and recipient
        
        Args:
            message: The message to process
            channel_id: The channel ID (0 for public, 1 for admin, etc.)
            node_short_name: The short name of the node for private chats
            
        Returns:
            The generated response text
        """
        try:
            response_text = None
            
            # Admin channel
            if channel_id == 1:  # admin_channel_number
                logging.info("Generating response for admin channel")
                response = self.admin_chat.send_message(message)
                response_text = response.text
            
            # Public channel
            elif channel_id == 0:  # public_channel_number
                logging.info("Generating response for public channel")
                response = self.public_chat.send_message(message)
                response_text = response.text
            
            # Private message to a specific node
            elif node_short_name:
                logging.info(f"Generating response for private chat with {node_short_name}")
                private_chat = self.get_or_create_private_chat(node_short_name)
                response = private_chat.send_message(message)
                response_text = response.text
            
            # For any other case, fall back to a generic content generation
            else:
                generic_instruction = self.base_system_instruction + (
                    " You are preparing a message for transmission on the mesh network."
                )
                
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=generic_instruction,
                        max_output_tokens=75
                    ),
                    contents=f"Modify this message for transmission: {message}. Return only the modified message so that I can send it directly to the recipient.",
                )
                response_text = response.candidates[0].content.parts[0].text.strip()
            
            if not response_text:
                logging.error("No response generated by the AI model.")
                return "I'm an auto-responder. I'm working on smarter replies, but it's going to be a while!"
                
            logging.info(f"Generated response: {response_text}")
            return response_text
            
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return f"Error generating response. Default message from DPMM."