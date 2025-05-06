import os
import re
import uuid
import functools
import dataclasses
from datetime import datetime
from flask import json, request, Blueprint, Flask
from database_manager import db_manager, AccountEntity, DeviceEntity, TokenEntity, TagEntity, AddressBookEntity

app = Flask(__name__)
api = Blueprint('/api', __name__, url_prefix='/api')
admin_api = Blueprint('/admin/api', __name__, url_prefix='/admin/api')

HTTP_DECODE_TOEKN = 'HTTP_DECODE_TOEKN'
TOKEN_LIFETIME_MS = 48 * 3600 * 1000 # 令牌存活毫秒
ENABLE_API_DEBUG = 'ENABLE_API_DEBUG' in os.environ

class Utils:
    @staticmethod
    def uuid(include_dash: bool = False) -> str:
        hex_str = str(uuid.uuid4())
        return hex_str if include_dash else hex_str.replace("-", "")

def get_token_from_header():
    return request.headers.environ[HTTP_DECODE_TOEKN]

# 校验令牌
def token_required(func):
    @functools.wraps(func)
    def check_token(*args, **kwargs):
        authorization = request.headers.get('Authorization')
        if not authorization:
            return {'error': '请先登录账户'}, 401

        what = re.fullmatch(r'Bearer\s(\S+)', authorization)
        if not what:
            return {'error': '身份信息认证失败'}, 401

        with db_manager.new_session() as session:
            login_token = session.query(TokenEntity).filter_by(id=what.group(1)).first()
            if not login_token:
                return {'error': '身份信息认证失败'}, 401

            if login_token.expire_at <= int(datetime.now().timestamp() * 1000):
                session.delete(login_token)
                session.commit()
                return {'error': '身份信息已过期,请重新登录'}, 401

            request.headers.environ[HTTP_DECODE_TOEKN] = dataclasses.asdict(login_token)
        return func(*args, **kwargs)
    return check_token

# 开启接口调试
@app.after_request
def after_request_handler(response):
    try:
        if ENABLE_API_DEBUG:
            print(f'\nurl: {request.url}\nrequest: {request.get_data()}\nresponse: {response.get_data()}', flush=True)
    except Exception as ec:
        print(f'\nerror: {str(ec)}', flush=True)
    finally:
        return response

# 自定义404
@app.errorhandler(404)
def page_not_found(_):
    return {'error': '请求资源未找到'}, 404

# 自定义405
@app.errorhandler(405)
def method_not_allowed(_):
    return {'error': '请求方法错误'}, 405

# 自定义500
@app.errorhandler(500)
def internal_server_error(error):
    print(f'\nerror: {str(error)}', flush=True)
    return {'error': '服务请求错误, 稍后重试'}, 500

# 添加账户，客户端已传递明文密码，直接存储即可
@admin_api.route('/accounts', methods=['POST'])
def add_user():
    add_req = request.get_json()
    with db_manager.new_session() as session:
        account = session.query(AccountEntity).filter_by(account=add_req.get('account')).first()
        if account:
            return {'message': f"账户:{add_req.get('account')}已存在"}

        create_at = int(datetime.now().timestamp() * 1000)
        session.add(AccountEntity(id=Utils.uuid(), account=add_req.get('account'), password=add_req.get('password'), create_at=create_at))
        session.commit()
        return {'message': f"账户:{add_req.get('account')}添加成功"}

# 删除账户
@admin_api.route('/accounts', methods=['DELETE'])
def delete_user():
    with db_manager.new_session() as session:
        account = session.query(AccountEntity).filter_by(account=request.args.get('account')).first()
        if account:
            session.delete(account)
            session.commit()
            return {'message': f"账户:{request.args.get('account')}删除成功"}

        return {'message': f"账户:{request.args.get('account')}不存在"}  

