"""Доска объявлений и опросы (главная страница)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Announcement, AnnouncementComment, Poll, PollOption, PollVote, User
from app.schemas.announcement import (
    AnnouncementCommentCreate,
    AnnouncementCommentResponse,
    AnnouncementCommentUpdate,
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.schemas.poll import PollCreate, PollResponse, PollVoteCreate

from .deps import get_current_user, require_role

router = APIRouter(prefix="/board", tags=["board"])


def _author_brief(user: User) -> dict:
    return {"id": user.id, "full_name": user.full_name}


def _announcement_response(a) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=a.id,
        title=a.title,
        content=a.content,
        author_id=a.author_id,
        author=_author_brief(a.author) if a.author else None,
        created_at=a.created_at,
        is_pinned=getattr(a, "is_pinned", False),
        is_important=getattr(a, "is_important", False),
        tag=getattr(a, "tag", None),
    )


# ——— Объявления ———

@router.get("/announcements", response_model=list[AnnouncementResponse])
def list_announcements(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    filter: str | None = Query(None, description="all | important | pinned"),
):
    """Список объявлений. filter: important — только важные, pinned — только закреплённые."""
    q = db.query(Announcement).options(joinedload(Announcement.author))
    if filter == "important":
        q = q.filter(Announcement.is_important == True)
    elif filter == "pinned":
        q = q.filter(Announcement.is_pinned == True)
    items = q.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(100).all()
    return [_announcement_response(a) for a in items]


@router.post("/announcements", response_model=AnnouncementResponse)
def create_announcement(
    data: AnnouncementCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Создать объявление (любой авторизованный)."""
    a = Announcement(
        title=data.title.strip(),
        content=data.content.strip(),
        author_id=user.id,
        is_pinned=getattr(data, "is_pinned", False),
        is_important=getattr(data, "is_important", False),
        tag=(data.tag.strip() if data.tag else None) if getattr(data, "tag", None) else None,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return AnnouncementResponse(
        id=a.id,
        title=a.title,
        content=a.content,
        author_id=a.author_id,
        author={"id": user.id, "full_name": user.full_name},
        created_at=a.created_at,
        is_pinned=a.is_pinned,
        is_important=a.is_important,
        tag=a.tag,
    )


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Редактировать объявление (автор или admin/chief)."""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    if a.author_id != user.id and user.role not in ("admin", "chief") and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k == "title" and v is not None:
            a.title = v.strip()
        elif k == "content" and v is not None:
            a.content = v.strip()
        elif k == "is_pinned":
            a.is_pinned = v
        elif k == "is_important":
            a.is_important = v
        elif k == "tag":
            a.tag = v.strip() if v else None
    db.commit()
    db.refresh(a)
    a = db.query(Announcement).options(joinedload(Announcement.author)).get(a.id)
    return _announcement_response(a)


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Удалить объявление (автор или admin/chief)."""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    if a.author_id != user.id and user.role not in ("admin", "chief") and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    db.delete(a)
    db.commit()
    return {"detail": "ok"}


# ——— Комментарии к объявлениям ———

@router.get("/announcements/{announcement_id}/comments", response_model=list[AnnouncementCommentResponse])
def list_announcement_comments(
    announcement_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Комментарии к объявлению."""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    comments = (
        db.query(AnnouncementComment)
        .options(joinedload(AnnouncementComment.author))
        .filter(AnnouncementComment.announcement_id == announcement_id)
        .order_by(AnnouncementComment.created_at.asc())
        .all()
    )
    return [
        AnnouncementCommentResponse(
            id=c.id,
            announcement_id=c.announcement_id,
            author_id=c.author_id,
            author=_author_brief(c.author) if c.author else None,
            content=c.content,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post("/announcements/{announcement_id}/comments", response_model=AnnouncementCommentResponse)
def create_announcement_comment(
    announcement_id: int,
    data: AnnouncementCommentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Добавить комментарий к объявлению."""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текст комментария не может быть пустым")
    c = AnnouncementComment(announcement_id=announcement_id, author_id=user.id, content=content)
    db.add(c)
    db.commit()
    db.refresh(c)
    return AnnouncementCommentResponse(
        id=c.id,
        announcement_id=c.announcement_id,
        author_id=c.author_id,
        author={"id": user.id, "full_name": user.full_name},
        content=c.content,
        created_at=c.created_at,
    )


@router.patch("/announcements/{announcement_id}/comments/{comment_id}", response_model=AnnouncementCommentResponse)
def update_announcement_comment(
    announcement_id: int,
    comment_id: int,
    data: AnnouncementCommentUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Редактировать комментарий (автор или admin/chief)."""
    c = (
        db.query(AnnouncementComment)
        .filter(
            AnnouncementComment.id == comment_id,
            AnnouncementComment.announcement_id == announcement_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комментарий не найден")
    if c.author_id != user.id and user.role not in ("admin", "chief") and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текст не может быть пустым")
    c.content = content
    db.commit()
    db.refresh(c)
    c = (
        db.query(AnnouncementComment)
        .options(joinedload(AnnouncementComment.author))
        .filter(AnnouncementComment.id == comment_id)
        .first()
    )
    return AnnouncementCommentResponse(
        id=c.id,
        announcement_id=c.announcement_id,
        author_id=c.author_id,
        author=_author_brief(c.author) if c.author else None,
        content=c.content,
        created_at=c.created_at,
    )


@router.delete("/announcements/{announcement_id}/comments/{comment_id}")
def delete_announcement_comment(
    announcement_id: int,
    comment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Удалить комментарий (автор или admin/chief)."""
    c = (
        db.query(AnnouncementComment)
        .filter(
            AnnouncementComment.id == comment_id,
            AnnouncementComment.announcement_id == announcement_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комментарий не найден")
    if c.author_id != user.id and user.role not in ("admin", "chief") and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    db.delete(c)
    db.commit()
    return {"detail": "ok"}


# ——— Опросы ———

def _poll_response(poll: Poll, current_user_id: int) -> PollResponse:
    my_vote = next((v for v in poll.votes if v.user_id == current_user_id), None)
    options = [
        {"id": o.id, "poll_id": o.poll_id, "text": o.text, "votes_count": len(o.votes)}
        for o in poll.options
    ]
    return PollResponse(
        id=poll.id,
        question=poll.question,
        created_by_id=poll.created_by_id,
        created_at=poll.created_at,
        closed_at=poll.closed_at,
        options=options,
        my_vote_option_id=my_vote.option_id if my_vote else None,
    )


@router.get("/polls", response_model=list[PollResponse])
def list_polls(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Список опросов (активные и закрытые, последние сверху)."""
    polls = (
        db.query(Poll)
        .options(
            joinedload(Poll.options).joinedload(PollOption.votes),
            joinedload(Poll.votes),
        )
        .order_by(Poll.created_at.desc())
        .limit(50)
        .all()
    )
    return [_poll_response(p, user.id) for p in polls]


@router.post("/polls", response_model=PollResponse)
def create_poll(
    data: PollCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Создать опрос (минимум 2 варианта ответа)."""
    if len(data.options) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно минимум 2 варианта ответа")
    poll = Poll(question=data.question.strip(), created_by_id=user.id)
    db.add(poll)
    db.flush()
    for opt in data.options:
        o = PollOption(poll_id=poll.id, text=opt.text.strip())
        db.add(o)
    db.commit()
    db.refresh(poll)
    poll = (
        db.query(Poll)
        .options(
            joinedload(Poll.options).joinedload(PollOption.votes),
            joinedload(Poll.votes),
        )
        .filter(Poll.id == poll.id)
        .first()
    )
    return _poll_response(poll, user.id)


@router.post("/polls/{poll_id}/vote", response_model=PollResponse)
def vote_poll(
  poll_id: int,
  data: PollVoteCreate,
  db: Annotated[Session, Depends(get_db)],
  user: Annotated[User, Depends(get_current_user)],
):
    """Проголосовать (один раз за опрос; можно изменить выбор)."""
    poll = (
        db.query(Poll)
        .options(
            joinedload(Poll.options).joinedload(PollOption.votes),
            joinedload(Poll.votes),
        )
        .filter(Poll.id == poll_id)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опрос не найден")
    if poll.closed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Опрос закрыт")
    option_ids = [o.id for o in poll.options]
    if data.option_id not in option_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный вариант ответа")
    existing = db.query(PollVote).filter(PollVote.poll_id == poll_id, PollVote.user_id == user.id).first()
    if existing:
        existing.option_id = data.option_id
    else:
        db.add(PollVote(poll_id=poll_id, option_id=data.option_id, user_id=user.id))
    db.commit()
    db.refresh(poll)
    poll = (
        db.query(Poll)
        .options(
            joinedload(Poll.options).joinedload(PollOption.votes),
            joinedload(Poll.votes),
        )
        .filter(Poll.id == poll_id)
        .first()
    )
    return _poll_response(poll, user.id)


@router.post("/polls/{poll_id}/close", response_model=PollResponse)
def close_poll(
  poll_id: int,
  db: Annotated[Session, Depends(get_db)],
  user: Annotated[User, Depends(get_current_user)],
):
    """Закрыть опрос (создатель или admin/chief)."""
    from datetime import datetime
    poll = (
        db.query(Poll)
        .options(
            joinedload(Poll.options).joinedload(PollOption.votes),
            joinedload(Poll.votes),
        )
        .filter(Poll.id == poll_id)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опрос не найден")
    if poll.closed_at:
        return _poll_response(poll, user.id)
    if poll.created_by_id != user.id and user.role not in ("admin", "chief") and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    poll.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(poll)
    return _poll_response(poll, user.id)
