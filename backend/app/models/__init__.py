from ..core.database import Base

__all__ = ["Base"]

from app.core.database import Base  # noqa: F401
from .user import User, Station  # noqa: F401
from .ticket import Ticket, Task, TicketComment  # noqa: F401
from .ticket_history import TicketHistory  # noqa: F401
from .task_history import TaskHistory  # noqa: F401
from .chat import Chat, Message  # noqa: F401
from .notification import Notification  # noqa: F401
from .attachment import Attachment  # noqa: F401

