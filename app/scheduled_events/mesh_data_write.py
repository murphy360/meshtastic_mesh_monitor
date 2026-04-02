"""
Mesh Data Write scheduled task - writes mesh data to file every cycle.

Writes the current mesh node data to a JSON file that the
meshtastic_mesh_visualizer reads to display nodes on a map.
"""

from .base_scheduled_event import BaseScheduledEvent, ScheduleType


class MeshDataWriteScheduledEvent(BaseScheduledEvent):
    """Write mesh data to file every minute for the visualizer."""

    name = "Mesh Data Write"
    enabled = True
    schedule_type = ScheduleType.INTERVAL
    interval_minutes = 1

    def execute(self) -> bool:
        try:
            if not self.sitrep:
                self.logger.error("Missing sitrep dependency")
                return False

            if self.sitrep.interface is None:
                self.logger.warning("SITREP interface not set, skipping mesh data write")
                return False

            self.sitrep.write_mesh_data_to_file()
            self.logger.debug("📁 Mesh Data Write: completed")
            return True

        except Exception as e:
            self.logger.error(f"Error in mesh data write: {e}")
            return False
