import os
import logging
from google import genai
from google.genai import types # type: ignore
from typing import Dict, Optional

class GeminiInterface:
    def __init__(self, location: str = "Unknown Location"):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            logging.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.location = location
        self.max_message_length = 350  # Maximum message length for transmission
        self.max_output_tokens = 70  # Maximum output tokens for responses
        self.update_base_system_instruction()
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.public_chat = self._create_public_chat()
        self.admin_chat = self._create_admin_chat()
        self.private_chats: Dict[str, any] = {}  # Dictionary to store private chats


    def update_base_system_instruction(self):
        """Update the base system instruction with the current location"""
        self.base_system_instruction = (
            "You are an AI named DPMM (Don't Panic Mesh Monitor). "
            "You are a knowledgeable and professional radio enthusiast with a background in the United States Navy "
            "where you were trained in proper radio etiquette. You were an Eagle Scout."
            f"You are currently located in {self.location}. "
            "Don't talk directly about your military background or time in Scouting. "
            "Don't ever say 'Roger That'. "
            "You will be given messages to transmit on a mesh network. Send them as if they were from you."
            "All responses must only include the finalized message, ready for broadcast. "
            "Don't create links or URLs that weren't already provided to you in the message. "
            f"All responses must be less than {self.max_message_length} characters or they will not be transmitted or received."
        )
    

    def update_location(self, new_location: str):
        """Update the bot's location and recreate the chat models"""
        if new_location == self.location:
            return
            
        logging.info(f"Updating location from {self.location} to {new_location}")
        self.location = new_location
        
        self.update_base_system_instruction()
        
        # Recreate chats with updated location
        self.public_chat = self._create_public_chat()
        self.admin_chat = self._create_admin_chat()
        self.private_chats = {}  # Clear private chats so they'll be recreated with new location
    
    def _create_public_chat(self):
        """Create a chat for public channel communications"""
        public_instruction = self.base_system_instruction + (
            "You are tasked with monitoring a meshtastic mesh network and responding on a public channel. "
            "Your messages will be visible to all nodes in the network."
            "Do NOT respond as if you are talking to me. ONLY provide the rephrased message. "
            "Do not label responses with 'Public Channel' or similar tags."
        )
        
        return self.gemini_client.chats.create(
            model='gemini-2.5-flash-lite-preview-06-17',
            config=types.GenerateContentConfig(
                system_instruction=public_instruction,
                max_output_tokens=self.max_output_tokens
            )
        )
    
    def _create_admin_chat(self):
        """Create a chat for admin channel communications"""
        admin_instruction = self.base_system_instruction + (
            "You are tasked with monitoring a meshtastic mesh network and are currently working directly "
            "with administrators on a private admin channel. Be more technical and detailed in your responses "
            "to administrators, as they need accurate information. "
            "Do NOT respond as if you are talking to me. ONLY provide the rephrased message. "
            "Do not label responses with 'Admin Channel' or similar tags."
        )
        
        return self.gemini_client.chats.create(
            model='gemini-2.5-flash-lite-preview-06-17',
            config=types.GenerateContentConfig(
                system_instruction=admin_instruction,
                max_output_tokens=self.max_output_tokens
            )
        )
    
    def get_or_create_private_chat(self, node_short_name: str):
        """Get an existing private chat or create a new one for direct communications with a node"""
        if node_short_name not in self.private_chats:
            logging.info(f"Creating new private chat with {node_short_name}")
            
            private_instruction = self.base_system_instruction + (
                f"You are currently in a private encrypted conversation with {node_short_name}. "
                f"While this is a conversation with a specific node, you may still be asked to forward messages "
                f"If [Forward Message] is included in the message you should treat it as a request to initiate a conversation with {node_short_name} not a reply. You may modify this message slightly to make it more suitable for the recipient. "
                f"You may be slightly more casual in your responses, but still maintain professionalism. "
                "Do not label responses with 'Private Chat' or similar tags."
            )
            
            self.private_chats[node_short_name] = self.gemini_client.chats.create(
                model='gemini-2.5-flash-lite-preview-06-17',
                config=types.GenerateContentConfig(
                    system_instruction=private_instruction,
                    max_output_tokens=self.max_output_tokens
                )
            )
        return self.private_chats[node_short_name]

    def summarize_pdf(self, path_to_pdf: str) -> str:
        """
        Summarize the content of a PDF document
        
        Args:
            path_to_pdf: The file path to the PDF document

        Returns:
            A summary of the PDF content
        """
        try:
            uploaded_file = self.gemini_client.files.upload(file=path_to_pdf)

            if not uploaded_file:
                logging.error("Failed to upload PDF file.")
                return "Error uploading PDF file."

        except Exception as e:
            logging.error(f"Error reading PDF file: {e}")
            return "Error reading PDF file."

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite-preview-06-17",
                config=types.GenerateContentConfig(
                    system_instruction="You are an AI tasked with summarizing PDF documents in {self.max_message_length} characters or less. Provide a concise summary of the document's content.",
                    max_output_tokens=self.max_output_tokens
                ),
                contents=f"Summarize this PDF File in {self.max_message_length} characters or less: {uploaded_file}"
            )
            logging.info(f"Response: {response}")
            return response.text

        except Exception as e:
            logging.error(f"Error summarizing PDF: {e}")
            return "Error summarizing PDF content."
        
    
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
            
            # Private message to a specific node (takes precedence over channel ID)
            if node_short_name:
                logging.info(f"Generating response for private chat with {node_short_name}")
                private_chat = self.get_or_create_private_chat(node_short_name)
                response = private_chat.send_message(message)
                response_text = response.text
            
            # Admin channel
            elif channel_id == 1:  # admin_channel_number
                logging.info("Generating response for admin channel")
                response = self.admin_chat.send_message(message)
                response_text = response.text
            
            # Public channel
            elif channel_id == 0:  # public_channel_number
                logging.info("Generating response for public channel")
                response = self.public_chat.send_message(message)
                response_text = response.text
            
            # For any other case, fall back to a generic content generation
            else:
                generic_instruction = self.base_system_instruction + (
                    " You are preparing a message for transmission on the mesh network."
                )
                
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite-preview-06-17",
                    config=types.GenerateContentConfig(
                        system_instruction=generic_instruction,
                        max_output_tokens=self.max_output_tokens
                    ),
                    contents=f"Modify this message for transmission: {message}. Return only the modified message so that I can send it directly to the recipient.",
                )
                response_text = response.candidates[0].content.parts[0].text.strip()
            
            if not response_text:
                logging.error("No response generated by the AI model.")
                return "I'm an auto-responder. I'm working on smarter replies, but it's going to be a while!"
                
            logging.info(f"Generated response: {response_text}")
            return response_text
        
        # Handle 503 Service Unavailable errors
        except genai.exceptions.ServiceUnavailable as e:
            logging.error(f"Service Unavailable: {e}")
            return "I'm currently unable to process your request. Please try again later."
            
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return f"(Error with AI response: {message})"