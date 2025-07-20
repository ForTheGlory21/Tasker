import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ——— Database setup ———
engine = create_engine("sqlite:///tasks.db", connect_args={"check_same_thread": False})
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    due = Column(Date, nullable=False)
    user = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Inactive")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ——— UI ———
st.title("🛠️ Game‑Dev Task Tracker")

# Sidebar: add new task
st.sidebar.header("Add new task")
with st.sidebar.form("new_task"):
    n = st.text_input("Task name")
    d = st.date_input("Due by")
    u = st.selectbox("Assign to", ["You","Friend"])
    submitted = st.form_submit_button("➕ Add")
if submitted:
    session.add(Task(name=n, due=d, user=u))
    session.commit()
    st.sidebar.success("Task added!")

# Main area: list and manage tasks
statuses = ["Inactive","Working on it","Testing it","Bugged","Stuck","Completed"]

for t in session.query(Task).order_by(Task.due):
    with st.expander(f"{t.name} — due {t.due} — [{t.status}]"):
        # Status picker
        new_s = st.selectbox("Status", statuses, index=statuses.index(t.status), key=f"stat_{t.id}")
        if new_s != t.status:
            t.status = new_s
            session.commit()
            st.success("Status updated!")

        st.write(f"**Assigned to:** {t.user}")

        # Comments
        st.markdown("---")
        st.write("💬 **Comments:**")
        for c in session.query(Comment).filter_by(task_id=t.id).order_by(Comment.timestamp):
            st.write(f"> {c.timestamp:%Y-%m-%d %H:%M}: {c.text}")

        new_c = st.text_area("Add a comment…", key=f"com_{t.id}")
        if st.button("Post comment", key=f"post_{t.id}"):
            session.add(Comment(task_id=t.id, text=new_c))
            session.commit()
            st.experimental_rerun()  # refresh so comment appears
