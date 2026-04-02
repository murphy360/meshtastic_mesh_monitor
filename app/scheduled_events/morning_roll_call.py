"""
Morning Roll Call scheduled task - sends a daily greeting to the public channel at 5am ET.

Gemini composes a unique message based on an interesting fact, historical event,
holiday, or notable occurrence for today's date.
"""

from datetime import datetime, timezone

from core.constants import BROADCAST_DESTINATION

from .base_scheduled_event import BaseScheduledEvent, ScheduleType


class MorningRollCallScheduledEvent(BaseScheduledEvent):
    """Send a daily morning greeting to the public channel at 5am ET (9am UTC)."""

    # Task configuration
    name = "Morning Roll Call"
    enabled = True
    schedule_type = ScheduleType.CRON
    cron_expression = "0 9 * * *"  # 9:00 UTC = 5:00 AM ET (EDT)

    def execute(self) -> bool:
        """
        Execute the roll call.

        Returns:
            bool: True if successful, False if failed
        """
        try:
            # Example: Log the execution
            self.logger.info(f"🌅 {self.name} - Executing at {datetime.now(timezone.utc)}")

            # Example: Get node count from database
            if self.db_helper:
                node_count = self.db_helper.get_node_count()
                self.logger.info(f"   Current node count: {node_count}")

            # Send a roll call message to the mesh
            if self.message_sender and self.interfaces and self.config_manager:
                tcp_interface = self.interfaces.get("tcp_interface")
                if tcp_interface:
                    # Get current date/time for greeting
                    now_utc = datetime.now(timezone.utc)
                    day_of_week = now_utc.strftime("%A")

                    # Frame as a broadcast instruction so Gemini composes
                    # a unique morning message based on today's trivia
                    date_str = now_utc.strftime("%B %d")
                    message = (
                        f"[Broadcast Message] Compose a fun and unique morning "
                        f"greeting for the mesh network. Today is {day_of_week}, "
                        f"{date_str}. Share a lighthearted fun fact, quirky holiday, "
                        f"pop culture moment, science tidbit, or weird-but-true "
                        f"historical event for today's date. Keep it fun and "
                        f"low-stakes — avoid politics, religion, war, tragedy, "
                        f"or anything controversial. End by inviting nodes to "
                        f"check in. Keep it concise and engaging. "
                        f"Do NOT respond to this — just compose the broadcast message."
                    )

                    # Send to public channel using LLM
                    public_channel = self.config_manager.get_public_channel()
                    self.message_sender.send_llm_message(
                        tcp_interface, message, public_channel, BROADCAST_DESTINATION
                    )

                    self.logger.info("   Roll call message sent to public channel")

            return True

        except Exception as e:
            self.logger.error(f"Error in morning roll call: {e}")
            return False
