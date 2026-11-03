import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from backend.app.core.database import AppSessionLocal
from backend.app.core.security import hash_password
from backend.app.models.user import User


def create_or_update_admin(email: str = "admin@sqlperformance.com", password: str = "Admin@12345", full_name: str = "Superadmin"):
    db = AppSessionLocal()
    user = db.scalar(select(User).where(User.email == email))

    if user:
        user.password_hash = hash_password(password)
        user.role = "ADMIN"
        user.is_active = True
        user.full_name = full_name
        db.commit()
        print(f"Admin account updated successfully: {email}")
    else:
        new_admin = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role="ADMIN",
            is_active=True,
        )
        db.add(new_admin)
        db.commit()
        print(f"Admin account created successfully: {email}")

    db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@sqlperformance.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin@12345"
    create_or_update_admin(email, password)
