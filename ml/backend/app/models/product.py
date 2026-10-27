from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observations: Mapped[list["PriceObservation"]] = relationship(back_populates="product")
