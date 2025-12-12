"""
需求管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement, RequirementType, TaskStatus

router = APIRouter()


# ========== Schemas ==========

class RequirementCreate(BaseModel):
    title: str
    requirement_type: RequirementType = RequirementType.OTHER
    dimensions: Optional[str] = None
    deadline: Optional[datetime] = None
    copywriting: Optional[str] = None
    reference_images: List[str] = []
    additional_notes: Optional[str] = None
    designer_id: Optional[int] = None
    estimated_hours: Optional[float] = None


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    requirement_type: Optional[RequirementType] = None
    dimensions: Optional[str] = None
    deadline: Optional[datetime] = None
    copywriting: Optional[str] = None
    reference_images: Optional[List[str]] = None
    additional_notes: Optional[str] = None
    designer_id: Optional[int] = None
    estimated_hours: Optional[float] = None


class RequirementResponse(BaseModel):
    id: int
    title: str
    requirement_type: str  # SQLite 兼容
    dimensions: Optional[str]
    deadline: Optional[datetime]
    copywriting: Optional[str]
    reference_images: Optional[List[str]] = []
    additional_notes: Optional[str]
    requester_id: int
    designer_id: Optional[int]
    estimated_hours: Optional[float]
    status: str  # SQLite 兼容
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    conversation_id: Optional[str] = None

    class Config:
        from_attributes = True


# ========== Routes ==========

@router.get("", response_model=List[RequirementResponse])
@router.get("/", response_model=List[RequirementResponse])
async def list_requirements(
    status: Optional[TaskStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取需求列表"""
    query = select(Requirement)
    
    if status:
        query = query.where(Requirement.status == status)
    
    # 根据角色过滤
    user_role = current_user.get("role")
    user_id = int(current_user["sub"])
    
    if user_role == "operator":
        # 运营只看自己的需求
        query = query.where(Requirement.requester_id == user_id)
    elif user_role == "designer":
        # 设计师只看分配给自己的需求
        query = query.where(Requirement.designer_id == user_id)
    
    query = query.offset(skip).limit(limit).order_by(Requirement.created_at.desc())
    result = await db.execute(query)
    
    return result.scalars().all()


@router.post("/", response_model=RequirementResponse)
async def create_requirement(
    req_data: RequirementCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建需求单"""
    requirement = Requirement(
        title=req_data.title,
        requirement_type=req_data.requirement_type,
        dimensions=req_data.dimensions,
        deadline=req_data.deadline,
        copywriting=req_data.copywriting,
        reference_images=req_data.reference_images,
        additional_notes=req_data.additional_notes,
        requester_id=int(current_user["sub"]),
        designer_id=req_data.designer_id,
        estimated_hours=req_data.estimated_hours,
        status=TaskStatus.PENDING
    )
    db.add(requirement)
    await db.commit()
    await db.refresh(requirement)
    
    return requirement


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取需求详情"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    return requirement


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    req_data: RequirementUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新需求单"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    # 更新字段
    update_data = req_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(requirement, field, value)
    
    await db.commit()
    await db.refresh(requirement)
    
    return requirement


@router.post("/{requirement_id}/upload-image")
async def upload_reference_image(
    requirement_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """上传参考图到 MinIO"""
    # TODO: 实现 MinIO 上传
    return {"message": "图片上传成功", "url": f"/images/{file.filename}"}
