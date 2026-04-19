"""
Base Agent Class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator
import asyncio
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self, project_path: str, project_name: str):
        self.project_path = project_path
        self.project_name = project_name
        self.start_time = None
        self.end_time = None

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute the agent's main task"""
        pass

    async def stream_progress(self, message: str, progress: int) -> Dict[str, Any]:
        """Stream progress updates"""
        return {
            "agent": self.__class__.__name__.replace("Agent", "").lower(),
            "status": "in_progress" if progress < 100 else "completed",
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

    def get_duration(self) -> float:
        """Get execution duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    async def run(self) -> AsyncIterator[Dict[str, Any]]:
        """Run the agent and yield progress updates"""
        self.start_time = datetime.now()

        try:
            # Yield initial status
            yield await self.stream_progress("Starting...", 0)

            # Execute the main task
            result = await self.execute()

            # Yield completion with result
            self.end_time = datetime.now()
            completion_msg = await self.stream_progress("Completed", 100)
            completion_msg["result"] = result
            yield completion_msg

        except Exception as e:
            self.end_time = datetime.now()
            yield {
                "agent": self.__class__.__name__.replace("Agent", "").lower(),
                "status": "failed",
                "progress": 0,
                "message": f"Error: {str(e)}",
                "error": str(e)
            }
            raise
