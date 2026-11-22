from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import bcrypt, db, login_manager

if TYPE_CHECKING:
    from app.posts.models import Post


@login_manager.user_loader
def user_loader(user_id):
    # id із сесії приходить рядком
    return db.session.get(User, int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(60), nullable=False)

    # Зв'язок «один до багатьох»: пости, написані користувачем
    posts: Mapped[list["Post"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"User({self.username!r}, {self.email!r})"

    def hash_password(self):
        """Замінює пароль у відкритому вигляді його bcrypt-хешем."""
        self.password = bcrypt.generate_password_hash(self.password).decode('utf-8')

    def check_password(self, password):
        """Порівнює пароль із хешем, збереженим у БД."""
        try:
            return bcrypt.check_password_hash(self.password, password)
        except ValueError:  # у БД не bcrypt-хеш (старі записи) або задовгий пароль
            return False
