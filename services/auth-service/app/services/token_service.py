from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.token import RefreshTokenDB, RevokedTokenDB
from app.core.security import verify_token

class TokenService:
    @staticmethod
    async def store_refresh_token(db: Session, token: str, user_id: int) -> bool:
        """Store refresh token in database."""
        try:
            payload = verify_token(token, "refresh")
            refresh_token = RefreshTokenDB(
                token=token,
                user_id=user_id,
                expires_at=datetime.fromtimestamp(payload.exp)
            )
            db.add(refresh_token)
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    async def verify_refresh_token(db: Session, token: str, user_id: int) -> bool:
        """Verify if refresh token exists and is valid."""
        try:
            # Check if token is revoked
            revoked = db.query(RevokedTokenDB).filter(
                RevokedTokenDB.jti == token
            ).first()
            if revoked:
                return False

            # Check if token exists and belongs to user
            stored_token = db.query(RefreshTokenDB).filter(
                RefreshTokenDB.token == token,
                RefreshTokenDB.user_id == user_id
            ).first()
            
            if not stored_token:
                return False

            # Check if token has expired
            if stored_token.expires_at < datetime.utcnow():
                await TokenService.revoke_refresh_token(
                    db, token, user_id, "Token expired"
                )
                return False

            return True
        except Exception:
            return False

    @staticmethod
    async def revoke_refresh_token(
        db: Session, 
        token: str, 
        user_id: int, 
        reason: str = "Logout"
    ) -> bool:
        """Revoke a refresh token."""
        try:
            # Remove token from active refresh tokens
            db.query(RefreshTokenDB).filter(
                RefreshTokenDB.token == token,
                RefreshTokenDB.user_id == user_id
            ).delete()

            # Add token to revoked tokens
            revoked_token = RevokedTokenDB(
                jti=token,
                user_id=user_id,
                expires_at=datetime.utcnow(),
                reason=reason
            )
            
            db.add(revoked_token)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    @staticmethod
    async def revoke_all_user_tokens(
        db: Session, 
        user_id: int, 
        reason: str = "Security measure"
    ) -> bool:
        """Revoke all refresh tokens for a user."""
        try:
            # Get all active refresh tokens for user
            tokens = db.query(RefreshTokenDB).filter(
                RefreshTokenDB.user_id == user_id
            ).all()
            
            for token in tokens:
                await TokenService.revoke_refresh_token(
                    db,
                    token.token,
                    user_id,
                    reason
                )
            
            return True
        except Exception:
            return False

    @staticmethod
    async def cleanup_expired_tokens(db: Session) -> bool:
        """Remove expired tokens from database."""
        try:
            current_time = datetime.utcnow()
            
            # Remove expired refresh tokens
            db.query(RefreshTokenDB).filter(
                RefreshTokenDB.expires_at < current_time
            ).delete()
            
            # Remove expired revoked tokens (older than 30 days)
            thirty_days_ago = current_time.replace(day=current_time.day - 30)
            db.query(RevokedTokenDB).filter(
                RevokedTokenDB.revoked_at < thirty_days_ago
            ).delete()
            
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False