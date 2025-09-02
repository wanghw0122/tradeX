import imaplib
import email
import time
import re
import logging
import sys
import codecs
from email.header import decode_header

# 尝试设置控制台编码为UTF-8（Windows）
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except:
        pass

# 安全字符串处理函数
def safe_string(s, encoding='gbk', errors='ignore'):
    """
    安全处理字符串，避免编码错误
    """
    if not isinstance(s, str):
        return s
        
    try:
        s.encode(encoding, errors=errors)
        return s
    except UnicodeEncodeError:
        return s.encode(encoding, errors=errors).decode(encoding)

# 设置日志
def setup_logger():
    logger = logging.getLogger("QQMail-Controller")
    logger.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 文件处理器 - 使用UTF-8编码
    file_handler = logging.FileHandler("email_controller.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

class QQMailCommandClient:
    def __init__(self, username, password, allowed_sender=None, mailbox='INBOX'):
        """
        初始化QQ邮件命令客户端
        """
        self.username = username
        self.password = password
        self.allowed_sender = allowed_sender.lower() if allowed_sender else None
        self.mailbox = mailbox
        self.imap_server = 'imap.qq.com'
        self.imap_port = 993
        self.connection = None
        self.running = False
        
        # 编译命令正则表达式：匹配 "buy 123" 格式
        self.command_pattern = re.compile(r'^\s*buy\s+(\d+)\s*$', re.IGNORECASE)

    def connect(self):
        """连接到QQ邮箱IMAP服务器"""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.username, self.password)
            self.connection.select(self.mailbox)
            logger.info(f"成功连接到QQ邮箱 {self.username}")
            return True
        except Exception as e:
            logger.error(f"连接QQ邮箱失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("已断开与QQ邮箱的连接")
            except Exception as e:
                logger.error(f"断开连接时发生错误: {e}")

    def check_connection(self):
        """检查连接是否仍然有效"""
        try:
            # 发送一个简单的NOOP命令来检查连接状态
            status, _ = self.connection.noop()
            return status == 'OK'
        except Exception:
            return False

    def reconnect_if_needed(self):
        """如果需要，重新建立连接"""
        if not self.check_connection():
            logger.warning("连接已断开，尝试重新连接...")
            self.disconnect()
            time.sleep(5)  # 等待5秒再重试
            return self.connect()
        return True

    def fetch_unread_emails(self):
        """获取所有未读邮件"""
        try:
            # 确保连接有效
            if not self.reconnect_if_needed():
                return []
                
            status, messages = self.connection.search(None, 'UNSEEN')
            if status != 'OK':
                logger.warning("搜索未读邮件失败")
                return []

            email_ids = messages[0].split()
            email_list = []
            
            for email_id in email_ids:
                status, data = self.connection.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    msg = email.message_from_bytes(data[0][1])
                    email_list.append((email_id, msg))
            
            return email_list
        except Exception as e:
            logger.error(f"获取未读邮件失败: {e}")
            return []

    def parse_email(self, msg):
        """
        解析邮件，提取发件人、主题和文本正文
        :return: (from_address, subject, body_text)
        """
        # 解析发件人
        from_str = msg.get('From', '')
        email_address = re.findall(r'<(.+?)>', from_str)
        from_address = email_address[0].lower() if email_address else from_str.lower()

        # 解析主题
        subject, encoding = decode_header(msg.get('Subject', ''))[0]
        if isinstance(subject, bytes):
            try:
                subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
            except:
                subject = subject.decode('utf-8', errors='ignore')
        subject = str(subject).strip()

        # 解析正文
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                    
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    try:
                        body_text = payload.decode('utf-8', errors='ignore')
                    except:
                        try:
                            body_text = payload.decode('gbk', errors='ignore')
                        except:
                            body_text = payload.decode('iso-8859-1', errors='ignore')
                    break
        else:
            payload = msg.get_payload(decode=True)
            try:
                body_text = payload.decode('utf-8', errors='ignore')
            except:
                try:
                    body_text = payload.decode('gbk', errors='ignore')
                except:
                    body_text = payload.decode('iso-8859-1', errors='ignore')
        
        body_text = body_text.strip() if body_text else ''
        return from_address, subject, body_text

    def is_valid_command(self, from_address, body):
        """
        验证是否是有效的命令
        :return: 匹配对象（如果有效）或None
        """
        # 检查发件人
        if self.allowed_sender and from_address != self.allowed_sender:
            logger.warning(f"收到来自未授权发件人 {from_address} 的邮件，已忽略")
            return None
        
        # 检查正文是否符合命令格式
        match = self.command_pattern.match(body)
        if not match:
            logger.warning(f"收到来自 {from_address} 的邮件，但正文格式不符: '{body}'")
            return None
            
        return match

    def process_command(self, command_match):
        """
        处理识别出的命令
        """
        number = command_match.group(1)
        command_str = command_match.group(0).strip()
        logger.info(f"执行命令: {command_str}")
        
        # 在这里执行你的操作
        print(f"Received command: '{command_str}'. Executing action...")
        # 示例操作 - 替换为你的实际逻辑
        time.sleep(0.1)  # 模拟短暂延迟
        print(f"Action for '{command_str}' completed.")
        
    def mark_as_read(self, email_id):
        """将邮件标记为已读"""
        try:
            # 确保连接有效
            if not self.reconnect_if_needed():
                return
                
            self.connection.store(email_id, '+FLAGS', '\\Seen')
            logger.debug(f"已标记邮件 {email_id} 为已读")
        except Exception as e:
            logger.error(f"标记邮件为已读失败: {e}")

    def run_with_polling(self, poll_interval=10):
        """
        使用轮询模式运行监听
        :param poll_interval: 轮询间隔时间（秒）
        """
        if not self.connect():
            return
            
        self.running = True
        logger.info(f"开始轮询QQ邮箱，检查间隔 {poll_interval} 秒...")
        
        try:
            while self.running:
                # 处理邮件
                self.process_emails()
                
                # 等待下一次检查
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("用户中断监听")
        except Exception as e:
            logger.error(f"轮询过程中发生错误: {e}")
        finally:
            self.running = False
            self.disconnect()

    def process_emails(self):
        """处理所有未读邮件"""
        try:
            unread_emails = self.fetch_unread_emails()
            if not unread_emails:
                return
                
            logger.info(f"发现 {len(unread_emails)} 封未读邮件")
            processed_commands = 0
            
            for email_id, msg in unread_emails:
                from_address, subject, body = self.parse_email(msg)
                
                # 使用安全字符串处理，避免编码错误
                safe_from = safe_string(from_address)
                safe_subject = safe_string(subject)
                
                logger.info(f"新邮件 - 发件人: {safe_from}, 主题: {safe_subject}")
                
                # 检查是否是有效命令
                command_match = self.is_valid_command(from_address, body)
                if command_match:
                    self.process_command(command_match)
                    processed_commands += 1
                
                # 标记为已读，避免重复处理
                self.mark_as_read(email_id)
                
            if processed_commands > 0:
                logger.info(f"本轮处理了 {processed_commands} 个命令")
                
        except Exception as e:
            logger.error(f"处理邮件时发生错误: {e}")

    def stop(self):
        """停止监听"""
        self.running = False


# 主程序
if __name__ == "__main__":
    # 配置你的QQ邮箱信息
    QQ_EMAIL = 'your_qq_number@qq.com'  # 替换为你的QQ邮箱
    QQ_AUTH_CODE = 'your_authorization_code'  # 替换为你的授权码
    ALLOWED_SENDER = 'sender_email@example.com'  # 允许发送命令的邮箱地址
    
    # 创建客户端实例
    client = QQMailCommandClient(
        username=QQ_EMAIL,
        password=QQ_AUTH_CODE,
        allowed_sender=ALLOWED_SENDER
    )
    
    # 直接使用轮询模式
    try:
        # 使用较短的轮询间隔（10秒）以降低延迟
        client.run_with_polling(poll_interval=0.5)
    except Exception as e:
        logger.error(f"程序运行失败: {e}")