"""
系统管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole, OperatorDesignerBinding

router = APIRouter()


# ========== Schemas ==========

class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    department: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class BindingCreate(BaseModel):
    operator_id: int
    designer_id: int


class BindingResponse(BaseModel):
    id: int
    operator_id: int
    designer_id: int
    is_active: bool

    class Config:
        from_attributes = True


# ========== Routes ==========

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    role: Optional[UserRole] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表 (管理员)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以查看用户列表")
    
    query = select(User)
    if role:
        query = query.where(User.role == role)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/designers", response_model=List[UserListResponse])
async def list_designers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取设计师列表"""
    query = select(User).where(User.role == UserRole.DESIGNER).where(User.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/bindings", response_model=BindingResponse)
async def create_binding(
    binding_data: BindingCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建运营-设计师绑定"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以创建绑定")
    
    binding = OperatorDesignerBinding(
        operator_id=binding_data.operator_id,
        designer_id=binding_data.designer_id,
        is_active=True
    )
    db.add(binding)
    await db.commit()
    await db.refresh(binding)
    
    return binding


@router.get("/bindings", response_model=List[BindingResponse])
async def list_bindings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取绑定列表"""
    query = select(OperatorDesignerBinding).where(OperatorDesignerBinding.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/my-designer")
async def get_my_designer(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前运营绑定的设计师"""
    user_id = int(current_user["sub"])
    
    result = await db.execute(
        select(OperatorDesignerBinding)
        .where(OperatorDesignerBinding.operator_id == user_id)
        .where(OperatorDesignerBinding.is_active == True)
    )
    binding = result.scalar_one_or_none()
    
    if not binding:
        return {"designer_id": None, "designer": None}
    
    # 获取设计师信息
    designer_result = await db.execute(
        select(User).where(User.id == binding.designer_id)
    )
    designer = designer_result.scalar_one_or_none()
    
    return {
        "designer_id": binding.designer_id,
        "designer": UserListResponse.model_validate(designer) if designer else None
    }
