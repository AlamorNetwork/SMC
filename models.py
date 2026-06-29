from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class WatchlistModel(Base):
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)