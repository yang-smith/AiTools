from collections import deque
from typing import Optional, List, Dict
import tiktoken

class ConversationManager:
    def __init__(self, *, max_tokens: int = 1000, model: str = "gpt-4o", system_prompt: str = None):
        """
        初始化对话管理器
        Args:
            max_tokens: 最大token数量
            model: 使用的模型名称
            system_prompt: 系统提示词
        """
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model('gpt-4o')
        self.messages = deque()
        
        # 如果有system prompt，添加到消息队列开头
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到对话历史
        Args:
            role: 消息角色 (system/user/assistant)
            content: 消息内容
        """
        if not content.strip():  # 忽略空消息
            return
            
        self.messages.append({
            "role": role,
            "content": content
        })
        self._trim_conversation()

    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有对话历史"""
        return list(self.messages)

    def clear(self) -> None:
        """清空对话历史，保留system prompt"""
        system_message = next((msg for msg in self.messages if msg["role"] == "system"), None)
        self.messages.clear()
        if system_message:
            self.messages.append(system_message)

    def _trim_conversation(self) -> None:
        """如果对话超出token限制，从最早的非system消息开始删除"""
        while self._count_tokens() > self.max_tokens and len(self.messages) > 1:
            # 如果第一条是system消息，从第二条开始删除
            if self.messages[0]["role"] == "system":
                self.messages.rotate(-1)  # 将system消息移到末尾
                self.messages.popleft()   # 删除最早的非system消息
                self.messages.rotate(1)   # 将system消息移回开头
            else:
                self.messages.popleft()

    def _count_tokens(self) -> int:
        """计算当前对话历史的总token数"""
        return sum(len(self.encoding.encode(msg["content"])) for msg in self.messages)

    def get_context(self, max_context_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取在token限制内的最近对话历史
        Args:
            max_context_tokens: 可选的最大上下文token数
        Returns:
            符合token限制的对话历史列表
        """
        max_tokens = max_context_tokens or self.max_tokens
        context = []
        token_count = 0

        # 确保system message总是在开头
        system_message = next((msg for msg in self.messages if msg["role"] == "system"), None)
        if system_message:
            system_tokens = len(self.encoding.encode(system_message["content"]))
            if system_tokens <= max_tokens:
                context.append(system_message)
                token_count += system_tokens

        # 添加其他消息
        for message in reversed(list(msg for msg in self.messages if msg["role"] != "system")):
            message_tokens = len(self.encoding.encode(message["content"]))
            if token_count + message_tokens > max_tokens:
                break
            if message["role"] != "system":  # 避免重复添加system消息
                context.insert(1 if system_message else 0, message)
                token_count += message_tokens

        return context