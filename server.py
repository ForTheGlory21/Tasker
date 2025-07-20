from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import date

DATABASE_URL = "sqlite:///./tasks.db"

# Create engine and session
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Ensure columns exist ---
# SQLite: add description and priority if missing
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE tasks ADD COLUMN description TEXT DEFAULT ""'))
    except Exception:
        pass
    try:
        conn.execute(text('ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 1'))
    except Exception:
        pass

# --- SQLAlchemy Model ---
class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    due = Column(Date, index=True)
    status = Column(String, default="Inactive")
    user = Column(String)
    description = Column(Text, default="")
    priority = Column(Integer, default=1)

# Create tables (does not recreate existing columns)
Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class TaskBase(BaseModel):
    name: str
    due: date
    status: str
    user: str
    description: Optional[str] = ""
    priority: Optional[int] = 1

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int

    class Config:
        orm_mode = True

# --- FastAPI App ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---
@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskModel(
        name=payload.name,
        due=payload.due,
        status=payload.status,
        user=payload.user,
        description=payload.description,
        priority=payload.priority
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks", response_model=List[Task])
def read_tasks(db: Session = Depends(get_db)):
    return db.query(TaskModel).all()

@app.put("/tasks/{task_id}/status", response_model=Task)
def update_status(task_id: int, status: str, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = status
    db.commit()
    db.refresh(task)
    return task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskCreate, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.name = payload.name
    task.due = payload.due
    task.status = payload.status
    task.user = payload.user
    task.description = payload.description
    task.priority = payload.priority
    db.commit()
    db.refresh(task)
    return task
