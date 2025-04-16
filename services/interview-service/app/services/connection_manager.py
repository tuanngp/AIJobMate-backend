from typing import Dict, List, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Dict to store connections by session_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: int):
        """
        Add a new WebSocket connection for a specific session
        """
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"New connection added to session {session_id}. Total connections: {len(self.active_connections[session_id])}")

    async def disconnect(self, websocket: WebSocket, session_id: int):
        """
        Remove a WebSocket connection for a specific session
        """
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                logger.info(f"Connection removed from session {session_id}")
                # Clean up empty session entries
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            except ValueError:
                logger.warning(f"Connection not found in session {session_id}")

    async def broadcast_to_session(self, session_id: int, message: dict):
        """
        Broadcast a message to all connections in a specific session
        """
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
            
        disconnected = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                disconnected.append(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection, session_id)

    async def close_all(self):
        """
        Close all active connections
        """
        for session_id in list(self.active_connections.keys()):
            for connection in self.active_connections[session_id]:
                try:
                    await connection.close(code=1000)
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")
        self.active_connections.clear()