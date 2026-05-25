"""
用户认证与权限管理
"""
from sqlalchemy.orm import Session
from models import User, Subject, UserRole
from typing import Optional, List
import secrets


def create_user(session: Session, username: str, password: str, display_name: str, role: UserRole) -> User:
    """创建新用户"""
    existing = session.query(User).filter(User.username == username).first()
    if existing:
        raise ValueError("用户名已存在")
    salt = secrets.token_hex(32)
    password_hash, _ = User.hash_password(password, salt)
    user = User(
        username=username,
        password_hash=password_hash,
        salt=salt,
        display_name=display_name,
        role=role
    )
    session.add(user)
    session.commit()
    return user


def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    """验证用户登录"""
    user = session.query(User).filter(User.username == username).first()
    if not user:
        return None
    if user.verify_password(password):
        return user
    return None


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return session.query(User).filter(User.id == user_id).first()


def assign_subject_to_crc(session: Session, subject_id: int, crc_id: int):
    """将受试者分配给CRC"""
    subject = session.get(Subject, subject_id)
    crc = session.get(User, crc_id)
    if not subject or not crc:
        raise ValueError("受试者或CRC不存在")
    if crc.role != UserRole.CRC:
        raise ValueError("只能将受试者分配给CRC角色")
    if crc not in subject.assigned_crcs:
        subject.assigned_crcs.append(crc)
        session.commit()


def unassign_subject_from_crc(session: Session, subject_id: int, crc_id: int):
    """取消CRC对受试者的负责"""
    subject = session.get(Subject, subject_id)
    crc = session.get(User, crc_id)
    if not subject or not crc:
        return
    if crc in subject.assigned_crcs:
        subject.assigned_crcs.remove(crc)
        session.commit()


def batch_assign_subjects_to_crc(session: Session, subject_ids: List[int], crc_id: int) -> int:
    """批量将受试者分配给指定CRC，crc_id=0 时取消所有CRC分配"""
    count = 0
    
    if crc_id == 0:
        # 取消所有CRC分配
        for subject_id in subject_ids:
            subject = session.get(Subject, subject_id)
            if not subject:
                continue
            if subject.assigned_crcs:
                count += len(subject.assigned_crcs)
                subject.assigned_crcs.clear()
    else:
        crc = session.get(User, crc_id)
        if not crc:
            raise ValueError("CRC不存在")
        if crc.role != UserRole.CRC:
            raise ValueError("只能将受试者分配给CRC角色")
        
        for subject_id in subject_ids:
            subject = session.get(Subject, subject_id)
            if not subject:
                continue
            if crc not in subject.assigned_crcs:
                subject.assigned_crcs.append(crc)
                count += 1
    
    if count > 0:
        session.commit()
    return count


def get_crcs_for_subject(session: Session, subject_id: int) -> List[User]:
    """获取负责该受试者的所有CRC"""
    subject = session.get(Subject, subject_id)
    if not subject:
        return []
    return [crc for crc in subject.assigned_crcs if crc.role == UserRole.CRC]


def get_subjects_for_crc(session: Session, crc_id: int) -> List[Subject]:
    """获取CRC负责的所有受试者"""
    crc = session.get(User, crc_id)
    if not crc or crc.role != UserRole.CRC:
        return []
    return crc.subjects


def get_all_crcs(session: Session) -> List[User]:
    """获取所有CRC用户"""
    return session.query(User).filter(User.role == UserRole.CRC).all()


def get_all_pis(session: Session) -> List[User]:
    """获取所有PI用户"""
    return session.query(User).filter(User.role == UserRole.PI).all()


def can_view_subject(user: User, subject: Subject) -> bool:
    """检查用户是否有权限查看受试者"""
    if user.role == UserRole.PI:
        return True
    if user.role == UserRole.CRC:
        return user in subject.assigned_crcs
    return False


def can_edit_subject(user: User, subject: Subject) -> bool:
    """检查用户是否有权限编辑受试者"""
    if user.role == UserRole.PI:
        return True
    if user.role == UserRole.CRC:
        return user in subject.assigned_crcs
    return False


def get_viewable_subjects(session: Session, user: User):
    """获取用户有权限查看的所有受试者"""
    from models import Subject
    if user.role == UserRole.PI:
        return session.query(Subject).all()
    else:
        return user.subjects