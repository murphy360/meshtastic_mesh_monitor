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
    short_name: str
    long_name: str
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
    def get_instance(cls, location: str = "Unknown Location", short_name: str = "MM", long_name: str = "Mesh Monitor") -> 'GeminiInterface':
        """
        Returns the singleton instance of GeminiInterface, creating it if necessary.
        This method should be used to access GeminiInterface throughout the application.
        Args:
            location: The location context for the interface.
            short_name: The short name for the AI (callsign).
            long_name: The long name/description for the AI.
        Returns:
            GeminiInterface: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls(location=location, short_name=short_name, long_name=long_name)
        return cls._instance

    def __init__(self, location: str = "Unknown Location", short_name: str = "MM", long_name: str = "Mesh Monitor") -> None:
        """
        Initialize the Gemini AI interface.
        Args:
            location (str): Current location for context.
            short_name (str): Short name/callsign for the AI.
            long_name (str): Long name/description for the AI.
        This constructor sets up the Gemini API client and initializes chat objects for public, admin, and private channels.
        """
        super().__init__(cache_duration_seconds=0)  # No caching for AI responses
        self.logger.info(f"Initializing GeminiInterface at location: {location}, AI: {short_name} ({long_name})")
        self.gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
        if not self.gemini_api_key:
            self.logger.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.gemini_model: str = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.location: str = location
        self.short_name: str = short_name
        self.long_name: str = long_name
        self.max_message_length: int = 200  # Maximum message length for transmission
        self.max_output_tokens: int = 100  # Maximum output tokens for responses
        # Load Gemini instructions/configs from external config file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "gemini_config.json")
        self.config_manager = ConfigManager(config_file_path=config_path)
        gemini_config = self.config_manager.config
        self.logger.info(f"Loaded Gemini config from {config_path}: {gemini_config}")
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
        self.summarize_and_cleanup_chat_histories()

    def update_base_system_instruction(self):
        """
        Update the base system instruction with the current location, AI names, and message length.
        Logs the current location, names, and instruction.
        """
        self.logger.info(f"update_base_system_instruction called. location={self.location}, short_name={self.short_name}, long_name={self.long_name}")
        self.base_system_instruction = self.base_system_instruction_config.format(
            short_name=self.short_name,
            long_name=self.long_name,
            location=self.location,
            max_message_length=self.max_message_length
        )
        self.logger.info(f"Base system instruction updated: {self.base_system_instruction}")
    

    def update_location(self, new_location: str):
        """
        Update the bot's location and recreate the chat models.
        Logs the old and new location.
        """
        self.logger.info(f"update_location called. new_location={new_location}")
        if new_location == self.location:
            return
        self.logger.info(f"Updating location from {self.location} to {new_location}")
        self.location = new_location
        self.update_base_system_instruction()
        # Recreate chats with updated location
        self.chats = {}
        self.chats["public"] = self._create_chat("public")
        self.chats["admin"] = self._create_chat("admin")
    
    def update_ai_names(self, short_name: str, long_name: str):
        """
        Update the AI's short and long names and recreate the chat models.
        Logs the old and new names.
        """
        self.logger.info(f"update_ai_names called. short_name={short_name}, long_name={long_name}")
        if short_name == self.short_name and long_name == self.long_name:
            return
        self.logger.info(f"Updating AI names from {self.short_name} ({self.long_name}) to {short_name} ({long_name})")
        self.short_name = short_name
        self.long_name = long_name
        self.update_base_system_instruction()
        # Recreate chats with updated names
        self.chats = {}
        self.chats["public"] = self._create_chat("public")
        self.chats["admin"] = self._create_chat("admin")
        
    
    def _create_chat(self, key: str) -> Any:
        """
        Create a chat for a given key (public, admin, or private).
        Args:
            key (str): 'public', 'admin', or node_short_name for private chats.
        Returns:
            Chat object configured for the specified key.
        """
        if key in ["public", "admin"]:
            instruction = self.base_system_instruction + self.chat_configs[key]["instruction"]
        else:
            # Private chat: use "private" config and format with node_short_name
            instruction = self.base_system_instruction + self.chat_configs["private"]["instruction"]
            instruction = instruction.format(node_short_name=key)

        instruction = instruction + self.read_chat_from_file(key)
        
        self.logger.info(f"_create_chat called for key={key}. instruction={instruction}")
        chat = self.gemini_client.chats.create(
            model=self.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction=instruction
            )
        )

        self.logger.info(f"_create_chat created chat: {chat}")
        return chat
        
    
    def get_chat(self, key: str) -> Any:
        """
        Get an existing chat or create a new one for the given key.
        Args:
            key (str): 'public', 'admin', or node_short_name for private chats.
        Returns:
            Chat object for the specified key.
        """
        if key not in self.chats:
            self.logger.info(f"Creating new chat for key={key}")
            self.chats[key] = self._create_chat(key)
        return self.chats[key]

    def summarize_pdf(self, path_to_pdf: str) -> str:
        """
        Summarize the content of a PDF document.
        Logs the file path and summary result.
        """
        self.logger.info(f"summarize_pdf called. path_to_pdf={path_to_pdf}")
        try:
            uploaded_file = self.gemini_client.files.upload(file=path_to_pdf)
            if not uploaded_file:
                self.logger.error("Failed to upload PDF file.")
                return "Error uploading PDF file."
        except Exception as e:
            self.logger.error(f"Error reading PDF file: {e}")
            return "Error reading PDF file."
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[f"Summarize this PDF File in {self.max_message_length} characters or less", uploaded_file]
            )
            self.logger.info(f"summarize_pdf returning: {response.text}")
            return response.text
        except Exception as e:
            self.logger.error(f"Error summarizing PDF: {e}")
            return "Error summarizing PDF content."
        
    
    def generate_response(self, message: str, channel_id: int, node_short_name: Optional[str] = None) -> str:
        """
        Generate a response using the appropriate chat model based on the channel and recipient.
        Logs the arguments and the response text.
        """
        self.logger.info(f"generate_response called. message={message}, channel_id={channel_id}, node_short_name={node_short_name}")
        try:
            response_text = None
            key = node_short_name if node_short_name else ("admin" if channel_id == 1 else "public")
            self.logger.info(f"Generate response using chat key={key}")
            chat = self.get_chat(key)
            response = chat.send_message(message)
            response_text = response.text
            self.logger.info(f"generate_response returning: {response_text}")
            self.write_chat_to_file(key, f"logs/{key}_chat_history.txt")
            return response_text
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return message
        
    def summarize_error_log(self, text: str) -> str:
        """
        Summarize an error log text string using the Gemini API.
        Model is instructed to return no more than max_message_length
        Logs the input text and summary result.
        """        
        self.logger.info(f"summarize_error_log called. text={text}")
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=f"Summarize this error log in {self.max_message_length} characters or less: {text}."
            )
            self.logger.info(f"summarize_error_log returning: {response.text}")
            return response.text
        except Exception as e:
            self.logger.error(f"Error summarizing error log: {e}")
            return "Error summarizing error log."
        
    def summarize_text(self, text: str) -> str:
        """
        Summarize a given text string using the Gemini API.
        Logs the input text and summary result.
        """
        self.logger.info(f"summarize_text called. text={text}")
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=f"Summarize this text Provide key points that will be useful to know in future chats: {text}"
            )
            self.logger.info(f"summarize_text returning: {response.text}")
            return response.text
        except Exception as e:
            self.logger.error(f"Error summarizing text: {e}")
            return "Error summarizing text."
        
    def summarize_and_cleanup_chat_histories(self) -> None:
        """
        On initialization, summarize all _chat_history.txt files by combining them with any existing _chat_summary.txt files,
        run through summarize_text(), write to _chat_summary.txt, and delete _chat_history.txt files.
        """
        self.logger.info("summarize_and_cleanup_chat_histories called.")
        directory = "logs"
        if not os.path.exists(directory):
            self.logger.info(f"Directory does not exist: {directory}")
            return
        for filename in os.listdir(directory):
            if filename.endswith("_chat_history.txt"):
                key = filename.replace("_chat_history.txt", "")
                self.logger.info(f"Summarizing and cleaning up chat history for key={key}")
                chat_history = self.read_chat_history_from_file(key)
                chat_summary = self.read_chat_summary_from_file(key)
                # Combine summary and history
                if chat_summary and chat_summary != "No Chat Summary":
                    text_to_summarize = chat_summary + "\n" + chat_history
                else:
                    text_to_summarize = chat_history
                # Summarize and write to summary file with context-preserving prompt
                context_prompt = (
                    "Summarize this chat history to preserve all information that could be important for future conversations. "
                    "Focus on retaining names, dates/times, events, pets, people, and any other details that might be relevant for context or continuity. "
                    "Do not discard information unless it is clearly trivial or repetitive. "
                    "The summary should be concise but comprehensive enough to allow a new chat to be recreated with meaningful historical context, even if the specific importance of some details is not yet known.\n"
                )
                summarize_input = context_prompt + text_to_summarize
                summarized_text = self.summarize_text(summarize_input)
                self.write_chat_summary_to_file(key, summarized_text)
                self.logger.info(f"Chat history for key={key} summarized and written to summary.")
                # Delete chat history file
                chat_history_path = os.path.join(directory, f"{key}_chat_history.txt")
                try:
                    if os.path.exists(chat_history_path):
                        os.remove(chat_history_path)
                        self.logger.info(f"Deleted chat history file: {chat_history_path}")
                except Exception as e:
                    self.logger.error(f"Error deleting chat history file {chat_history_path}: {e}")

    def read_chat_summary_from_file(self, key: str) -> str:
        """
        Read Chat Summary from a file if it exists and return lines as a single string.
        that we will feed into a new chat.
        Returns "" if file does not exist or error occurs
        """
        file_path = f"logs/{key}_chat_summary.txt"
        self.logger.info(f"read_chat_summary_from_file called. key={key}, file_path={file_path}")
        if not os.path.exists(file_path):
            self.logger.info(f"File does not exist: {file_path}")
            return "No Chat Summary"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            message_string = ' '.join(lines).strip()
            return message_string
        except Exception as e:
            self.logger.error(f"Error reading chat summary from file: {e}")
            return "No Chat Summary"

    def read_chat_history_from_file(self, key: str) -> str:
        """
        Read Chat History from a file if it exists and return lines as a single string.
        that we will feed into a new chat.
        Returns "" if file does not exist or error occurs
        """
        file_path = f"logs/{key}_chat_history.txt"
        self.logger.info(f"read_chat_history_from_file called. file_path={file_path}")
        if not os.path.exists(file_path):
            self.logger.info(f"File does not exist: {file_path}")
            return "New Chat"
        try:
            message_string = ""
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                message_string = ' '.join(lines).strip()
            return message_string
        except Exception as e:
            self.logger.error(f"Error reading chat history from file: {e}")
            return "New Chat"

    def read_chat_from_file(self, key: str) -> str:
        """
        Read Chat History from a file if it exists and return lines as a single string.
        that we will feed into a new chat.
        Returns "" if file does not exist or error occurs
        """
        chat_history_file_path = f"logs/{key}_chat_history.txt"
        chat_summary_file_path = f"logs/{key}_chat_summary.txt"
        chat_history = "Chat History: " + self.read_chat_history_from_file(key)
        chat_summary = "Chat Summary: " + self.read_chat_summary_from_file(key)
        
        return chat_summary + "\n" + chat_history
        

    def write_chat_summary_to_file(self, key: str, summary: str) -> bool:
        """
        Write a summary of the chat history for a given key to a file.
        Logs the file path and success status.
        """
        file_path = f"logs/{key}_chat_summary.txt"
        self.logger.info(f"write_chat_summary_to_file called. key={key}, file_path={file_path}")
        try:
            # Delete existing file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Deleted existing file: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary + "\n")

        
            self.logger.info(f"Chat summary for key={key} written to {file_path}")
          
            return True
        except Exception as e:
            self.logger.error(f"Error writing chat summary to file: {e}")
            return False

    def write_chat_to_file(self, key: str, file_path: str) -> bool:
        """
        Write the chat history for a given key to a file.
        Logs the file path and success status.
        """
        self.logger.info(f"write_chat_to_file called. key={key}, file_path={file_path}")
        if key not in self.chats:
            self.logger.error(f"No chat found for key={key}")
            return False
        try:
            chat = self.chats[key]
            # Delete existing file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"Deleted existing file: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                for message in chat.get_history():
                    role = message.role
                    text = message.parts[0].text if hasattr(message, 'parts') and message.parts else ''
                    f.write(f"{role}: {text}\n")
            self.logger.info(f"Chat history for key={key} written to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error writing chat history to file: {e}")
            return False
        
    def test_connection(self) -> bool:
        """
        Test if the interface can connect to the Gemini API.
        Logs the result.
        """
        self.logger.info("test_connection called.")
        try:
            # Try a simple request to test connectivity
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents="Hello"
            )
            result = response is not None
            self.logger.info(f"test_connection returning: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Gemini interface.
        Logs the status dict returned.
        """
        self.logger.info("get_status called.")
        private_keys = [k for k in self.chats.keys() if k not in ["public", "admin"]]
        status = {
            "interface_type": "GeminiInterface",
            "location": self.location,
            "max_message_length": self.max_message_length,
            "max_output_tokens": self.max_output_tokens,
            "has_api_key": bool(self.gemini_api_key),
            "private_chats_count": len(private_keys),
            "connection_status": self.test_connection()
        }
        self.logger.info(f"get_status returning: {status}")
        return status
    
    def get_private_chats_string(self) -> str:
        """
        Get a printable string of private chat node short names with newlines in between.
        """
        private_keys = [k for k in self.chats.keys() if k not in ["public", "admin"]]
        chat_names = '\n'.join(private_keys)
        self.logger.info(f"private_chats_string returning: {chat_names}")
        return chat_names
    
    def get_chats_string(self) -> str:
        """
        Get a printable string of all chat names (public, admin, private) with newlines in between.
        """
        chat_names = ', '.join(self.chats.keys())
        self.logger.info(f"chats_string returning: {chat_names}")
        return chat_names