from datetime import date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Date)
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# --- Database Setup ---
DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)
Base = declarative_base()

class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    due = Column(Date)
    status = Column(String, index=True)
    user = Column(String, index=True)
    description = Column(String, nullable=True)
    priority = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class TaskBase(BaseModel):
    name: str
    category: Optional[str] = None
    due: date
    status: str
    user: str
    description: Optional[str] = None
    priority: Optional[int] = 0

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int

    class Config:
        orm_mode = True

class StatusUpdate(BaseModel):
    status: str

# --- App & Dependencies ---
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CRUD Endpoints ---
@app.post("/tasks", response_model=Task)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    db_task = TaskModel(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks", response_model=List[Task])
def read_tasks(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    user: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(TaskModel)
    if search:
        query = query.filter(TaskModel.name.contains(search))
    if category:
        query = query.filter(TaskModel.category == category)
    if status:
        query = query.filter(TaskModel.status == status)
    if user:
        query = query.filter(TaskModel.user == user)
    tasks = query.offset(skip).limit(limit).all()
    return tasks

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    db_task = db.get(TaskModel, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}/status", response_model=Task)
def update_status(
    task_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db)
):
    db_task = db.get(TaskModel, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.status = payload.status
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    db_task = db.get(TaskModel, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()