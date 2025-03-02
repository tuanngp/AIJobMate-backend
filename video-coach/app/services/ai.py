from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime
import numpy as np
import cv2
import mediapipe as mp
import face_recognition
from loguru import logger
import openai
import torch
from transformers import pipeline
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config.settings import settings
from app.schemas.video import (
    FacialExpression,
    PostureMetrics,
    GestureAnalysis,
    PerformanceMetrics
)

class AIService:
    def __init__(self):
        """Initialize AI models and processors"""
        # OpenAI setup
        openai.api_key = settings.OPENAI_API_KEY
        self.analysis_model = settings.ANALYSIS_MODEL

        # Initialize MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=settings.FACE_DETECTION_CONFIDENCE
        )
        self.mp_pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            min_detection_confidence=settings.FACE_DETECTION_CONFIDENCE
        )
        self.mp_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=settings.FACE_DETECTION_CONFIDENCE
        )

        # Initialize emotion detection
        self.emotion_detector = pipeline(
            "image-classification",
            model="joeddav/distilbert-base-uncased-emotion",
            top_k=3
        )

        # Load CLIP model if available
        if torch.cuda.is_available() and settings.USE_GPU:
            self.device = "cuda"
        else:
            self.device = "cpu"

    async def analyze_facial_expressions(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> FacialExpression:
        """Analyze facial expressions in a single frame"""
        try:
            # Convert to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return None

            # Get facial landmarks
            face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
            
            # Process with MediaPipe for detailed mesh
            results = self.mp_face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks:
                return None

            landmarks = results.multi_face_landmarks[0]

            # Calculate eye contact score
            eye_contact = self._calculate_eye_contact(landmarks)

            # Get head pose
            head_pose = self._estimate_head_pose(landmarks)

            # Detect emotions
            emotions = await self._detect_emotions(rgb_frame, face_locations[0])

            return FacialExpression(
                timestamp=timestamp,
                emotions=emotions,
                eye_contact=eye_contact,
                head_pose=head_pose
            )

        except Exception as e:
            logger.error(f"Error analyzing facial expressions: {str(e)}")
            return None

    async def analyze_posture(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> PostureMetrics:
        """Analyze body posture in a single frame"""
        try:
            # Process with MediaPipe Pose
            results = self.mp_pose.process(frame)
            
            if not results.pose_landmarks:
                return None

            landmarks = results.pose_landmarks.landmark

            # Calculate posture metrics
            alignment = self._calculate_spine_alignment(landmarks)
            stability = self._calculate_posture_stability(landmarks)
            position = self._extract_key_positions(landmarks)

            return PostureMetrics(
                timestamp=timestamp,
                alignment=alignment,
                stability=stability,
                position=position
            )

        except Exception as e:
            logger.error(f"Error analyzing posture: {str(e)}")
            return None

    async def analyze_gestures(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> GestureAnalysis:
        """Analyze hand gestures in a single frame"""
        try:
            # Process with MediaPipe Hands
            results = self.mp_hands.process(frame)
            
            if not results.multi_hand_landmarks:
                return None

            # Analyze each detected hand
            gestures = []
            for hand_landmarks in results.multi_hand_landmarks:
                gesture = self._classify_gesture(hand_landmarks)
                if gesture:
                    gestures.append(gesture)

            if not gestures:
                return None

            # Return the most confident gesture
            return max(gestures, key=lambda x: x.confidence)

        except Exception as e:
            logger.error(f"Error analyzing gestures: {str(e)}")
            return None

    def _calculate_eye_contact(self, landmarks) -> float:
        """Calculate eye contact score from facial landmarks"""
        try:
            # Extract eye landmarks
            left_eye = np.array([(p.x, p.y) for p in landmarks.landmark[33:46]])
            right_eye = np.array([(p.x, p.y) for p in landmarks.landmark[362:375]])

            # Calculate eye aspect ratio
            eye_ratio = (np.mean(left_eye[:, 1]) + np.mean(right_eye[:, 1])) / 2

            # Convert to score (0-1)
            return max(0, min(1, 1 - abs(0.5 - eye_ratio) * 4))

        except Exception as e:
            logger.error(f"Error calculating eye contact: {str(e)}")
            return 0.0

    def _estimate_head_pose(self, landmarks) -> Dict[str, float]:
        """Estimate head pose angles from facial landmarks"""
        try:
            # Extract key points for pose estimation
            nose_tip = np.array([landmarks.landmark[4].x, landmarks.landmark[4].y, landmarks.landmark[4].z])
            chin = np.array([landmarks.landmark[152].x, landmarks.landmark[152].y, landmarks.landmark[152].z])
            left_eye = np.array([landmarks.landmark[33].x, landmarks.landmark[33].y, landmarks.landmark[33].z])
            right_eye = np.array([landmarks.landmark[362].x, landmarks.landmark[362].y, landmarks.landmark[362].z])

            # Calculate angles
            forward_angle = np.arctan2(nose_tip[2], nose_tip[1])
            side_angle = np.arctan2(right_eye[0] - left_eye[0], right_eye[2] - left_eye[2])
            tilt_angle = np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])

            return {
                "forward": float(np.degrees(forward_angle)),
                "side": float(np.degrees(side_angle)),
                "tilt": float(np.degrees(tilt_angle))
            }

        except Exception as e:
            logger.error(f"Error estimating head pose: {str(e)}")
            return {"forward": 0.0, "side": 0.0, "tilt": 0.0}

    async def _detect_emotions(
        self,
        frame: np.ndarray,
        face_location: Tuple[int, int, int, int]
    ) -> Dict[str, float]:
        """Detect emotions in facial image"""
        try:
            # Extract face region
            top, right, bottom, left = face_location
            face_image = frame[top:bottom, left:right]
            
            # Resize for emotion detector
            face_image = cv2.resize(face_image, (224, 224))
            
            # Get predictions
            predictions = self.emotion_detector(face_image)
            
            # Convert to dictionary
            emotions = {pred['label']: float(pred['score']) for pred in predictions}
            
            return emotions

        except Exception as e:
            logger.error(f"Error detecting emotions: {str(e)}")
            return {}

    def _calculate_spine_alignment(self, landmarks) -> float:
        """Calculate spine alignment score"""
        try:
            # Get key spine landmarks
            shoulders = np.array([
                [landmarks[11].x, landmarks[11].y],  # Left shoulder
                [landmarks[12].x, landmarks[12].y]   # Right shoulder
            ])
            hips = np.array([
                [landmarks[23].x, landmarks[23].y],  # Left hip
                [landmarks[24].x, landmarks[24].y]   # Right hip
            ])

            # Calculate alignment angles
            shoulder_angle = np.arctan2(
                shoulders[1][1] - shoulders[0][1],
                shoulders[1][0] - shoulders[0][0]
            )
            hip_angle = np.arctan2(
                hips[1][1] - hips[0][1],
                hips[1][0] - hips[0][0]
            )

            # Convert angle difference to alignment score (0-1)
            angle_diff = abs(np.degrees(shoulder_angle - hip_angle))
            return max(0, min(1, 1 - angle_diff / 45))

        except Exception as e:
            logger.error(f"Error calculating spine alignment: {str(e)}")
            return 0.0

    def _calculate_posture_stability(self, landmarks) -> float:
        """Calculate posture stability score"""
        try:
            # Get key landmarks for stability
            keypoints = [
                landmarks[11],  # Left shoulder
                landmarks[12],  # Right shoulder
                landmarks[23],  # Left hip
                landmarks[24],  # Right hip
                landmarks[25],  # Left knee
                landmarks[26]   # Right knee
            ]

            # Calculate standard deviation of movements
            positions = np.array([[p.x, p.y] for p in keypoints])
            stability = 1 - min(1, np.std(positions) * 10)

            return float(stability)

        except Exception as e:
            logger.error(f"Error calculating posture stability: {str(e)}")
            return 0.0

    def _extract_key_positions(self, landmarks) -> Dict[str, List[float]]:
        """Extract key body positions"""
        try:
            return {
                "shoulders": [
                    [landmarks[11].x, landmarks[11].y, landmarks[11].z],
                    [landmarks[12].x, landmarks[12].y, landmarks[12].z]
                ],
                "hips": [
                    [landmarks[23].x, landmarks[23].y, landmarks[23].z],
                    [landmarks[24].x, landmarks[24].y, landmarks[24].z]
                ],
                "head": [
                    landmarks[0].x,
                    landmarks[0].y,
                    landmarks[0].z
                ]
            }
        except Exception as e:
            logger.error(f"Error extracting key positions: {str(e)}")
            return {}

    def _classify_gesture(self, hand_landmarks) -> Optional[GestureAnalysis]:
        """Classify hand gesture from landmarks"""
        try:
            # Convert landmarks to numpy array
            points = np.array([[l.x, l.y, l.z] for l in hand_landmarks.landmark])
            
            # Calculate basic gesture features
            palm_direction = points[0] - np.mean(points[5:9], axis=0)
            finger_angles = self._calculate_finger_angles(points)
            
            # Classify gesture based on features
            gesture_type, confidence = self._identify_gesture(palm_direction, finger_angles)
            
            if gesture_type:
                return GestureAnalysis(
                    timestamp=datetime.utcnow().timestamp(),
                    gesture_type=gesture_type,
                    confidence=confidence,
                    description=self._get_gesture_description(gesture_type)
                )
            return None

        except Exception as e:
            logger.error(f"Error classifying gesture: {str(e)}")
            return None

    def _calculate_finger_angles(self, points) -> List[float]:
        """Calculate angles between finger joints"""
        try:
            angles = []
            # For each finger
            for finger in range(5):
                base = 4 * finger + 5
                # Calculate angle between joints
                v1 = points[base + 1] - points[base]
                v2 = points[base + 2] - points[base + 1]
                angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
                angles.append(float(angle))
            return angles
        except Exception as e:
            logger.error(f"Error calculating finger angles: {str(e)}")
            return [0.0] * 5

    def _identify_gesture(
        self,
        palm_direction: np.ndarray,
        finger_angles: List[float]
    ) -> Tuple[Optional[str], float]:
        """Identify gesture type and confidence"""
        try:
            # Simple gesture classification based on finger angles
            extended_fingers = [angle < 1.0 for angle in finger_angles]
            
            if all(extended_fingers):
                return "open_palm", 0.9
            elif not any(extended_fingers):
                return "closed_fist", 0.9
            elif extended_fingers[1] and not any(extended_fingers[2:]):
                return "pointing", 0.8
            elif extended_fingers[0] and extended_fingers[1]:
                return "peace_sign", 0.8
            else:
                return "other", 0.5
                
        except Exception as e:
            logger.error(f"Error identifying gesture: {str(e)}")
            return None, 0.0

    def _get_gesture_description(self, gesture_type: str) -> str:
        """Get human-readable description of gesture"""
        descriptions = {
            "open_palm": "Open palm gesture, indicating openness or emphasis",
            "closed_fist": "Closed fist, may indicate tension or emphasis",
            "pointing": "Pointing gesture, directing attention",
            "peace_sign": "Peace sign or victory gesture",
            "other": "Unclassified hand gesture"
        }
        return descriptions.get(gesture_type, "Unknown gesture")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.OpenAIError)
    )
    async def generate_feedback(
        self,
        facial_expressions: List[FacialExpression],
        posture_metrics: List[PostureMetrics],
        gestures: List[GestureAnalysis],
        performance_metrics: PerformanceMetrics
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate comprehensive feedback and recommendations"""
        try:
            # Prepare analysis summary
            analysis = {
                "facial_expressions": [expr.model_dump() for expr in facial_expressions],
                "posture_metrics": [metric.model_dump() for metric in posture_metrics],
                "gestures": [gesture.model_dump() for gesture in gestures],
                "performance_metrics": performance_metrics.model_dump()
            }

            response = await openai.chat.completions.create(
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": """
                    Analyze interview performance based on:
                    1. Facial expressions and emotions
                    2. Body language and posture
                    3. Hand gestures and movement
                    4. Overall engagement and professionalism
                    
                    Provide constructive feedback and actionable recommendations.
                    """},
                    {"role": "user", "content": str(analysis)}
                ],
                temperature=0.5,
                response_format={ "type": "json_object" }
            )
            
            feedback = response.choices[0].message.content
            
            return (
                feedback.get("overall_feedback", ""),
                feedback.get("recommendations", []),
                feedback.get("practice_suggestions", {})
            )

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            raise
