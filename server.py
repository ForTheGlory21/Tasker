# server.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Date, Text, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ——— Database setup ———
engine = create_engine(
    "sqlite:///tasks.db",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"
    id     = Column(Integer, primary_key=True, index=True)
    name   = Column(String, nullable=False)
    due    = Column(Date,   nullable=False)
    user   = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Inactive")

class CommentDB(Base):
    __tablename__ = "comments"
    id        = Column(Integer, primary_key=True, index=True)
    task_id   = Column(Integer, nullable=False)
    text      = Column(Text,    nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


# ——— Pydantic schemas ———
class Comment(BaseModel):
    id: int
    text: str
    timestamp: datetime

    class Config:
        from_attributes = True

class Task(BaseModel):
    id: int
    name: str
    due: date
    user: str
    status: str
    comments: List[Comment] = []

    class Config:
        from_attributes = True

# **Missing –>** request bodies for create/update:
class TaskCreate(BaseModel):
    name: str
    due: date
    user: str

class StatusUpdate(BaseModel):
    status: str

class CommentCreate(BaseModel):
    text: str


# ——— Dependency ———
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ——— App setup ———
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# helper to bundle tasks + comments
def load_tasks(db: Session):
    tasks = db.query(TaskDB).order_by(TaskDB.due).all()
    out: List[Task] = []
    for t in tasks:
        comments = (
            db.query(CommentDB)
              .filter(CommentDB.task_id == t.id)
              .order_by(CommentDB.timestamp)
              .all()
        )
        out.append(
            Task(
                id=t.id,
                name=t.name,
                due=t.due,
                user=t.user,
                status=t.status,
                comments=comments
            )
        )
    return out


# ——— Endpoints ———
@app.get("/tasks", response_model=List[Task])
def get_tasks(db: Session = Depends(get_db)):
    return load_tasks(db)

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db)
):
    t = TaskDB(
        name=payload.name,
        due=payload.due,
        user=payload.user,
        status="Inactive"
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return Task.from_orm(t)

@app.put("/tasks/{task_id}/status", response_model=Task)
def update_status(
    task_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db)
):
    t = db.query(TaskDB).get(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    t.status = payload.status
    db.commit()
    db.refresh(t)
    # re‑load comments so they’re in the response
    comments = db.query(CommentDB).filter(CommentDB.task_id==t.id).all()
    return Task(
        id=t.id, name=t.name, due=t.due,
        user=t.user, status=t.status,
        comments=comments
    )

@app.post("/tasks/{task_id}/comments", response_model=Comment, status_code=201)
def add_comment(
    task_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db)
):
    if not db.query(TaskDB).get(task_id):
        raise HTTPException(404, "Task not found")
    c = CommentDB(task_id=task_id, text=payload.text)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
