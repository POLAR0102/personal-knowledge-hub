from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskStatus, AgentTaskType


class AgentTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        task_type: AgentTaskType,
        task_input: str,
    ) -> AgentTask:
        task = AgentTask(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            task_type=task_type,
            task_input=task_input,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def get_owned(self, *, task_id: int, user_id: int) -> AgentTask | None:
        statement = select(AgentTask).where(
            AgentTask.id == task_id,
            AgentTask.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def claim_for_execution(
        self,
        *,
        task_id: int,
        user_id: int,
        expected_status: AgentTaskStatus,
        started_at: datetime,
    ) -> bool:
        statement = (
            update(AgentTask)
            .where(
                AgentTask.id == task_id,
                AgentTask.user_id == user_id,
                AgentTask.status == expected_status,
            )
            .values(
                status=AgentTaskStatus.RUNNING,
                result_content=None,
                citations_json=None,
                error_message=None,
                started_at=started_at,
                completed_at=None,
            )
        )
        result = self.db.execute(statement)
        return result.rowcount == 1

    def list_owned(
        self,
        *,
        user_id: int,
        knowledge_base_id: int | None,
        offset: int,
        limit: int,
    ) -> list[AgentTask]:
        statement = select(AgentTask).where(AgentTask.user_id == user_id)
        if knowledge_base_id is not None:
            statement = statement.where(
                AgentTask.knowledge_base_id == knowledge_base_id
            )
        statement = (
            statement.order_by(AgentTask.created_at.desc(), AgentTask.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_owned(
        self,
        *,
        user_id: int,
        knowledge_base_id: int | None,
    ) -> int:
        statement = select(func.count(AgentTask.id)).where(
            AgentTask.user_id == user_id
        )
        if knowledge_base_id is not None:
            statement = statement.where(
                AgentTask.knowledge_base_id == knowledge_base_id
            )
        return self.db.execute(statement).scalar_one()
