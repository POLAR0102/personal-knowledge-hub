import argparse
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.models import Document, KnowledgeBase, User
from app.db.session import SessionLocal

DEFAULT_EMAIL = "demo@example.com"
DEFAULT_PASSWORD = "Demo123456!"
DEFAULT_USERNAME = "演示用户"
DEMO_KNOWLEDGE_BASE_NAME = "智能个人知识库系统演示"
DEMO_DOCUMENT_NAME = "PKH-2026-项目说明.md"
DEMO_DOCUMENT_CONTENT = """# 智能个人知识库系统演示资料

智能个人知识库系统的项目代号为 PKH-2026。

## 核心技术

项目核心技术包括 React、FastAPI、ChromaDB 和 RAG。

## 项目计划

核心版本计划在 14 天内完成。

## 项目人员

项目负责人为测试用户张三。

## FastAPI 学习要点

FastAPI 用于构建类型安全的 Python Web API。本项目使用依赖注入完成数据库会话和用户身份认证，并通过 Pydantic 校验请求数据。

## RAG 工作流程

RAG 会先检索知识库中的相关文本片段，再将真实检索上下文交给 Chat Model 生成回答，并返回文档引用。
"""


@dataclass(frozen=True)
class DemoSeedResult:
    user_id: int
    knowledge_base_id: int
    document_id: int
    created_user: bool
    created_knowledge_base: bool
    created_document: bool


def seed_demo_data(
    db: Session,
    settings: Settings,
    *,
    email: str,
    username: str,
    password: str,
) -> DemoSeedResult:
    normalized_email = email.strip().lower()
    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()
    created_user = user is None
    if user is None:
        user = User(
            username=username.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()

    knowledge_base = db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.user_id == user.id,
            KnowledgeBase.name == DEMO_KNOWLEDGE_BASE_NAME,
        )
    ).scalar_one_or_none()
    created_knowledge_base = knowledge_base is None
    if knowledge_base is None:
        knowledge_base = KnowledgeBase(
            user_id=user.id,
            name=DEMO_KNOWLEDGE_BASE_NAME,
            description="用于答辩演示文档处理、语义检索、RAG 和 Agent 的资料库。",
        )
        db.add(knowledge_base)
        db.flush()

    document = db.execute(
        select(Document).where(
            Document.user_id == user.id,
            Document.knowledge_base_id == knowledge_base.id,
            Document.original_filename == DEMO_DOCUMENT_NAME,
        )
    ).scalar_one_or_none()
    created_document = document is None

    if document is None:
        stored_filename = (
            uuid5(
                NAMESPACE_URL,
                f"{normalized_email}:{DEMO_KNOWLEDGE_BASE_NAME}:{DEMO_DOCUMENT_NAME}",
            ).hex
            + ".md"
        )
        file_path = _demo_file_path(
            settings.upload_dir,
            user.id,
            knowledge_base.id,
            stored_filename,
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(DEMO_DOCUMENT_CONTENT, encoding="utf-8")
        document = Document(
            user_id=user.id,
            knowledge_base_id=knowledge_base.id,
            original_filename=DEMO_DOCUMENT_NAME,
            stored_filename=stored_filename,
            file_type="md",
            mime_type="text/markdown",
            file_size=file_path.stat().st_size,
            file_path=str(file_path),
        )
        db.add(document)
        db.flush()
    else:
        existing_path = Path(document.file_path).expanduser().resolve()
        upload_root = settings.upload_dir.expanduser().resolve()
        if not existing_path.is_relative_to(upload_root):
            raise ValueError("Existing demo document path is outside UPLOAD_DIR")
        if not existing_path.exists():
            existing_path.parent.mkdir(parents=True, exist_ok=True)
            existing_path.write_text(DEMO_DOCUMENT_CONTENT, encoding="utf-8")

    db.commit()
    return DemoSeedResult(
        user_id=user.id,
        knowledge_base_id=knowledge_base.id,
        document_id=document.id,
        created_user=created_user,
        created_knowledge_base=created_knowledge_base,
        created_document=created_document,
    )


def _demo_file_path(
    upload_dir: Path,
    user_id: int,
    knowledge_base_id: int,
    stored_filename: str,
) -> Path:
    upload_root = upload_dir.expanduser().resolve()
    file_path = (
        upload_root / str(user_id) / str(knowledge_base_id) / stored_filename
    ).resolve()
    if not file_path.is_relative_to(upload_root):
        raise ValueError("Demo upload path is outside UPLOAD_DIR")
    return file_path


def resolve_demo_password(app_env: str, provided_password: str | None) -> str:
    if provided_password is None and app_env.lower() == "production":
        raise ValueError("--password is required when APP_ENV=production")
    password = provided_password if provided_password is not None else DEFAULT_PASSWORD
    if len(password) < 6:
        raise ValueError("Demo password must contain at least 6 characters")
    return password


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create repeatable local data for the project demonstration."
    )
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password")
    args = parser.parse_args()

    settings = get_settings()
    try:
        password = resolve_demo_password(settings.app_env, args.password)
    except ValueError as exc:
        parser.error(str(exc))

    print("WARNING: demo data is for local demonstrations only.")
    print("Delete the demo account or change its password before public deployment.")
    with SessionLocal() as db:
        result = seed_demo_data(
            db,
            settings,
            email=args.email,
            username=args.username,
            password=password,
        )

    print(f"Demo user: {args.email.strip().lower()}")
    if result.created_user and args.password is None:
        print(f"Demo password: {DEFAULT_PASSWORD}")
    elif not result.created_user:
        print("Existing demo user reused; its password was not changed.")
    print(f"Knowledge base ID: {result.knowledge_base_id}")
    print(f"Document ID: {result.document_id} (pending processing)")
    print("Run this command again safely; existing demo records are reused.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