# 修改账户
@admin_api.route('/accounts', methods=['PUT'])
def edit_user():
    edit_req = request.get_json()
    with db_manager.new_session() as session:
        account = session.query(AccountEntity).filter_by(account=request.args.get('account')).first()
        if not account:
            return {'message': f"账户:{edit_req.get('account')}不存在"}

        modified = False
        if edit_req.get('status') is not None:
            modified = True
            account.status = int(edit_req.get('status'))
            if not account.status: # 禁用账户立即吊销令牌
                session.query(TokenEntity).filter_by(account_id=account.id).delete()

        if edit_req.get('nickname'):
            modified = True
            account.nickname = edit_req.get('nickname')

        if edit_req.get('password'):
            modified = True
            account.password = edit_req.get('password')
 
        session.commit()
        return {'message': f"账户:{edit_req.get('account')}{'修改成功' if modified else '未修改'}"}

# 更新设备在线状态的心跳
@api.route('/heartbeat', methods=['POST'])
def heartbeat():
    heartbeat_req = request.get_json()
    with db_manager.new_session() as session:
        device = session.query(DeviceEntity).filter_by(uuid=heartbeat_req.get('uuid')).first()
        if device:
            device.modified_at = int(datetime.now().timestamp() * 1000)

            login_token = session.query(TokenEntity).filter_by(device_id=device.id).first()
            if login_token:
                login_token.expire_at = device.modified_at + TOKEN_LIFETIME_MS #  自动保活设备登录的账号

            session.commit()
        return {'data': '请求成功'}

# 更新设备系统信息
@api.route('/sysinfo', methods=['POST'])
def sysinfo():
    sysinfo_req = request.get_json()
    with db_manager.new_session() as session:
        device = session.query(DeviceEntity).filter_by(uuid=sysinfo_req.get('uuid')).first()
        if not device:
            device = DeviceEntity(id=Utils.uuid(), uuid=sysinfo_req.get('uuid'))
            session.add(device)

        device.os = sysinfo_req.get('os')
        device.cpu = sysinfo_req.get('cpu')
        device.client = sysinfo_req.get('id')
        device.memory = sysinfo_req.get('memory')
        device.version = sysinfo_req.get('version')
        device.hostname = sysinfo_req.get('hostname')
        device.username = sysinfo_req.get('username')
        device.modified_at = int(datetime.now().timestamp() * 1000)
        session.commit()
        return {'data': '上传系统信息成功'} 

# 账户登录
@api.route('/login', methods=['POST'])
def login():
    login_req = request.get_json()
    with db_manager.new_session() as session:
        account = session.query(AccountEntity).filter_by(account=login_req.get('username'), password=login_req.get('password')).first()
        if not account:
            return {'error': '用户名或密码错误'}

        # 清理当前账户过期令牌
        login_total = 0
        allow_login_total = 10
        login_access_token = None
        for login_token in session.query(TokenEntity).filter_by(account_id=account.id).all():
            if login_token.expire_at <= int(datetime.now().timestamp() * 1000):
                session.delete(login_token)
                continue

            if login_token.device.uuid == login_req.get('uuid'): # 同一设备已登录直接返回token
                login_access_token = login_token.id
                break
            login_total += 1

        if login_total >= allow_login_total:
            session.commit()
            return {'error': f'同一账户最多允许同时登录{allow_login_total}次'}

        # 保存登录设备信息
        device = session.query(DeviceEntity).filter_by(uuid=login_req.get('uuid')).first()
        if not device:
            device = DeviceEntity(id=Utils.uuid(), uuid=login_req.get('uuid'))
            session.add(device)

        device.client = login_req.get('id')
        device.hostname = login_req.get('deviceInfo').get('name')
        device.modified_at = int(datetime.now().timestamp() * 1000)

        # 生成新的用户令牌
        if not login_access_token:
            login_access_token = Utils.uuid()
            login_token = TokenEntity(id=login_access_token, account_id=account.id, device_id=device.id)
            login_token.login_at = int(datetime.now().timestamp() * 1000)
            login_token.expire_at = login_token.login_at + TOKEN_LIFETIME_MS
            session.add(login_token)

        session.commit()
        return {'type': 'access_token', 'access_token': login_access_token, 'user': {'name': account.account}}

