"""Bounded, expiring in-memory conversations for the local prototype."""
from dataclasses import dataclass, field
import secrets
from threading import Lock
import time


@dataclass
class Conversation:
    id: str
    messages: list = field(default_factory=list)
    slots: dict = field(default_factory=dict)
    artifact: object = None
    touched: float = field(default_factory=time.monotonic)
    lock: object = field(default_factory=Lock)


class ConversationStore:
    def __init__(self, ttl=3600, capacity=100):
        self.ttl = ttl
        self.capacity = capacity
        self.sessions = {}
        self.lock = Lock()

    def get(self, identifier=None):
        with self.lock:
            now = time.monotonic()
            self.sessions = {key: session for key, session in self.sessions.items()
                             if now - session.touched <= self.ttl or session.lock.locked()}
            if identifier:
                if identifier not in self.sessions:
                    raise ValueError("对话不存在或已过期，请开启新对话")
                session = self.sessions[identifier]
            else:
                if len(self.sessions) >= self.capacity:
                    raise ValueError("本机会话数量已达到上限，请清除旧对话")
                session = Conversation(secrets.token_urlsafe(24))
                self.sessions[session.id] = session
            session.touched = now
            return session

    def clear(self, identifier):
        with self.lock:
            session = self.sessions.get(identifier)
            if session is not None:
                if session.lock.locked():
                    raise ValueError("当前对话正在处理，请完成后再清除")
                del self.sessions[identifier]
        return {"cleared": True}
