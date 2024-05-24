from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, session

Base = declarative_base()


class WebSocket(Base):
    __tablename__ = 'web_socket'

    ws_id = Column(Integer, primary_key=True, unique=True, autoincrement=False)
    mode = Column(String(10))
    try_ordering = Column(Boolean)

    @classmethod
    def get_all_web_sockets(cls):
        return session.query(cls).all()


Base.metadata.create_all(engine, checkfirst=True)