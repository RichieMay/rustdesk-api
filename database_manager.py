from dataclasses import dataclass
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, create_engine, event

BaseEntity = declarative_base()

@dataclass
class DeviceEntity(BaseEntity):

    __tablename__ = "rustdesk_devices"

    # 主键ID
    id: str = Column(Text, primary_key=True)

    # 设备UUID
    uuid: str = Column(Text, nullable=False, unique=True)

    # 设备ID
    client: str = Column(Text, nullable=False, unique=True)

    # 设备主机名
    hostname: str = Column(Text, nullable=False)

    # 设备用户名
    username: str = Column(Text, nullable=True)

    # 操作系统
    os: str = Column(Text, nullable=True)

    # CPU
    cpu: str = Column(Text, nullable=True)

    # 内存
    memory: str = Column(Text, nullable=True)

    # 客户端版本
    version: str = Column(Text, nullable=True)

    # 修改时间
    modified_at: int = Column(Integer, nullable=False)

@dataclass
class AccountEntity(BaseEntity):

    __tablename__ = "rustdesk_accounts"

    # 主键ID
    id: str = Column(Text, primary_key=True)

    # 账户
    account: str = Column(Text, nullable=False, unique=True)

    # 密码
    password: str = Column(Text, nullable=False)

    # 昵称
    nickname: str = Column(Text, nullable=True)

    # 启/停用
    status: int = Column(Integer, nullable=False, default=1)

    # 创建时间
    create_at: int = Column(Integer, nullable=False)

@dataclass
class TokenEntity(BaseEntity):

    __tablename__ = "rustdesk_tokens"

    __table_args__ = (UniqueConstraint("account_id", "device_id", name="account_device_exist"),)

    # 主键ID
    id: str = Column(Text, primary_key=True)

    # 登录账户ID
    account_id: str = Column(Text, ForeignKey('rustdesk_accounts.id', ondelete='CASCADE'), nullable=False)

    # 登录设备ID
    device_id: str = Column(Text, ForeignKey('rustdesk_devices.id', ondelete='CASCADE'), nullable=False)

    # 登录时间
    login_at: int = Column(Integer, nullable=False)

    # 失效时间
    expire_at: int = Column(Integer, nullable=False)

    # 关联的账户
    account: AccountEntity = relationship("AccountEntity")

    # 关联的客户端设备
    device: DeviceEntity = relationship("DeviceEntity")

@dataclass
class TagEntity(BaseEntity):

    __tablename__ = "rustdesk_tags"

    # 主键ID
    id: str = Column(Text, primary_key=True)

    # 账户ID
    account_id: str = Column(Text, ForeignKey('rustdesk_accounts.id', ondelete='CASCADE'), nullable=False, unique=True)

    # 标签
    tags: str = Column(Text, nullable=False)

    # 标签颜色
    tag_colors: str = Column(Text, nullable=False)

    # 创建时间
    create_at: int = Column(Integer, nullable=False)

@dataclass
class AddressBookEntity(BaseEntity):

    __tablename__ = "rustdesk_address_books"

    __table_args__ = (UniqueConstraint("account_id", "peer", name="account_peer_exist"),)

    # 主键ID
    id: str = Column(Text, primary_key=True)

    # 账户ID
    account_id: str = Column(Text, ForeignKey('rustdesk_accounts.id', ondelete='CASCADE'), nullable=False)

    # 设备ID
    peer: str = Column(Text, nullable=False)

    # 设备用户名
    username: str = Column(Text, nullable=False)

    # 设备主机名
    hostname: str = Column(Text, nullable=False)

    # 设备平台  
    platform: str = Column(Text, nullable=False)

    # 绑定的标签
    tags: str = Column(Text, nullable=True)

    # 设备密码hash
    hash: str = Column(Text, nullable=True)

    # 别名
    alias: str = Column(Text, nullable=True)

    # 创建时间
    create_at: int = Column(Integer, nullable=False)

class DatabaseManager:

    def __init__(self) -> None:
        self._engine = create_engine(url='sqlite:////data/rustdest_api.db')
        event.listen(self._engine, 'connect', self._set_foreign_keys_on)
        self._session_maker = sessionmaker(bind=self._engine)
        BaseEntity.metadata.create_all(self._engine)

    def _set_foreign_keys_on(self, dbapi_con, _):
        dbapi_con.execute('PRAGMA foreign_keys=ON')

    def new_session(self) -> Session:
        return self._session_maker()

db_manager = DatabaseManager()
