# 2025-09-29: Clean code review: This file was reviewed for clean code standards.
# in accordance with standards listed in docs/generic_clean_code_review_prompt.md.
# TODO: Refactor long methods for clarity and maintainability.
# TODO: Ensure consistent logging usage and patterns.
# TODO: Review for code duplication in chat creation and message handling.
# TODO: Add error handling for all external API calls and file operations.
# TODO: Add file hygiene note if any sections are unused or misplaced.

import os
from config.config_manager import ConfigManager
from google import genai
from google.genai import types # type: ignore
from typing import Dict, Optional, Any
from core.base_interfaces import BaseInterface

class GeminiInterface(BaseInterface):
    """
    Interface for interacting with the Gemini AI API.
    Implements a singleton pattern to ensure only one instance exists.
    Manages chat objects for public, admin, and private communications.
    """
    _instance: Optional['GeminiInterface'] = None
    gemini_api_key: str
    gemini_model: str
    location: str
    max_message_length: int
    max_output_tokens: int
    gemini_client: Any
    public_chat: Any
    admin_chat: Any
    private_chats: Dict[str, Any]
    base_system_instruction: str

    def __new__(cls, *args, **kwargs) -> 'GeminiInterface':
        """
        Singleton pattern: ensures only one instance of GeminiInterface exists.
        This is used to centralize Gemini API access and chat management across the application.
        """
        if cls._instance is None:
            cls._instance = super(GeminiInterface, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls, location: str = "Unknown Location") -> 'GeminiInterface':
        """
        Returns the singleton instance of GeminiInterface, creating it if necessary.
        This method should be used to access GeminiInterface throughout the application.
        Args:
            location: The location context for the interface.
        Returns:
            GeminiInterface: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls(location=location)
        return cls._instance

    def __init__(self, location: str = "Unknown Location") -> None:
        """
        Initialize the Gemini AI interface.
        Args:
            location (str): Current location for context.
        This constructor sets up the Gemini API client and initializes chat objects for public, admin, and private channels.
        """
        super().__init__(cache_duration_seconds=0)  # No caching for AI responses
        self._logger.info(f"Initializing GeminiInterface at location: {location}")
        self.gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
        if not self.gemini_api_key:
            self._logger.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.gemini_model: str = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.location: str = location
        self.max_message_length: int = 200  # Maximum message length for transmission
        self.max_output_tokens: int = 100  # Maximum output tokens for responses
        # Load Gemini instructions/configs from external config file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "gemini_config.json")
        self.config_manager = ConfigManager(config_file_path=config_path)
        gemini_config = self.config_manager.config
        self._logger.info(f"Loaded Gemini config from {config_path}: {gemini_config}")
        self.base_system_instruction_config = gemini_config["base_system_instruction"]
        self.chat_configs = gemini_config["chat_configs"]
        self.update_base_system_instruction()
        # The Gemini client is used for all API interactions
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        # All chats (public, admin, private) are managed in a single dictionary
        self.chats = {
            "public": self._create_chat("public"),
            "admin": self._create_chat("admin")
        }

    def update_base_system_instruction(self):
        """
        Update the base system instruction with the current location and message length.
        Logs the current location and instruction.
        """
        self._logger.info(f"update_base_system_instruction called. location={self.location}")
        self.base_system_instruction = self.base_system_instruction_config.format(
            location=self.location,
            max_message_length=self.max_message_length
        )
    

    def update_location(self, new_location: str):
        """
        Update the bot's location and recreate the chat models.
        Logs the old and new location.
        """
        self._logger.info(f"update_location called. new_location={new_location}")
        if new_location == self.location:
            return
        self._logger.info(f"Updating location from {self.location} to {new_location}")
        self.location = new_location
        self.update_base_system_instruction()
        # Recreate chats with updated location
        self.chats["public"] = self._create_chat("public")
        self.chats["admin"] = self._create_chat("admin")
        # Remove all private chats (keys not 'public' or 'admin')
        self.chats = {k: v for k, v in self.chats.items() if k in ["public", "admin"]}
    
    def _create_chat(self, role: str, node_short_name: Optional[str] = None) -> Any:
        """
        Create a chat for a given role (public, admin, or private).
        Args:
            role (str): 'public', 'admin', or 'private'.
            node_short_name (str, optional): For private chats, the node short name.
        Returns:
            Chat object configured for the specified role.
        """
        if role not in self.chat_configs:
            raise ValueError(f"Unknown chat role: {role}")
        instruction = self.base_system_instruction + self.chat_configs[role]["instruction"]
        if role == "private" and node_short_name:
            instruction = instruction.format(node_short_name=node_short_name)
        self._logger.info(f"_create_chat called for role={role}, node_short_name={node_short_name}. instruction={instruction}")
        return self.gemini_client.chats.create(
            model=self.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=instruction
            )
        )
    
    def get_chat(self, role: str, node_short_name: Optional[str] = None) -> Any:
        """
        Get an existing chat or create a new one for the given role.
        Args:
            role (str): 'public', 'admin', or 'private'.
            node_short_name (str, optional): For private chats, the node short name.
        Returns:
            Chat object for the specified role.
        """
        key = role if role in ["public", "admin"] else node_short_name
        if key not in self.chats:
            self._logger.info(f"Creating new chat for role={role}, node_short_name={node_short_name}")
            if role == "private" and node_short_name:
                self.chats[node_short_name] = self._create_chat("private", node_short_name=node_short_name)
            else:
                self.chats[role] = self._create_chat(role)
        return self.chats[key]

    def summarize_pdf(self, path_to_pdf: str) -> str:
        """
        Summarize the content of a PDF document.
        Logs the file path and summary result.
        """
        self._logger.info(f"summarize_pdf called. path_to_pdf={path_to_pdf}")
        try:
            uploaded_file = self.gemini_client.files.upload(file=path_to_pdf)
            if not uploaded_file:
                self._logger.error("Failed to upload PDF file.")
                return "Error uploading PDF file."
        except Exception as e:
            self._logger.error(f"Error reading PDF file: {e}")
            return "Error reading PDF file."
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[f"Summarize this PDF File in {self.max_message_length} characters or less", uploaded_file]
            )
            self._logger.info(f"summarize_pdf returning: {response.text}")
            return response.text
        except Exception as e:
            self._logger.error(f"Error summarizing PDF: {e}")
            return "Error summarizing PDF content."
        
    
    def generate_response(self, message: str, channel_id: int, node_short_name: Optional[str] = None) -> str:
        """
        Generate a response using the appropriate chat model based on the channel and recipient.
        Logs the arguments and the response text.
        """
        self._logger.info(f"generate_response called. message={message}, channel_id={channel_id}, node_short_name={node_short_name}")
        try:
            response_text = None
            # Private message to a specific node (takes precedence over channel ID)
            if node_short_name:
                self._logger.info(f"Generating response for private chat with {node_short_name}")
                chat = self.get_chat("private", node_short_name=node_short_name)
                response = chat.send_message(message)
                response_text = response.text
            # Admin channel
            elif channel_id == 1:  # admin_channel_number
                self._logger.info("Generating response for admin channel")
                chat = self.get_chat("admin")
                response = chat.send_message(message)
                response_text = response.text
            # Public channel
            elif channel_id == 0:  # public_channel_number
                self._logger.info("Generating response for public channel")
                chat = self.get_chat("public")
                response = chat.send_message(message)
                response_text = response.text
            # For any other case, fall back to a generic content generation
            else:
                generic_instruction = self.base_system_instruction + (
                    " You are preparing a message for transmission on the mesh network."
                )
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    config=types.GenerateContentConfig(
                        system_instruction=generic_instruction
                    ),
                    contents=f"Modify this message for transmission: {message}. Return only the modified message so that I can send it directly to the recipient.",
                )
                response_text = response.candidates[0].content.parts[0].text.strip()
            if not response_text:
                self._logger.error("No response generated by the AI model.")
                return "I'm an auto-responder. I'm working on smarter replies, but it's going to be a while!"
            self._logger.info(f"generate_response returning: {response_text}")
            return response_text
        except Exception as e:
            self._logger.error(f"Error generating response: {e}")
            if "503" in str(e) or "Service Unavailable" in str(e):
                return "I'm currently unable to process your request. Please try again later."
            return f"(Error with AI response: {message})"

    def test_connection(self) -> bool:
        """
        Test if the interface can connect to the Gemini API.
        Logs the result.
        """
        self._logger.info("test_connection called.")
        try:
            # Try a simple request to test connectivity
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents="Hello"
            )
            result = response is not None
            self._logger.info(f"test_connection returning: {result}")
            return result
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Gemini interface.
        Logs the status dict returned.
        """
        self._logger.info("get_status called.")
        status = {
            "interface_type": "GeminiInterface",
            "location": self.location,
            "max_message_length": self.max_message_length,
            "max_output_tokens": self.max_output_tokens,
            "has_api_key": bool(self.gemini_api_key),
            "private_chats_count": len(self.private_chats),
            "connection_status": self.test_connection()
        }
        self._logger.info(f"get_status returning: {status}")
        return status
    
    def get_private_chats_string(self) -> str:
        """
        Get a printable string of private chat node short names with newlines in between.
        """
        private_keys = [k for k in self.chats.keys() if k not in ["public", "admin"]]
        chat_names = '\n'.join(private_keys)
        self._logger.info(f"private_chats_string returning: {chat_names}")
        return chat_names

