from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

class UserService:
    @staticmethod
    async def get_user(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    async def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    async def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    async def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users."""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    async def create_user(db: Session, user_in: UserCreate) -> User:
        """Create new user."""
        # Check if roles exist, create if not
        roles = []
        for role_name in user_in.roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name)
                db.add(role)
                db.commit()
            roles.append(role)

        # Create user
        db_user = User(
            email=user_in.email,
            username=user_in.username,
            full_name=user_in.full_name,
            hashed_password=get_password_hash(user_in.password),
            roles=roles
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    async def update_user(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """Update user information."""
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return None

        update_data = user_in.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    async def delete_user(db: Session, user_id: int) -> Optional[User]:
        """Delete user."""
        db_user = await UserService.get_user(db, user_id)
        if db_user:
            db.delete(db_user)
            db.commit()
        return db_user

    @staticmethod
    async def authenticate(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user."""
        user = db.query(User).filter(
            or_(User.email == username, User.username == username)
        ).first()
        
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def is_admin(user: User) -> bool:
        """Check if user is admin."""
        return any(role.name == "admin" for role in user.roles)

    @staticmethod
    async def add_role(db: Session, user_id: int, role_name: str) -> Optional[User]:
        """Add role to user."""
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return None

        # Check if role exists
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name)
            db.add(role)
            db.commit()

        # Add role if not already assigned
        if role not in db_user.roles:
            db_user.roles.append(role)
            db_user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_user)

        return db_user

    @staticmethod
    async def remove_role(db: Session, user_id: int, role_name: str) -> Optional[User]:
        """Remove role from user."""
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return None

        # Find role
        role = db.query(Role).filter(Role.name == role_name).first()
        if role and role in db_user.roles and role_name != "user":
            db_user.roles.remove(role)
            db_user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_user)

        return db_user