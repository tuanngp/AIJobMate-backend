# AIJobMate Development Guide

## 🚀 System Architecture Overview

### Current Components
- Interview Service (Backend)
- Database Models
- OpenAI Integration
- Redis Caching
- User Authentication

### Needed Components
- Speech-to-Text Service
- Real-time Communication
- Frontend Interface
- Analytics Service

## 📝 Enhancement Guide for Existing Components

### 1. Interview Service Improvements

#### Add Speech Processing Support
```python
# filepath: services/interview-service/app/services/speech_service.py
from fastapi import UploadFile
import whisper

class SpeechService:
    def __init__(self):
        self.model = whisper.load_model("base")
    
    async def transcribe_audio(self, audio_file: UploadFile) -> str:
        # Save temporary file
        temp_path = f"temp/{audio_file.filename}"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Transcribe
        result = self.model.transcribe(temp_path)
        return result["text"]
```

#### Add WebSocket Support for Real-time Communication
```python
# filepath: services/interview-service/app/api/websocket.py
from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

## 🆕 New Components Implementation Guide

### 1. Speech-to-Text Service (Tuấn)

#### Requirements
- Support both file upload and real-time audio streaming
- Handle multiple languages (Vietnamese & English)
- Error handling for poor audio quality
- Integration with existing interview flow

#### Recommended Technologies
- Whisper API for accuracy
- WebRTC for real-time audio capture
- Socket.io for streaming

#### Example Implementation Structure
```text
speech-service/
├── src/
│   ├── controllers/
│   │   └── speech_controller.py
│   ├── services/
│   │   ├── whisper_service.py
│   │   └── stream_service.py
│   └── utils/
│       └── audio_processing.py
└── tests/
```

### 2. User Interaction & Session Management (Huy)

#### Database Enhancements
```sql
-- Add to PostgreSQL Schema
CREATE TABLE practice_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    interview_id INTEGER REFERENCES interviews(id),
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    total_questions INTEGER,
    completed_questions INTEGER,
    average_score DECIMAL(4,2)
);

CREATE TABLE answer_recordings (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES practice_sessions(id),
    question_id INTEGER REFERENCES interview_questions(id),
    audio_url TEXT,
    transcription TEXT,
    feedback JSON,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. AI System Enhancements (Linh)

#### Improve Question Generation
- Add industry-specific templates
- Support multiple difficulty levels
- Include behavioral and technical questions
- Add scoring rubrics

#### Sample Configuration
```yaml
question_types:
  technical:
    categories:
      - programming
      - system_design
      - algorithms
      - databases
  behavioral:
    categories:
      - leadership
      - teamwork
      - conflict_resolution
      - problem_solving
```

### 4. System Prompts Development (Điệp)

#### Create Domain-Specific Prompt Templates
```json
{
  "tech_interview": {
    "system_prompt": "You are a senior technical interviewer...",
    "evaluation_criteria": {
      "technical_accuracy": 0.4,
      "communication": 0.3,
      "problem_solving": 0.3
    }
  },
  "business_interview": {
    "system_prompt": "You are an experienced business consultant...",
    "evaluation_criteria": {
      "strategic_thinking": 0.35,
      "leadership": 0.35,
      "communication": 0.3
    }
  }
}
```

## 📊 Monitoring & Analytics

### Add Prometheus Metrics
```python
from prometheus_client import Counter, Histogram

interview_requests = Counter(
    'interview_requests_total',
    'Total number of interview requests'
)

response_time = Histogram(
    'response_time_seconds',
    'Response time in seconds'
)
```

## 🔄 Next Steps

1. **Speech Service Implementation**
   - Set up basic audio processing
   - Implement real-time streaming
   - Add error handling

2. **Frontend Development**
   - Create user interface
   - Implement WebSocket connections
   - Add audio recording capabilities

3. **Testing & Integration**
   - Unit tests for new components
   - Integration tests for full flow
   - Load testing for WebSocket connections

4. **Documentation**
   - API documentation
   - User guides
   - Deployment instructions