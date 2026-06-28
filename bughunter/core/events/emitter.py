import uuid
from typing import Dict, Any, Optional
from bughunter.models.event import BugHunterEvent, EventType
from bughunter.core.events.bus import AsyncEventBus

class AgentEventEmitter:
    def __init__(self, agent_name: str, event_bus: AsyncEventBus):
        self.agent_name = agent_name
        self.event_bus = event_bus

    async def emit(self, run_id: str, event_type: EventType, message: str, metadata: Optional[Dict[str, Any]] = None):
        event = BugHunterEvent(
            id=str(uuid.uuid4()),
            run_id=run_id,
            type=event_type,
            agent=self.agent_name,
            message=message,
            metadata=metadata or {}
        )
        await self.event_bus.publish(event)
