import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class User:
    def __init__(self, username: str, password_hash: str, user_id: str = None, created_at: str = None):
        self.username = username
        self.password_hash = password_hash
        self.user_id = user_id or self._generate_user_id()
        self.created_at = created_at or datetime.now().isoformat()

    def _generate_user_id(self) -> str:
        """Generate a unique user ID"""
        return hashlib.md5(f"{self.username}{datetime.now().timestamp()}".encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash": self.password_hash,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user object from dictionary"""
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            user_id=data.get("user_id"),
            created_at=data.get("created_at")
        )


class UserManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self._ensure_data_files()

    def _ensure_data_files(self):
        """Ensure user and session data files exist"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump([], f)
                
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f)

    def _hash_password(self, password: str) -> str:
        """Hash password with SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, password: str) -> Optional[User]:
        """Create a new user"""
        # Check if user already exists
        if self.get_user_by_username(username):
            return None

        # Create new user
        password_hash = self._hash_password(password)
        user = User(username, password_hash)
        
        # Load existing users
        users = self._load_users()
        users.append(user.to_dict())
        
        # Save users
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            return user
        except Exception as e:
            print(f"Error saving user: {e}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        if not user:
            return None
            
        password_hash = self._hash_password(password)
        if user.password_hash == password_hash:
            return user
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        users = self._load_users()
        for user_data in users:
            if user_data["username"] == username:
                return User.from_dict(user_data)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user ID"""
        users = self._load_users()
        for user_data in users:
            if user_data["user_id"] == user_id:
                return User.from_dict(user_data)
        return None

    def _load_users(self) -> list:
        """Load users from file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def create_session(self, user: User) -> str:
        """Create a new session for user"""
        session_id = hashlib.md5(f"{user.user_id}{datetime.now().timestamp()}".encode()).hexdigest()
        
        # Load existing sessions
        sessions = self._load_sessions()
        
        # Add new session (expires in 24 hours)
        sessions[session_id] = {
            "user_id": user.user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        # Save sessions
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
            
        return session_id

    def validate_session(self, session_id: str) -> Optional[User]:
        """Validate session and return associated user"""
        sessions = self._load_sessions()
        
        if session_id not in sessions:
            return None
            
        session = sessions[session_id]
        
        # Check if session expired
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            # Remove expired session
            del sessions[session_id]
            self._save_sessions(sessions)
            return None
            
        # Get user
        return self.get_user_by_id(session["user_id"])

    def destroy_session(self, session_id: str):
        """Destroy session (logout)"""
        sessions = self._load_sessions()
        if session_id in sessions:
            del sessions[session_id]
            self._save_sessions(sessions)

    def _load_sessions(self) -> dict:
        """Load sessions from file"""
        try:
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_sessions(self, sessions: dict):
        """Save sessions to file"""
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)