# 账户登出
@api.route('/logout', methods=['POST'])
@token_required
def logout():
    login_token = get_token_from_header()
    with db_manager.new_session() as session:
        session.query(TokenEntity).filter_by(id=login_token.get('id')).delete()
        session.commit()
        return {'data': '登出成功'} 

# 当前账户
@api.route('/currentUser', methods=['GET', 'POST'])
@token_required
def current_user():
    account = get_token_from_header().get('account')
    return {'name': account.get('account'), 'status': account.get('status'), 'is_admin': False, 'info': {}}

# 更新地址簿
@api.route('/ab', methods=['POST'])
@token_required
def update_address_book():
    login_token = get_token_from_header()
    address_books_req = request.get_json()
    address_books = json.loads(address_books_req.get('data'))
    with db_manager.new_session() as session:
        # 创建时间
        create_at = int(datetime.now().timestamp() * 1000)

        # 保存tags
        tag = session.query(TagEntity).filter_by(account_id=login_token.get('account_id')).first()
        if not tag:
            tag = TagEntity(id=Utils.uuid(), account_id=login_token.get('account_id'))
            session.add(tag)

        tag.create_at = create_at
        tag.tags = ','.join(address_books.get('tags'))
        tag.tag_colors = address_books.get('tag_colors', '{}')

        # 保存地址簿,先清空后添加
        session.query(AddressBookEntity).filter_by(account_id=login_token.get('account_id')).delete()
        for peer in address_books.get('peers', []):
            address_book = AddressBookEntity(id=Utils.uuid(), account_id=login_token.get('account_id'))
            address_book.create_at = create_at
            address_book.peer = peer.get('id')
            address_book.username = peer.get('username')
            address_book.hostname = peer.get('hostname')
            address_book.platform = peer.get('platform')
            address_book.hash = peer.get('hash')
            address_book.alias = peer.get('alias')
            address_book.tags = ','.join(peer.get('tags'))
            session.add(address_book)

        session.commit()
        return {'data': '添加到地址簿成功'} 

# 获取地址簿
@api.route('/ab', methods=['GET'])
@token_required
def get_address_book():
    login_token = get_token_from_header()
    with db_manager.new_session() as session:
        address_books = {'tags': [], 'tag_colors': '{}', 'peers': []}

        # 获取tags
        tag = session.query(TagEntity).filter_by(account_id=login_token.get('account_id')).first()
        if tag:
            address_books['tags'] = [tag for tag in tag.tags.split(',') if tag]
            address_books['tag_colors'] = tag.tag_colors

        # 获取地址簿
        for address_book in session.query(AddressBookEntity).filter_by(account_id=login_token.get('account_id')).all():
            peer = {'id': address_book.peer}
            peer['username'] = address_book.username
            peer['hostname'] = address_book.hostname
            peer['platform'] = address_book.platform
            peer['hash'] = address_book.hash
            peer['alias'] = address_book.alias
            peer['tags'] = [tag for tag in address_book.tags.split(',') if tag]
            address_books['peers'].append(peer)
        return {'data': json.dumps(address_books), 'updated_at': int(datetime.now().timestamp() * 1000)}

# 获取群组
@api.route('/device-group/accessible', methods=['GET'])
@token_required
def get_accessible_device_group():
    return {'total': 0, 'data': [], 'updated_at': int(datetime.now().timestamp() * 1000)}

# 获取群组用户
@api.route('/users', methods=['GET'])
@token_required
def get_device_group_user():
    return {'total': 0, 'data': [], 'updated_at': int(datetime.now().timestamp() * 1000)}

# 获取群组设备
@api.route('/peers', methods=['GET'])
@token_required
def get_device_group_peer():
    return {'total': 0, 'data': [], 'updated_at': int(datetime.now().timestamp() * 1000)}

# 在反代后以单线程运行, 只应该反代api接口
app.register_blueprint(api)
app.register_blueprint(admin_api)
app.run(host='0.0.0.0', port=80, threaded=False)
