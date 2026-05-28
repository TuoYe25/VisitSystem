"""
认证中间件和依赖注入
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import datetime
from models import get_db, User
from crud_user import get_user_by_id

SECRET_KEY = "your-secret-key-here"  # 生产环境应使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_db)
) -> User:
    """获取当前登录用户（支持 Header 和 Cookie 两种方式）"""
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的令牌")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="令牌无效")
    user = get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_pi(user: User = Depends(get_current_user)) -> User:
    """要求用户为PI角色"""
    from models import UserRole
    if user.role != UserRole.PI:
        raise HTTPException(status_code=403, detail="需要PI权限")
    return user


def require_crc(user: User = Depends(get_current_user)) -> User:
    """要求用户为CRC角色"""
    from models import UserRole
    if user.role != UserRole.CRC:
        raise HTTPException(status_code=403, detail="需要CRC权限")
    return user