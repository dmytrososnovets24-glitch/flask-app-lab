from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app import db

CATEGORIES = ('news', 'publication', 'tech', 'other')


def utcnow():
    """Поточний час UTC без часової зони (заміна застарілого datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Post(db.Model):
    __tablename__ = 'posts'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    posted: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    category: Mapped[Optional[str]] = mapped_column(
        Enum(*CATEGORIES, name='post_category'), default='other')
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    author: Mapped[Optional[str]] = mapped_column(String(20), default='Anonymous')

    def __repr__(self):
        return f'<Post {self.id}: {self.title!r} ({self.category})>'
