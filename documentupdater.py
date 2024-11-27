from enum import Enum
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import re
from concurrent.futures import ThreadPoolExecutor
import hashlib
from datetime import datetime
from utils.ai_chat_client import ai_chat

class UpdateType(Enum):
    INSERT = "INSERT"
    DELETE = "DELETE"
    REPLACE = "REPLACE"
    MOVE = "MOVE"

@dataclass
class UpdateOperation:
    """文档更新操作"""
    type: UpdateType
    selector: str  # Markdown选择器
    content: Optional[str] = None
    new_selector: Optional[str] = None  # 用于MOVE操作
    reason: Optional[str] = None
    timestamp: str = datetime.now().isoformat()
    
@dataclass
class UpdateResult:
    """更新结果"""
    success: bool
    content: str
    operation_hash: str
    error: Optional[str] = None



class MarkdownSelector:
    """Markdown选择器解析和匹配"""
    
    @staticmethod
    def parse_selector(selector: str) -> List[Dict]:
        """解析选择器字符串为结构化数据"""
        parts = selector.split('>')
        parsed = []
        
        for part in parts:
            part = part.strip()
            data = {'raw': part}
            
            # 解析属性
            if '[' in part and ']' in part:
                attrs = re.findall(r'\[(.*?)\]', part)
                data['attributes'] = {}
                for attr in attrs:
                    key, value = attr.split('=')
                    data['attributes'][key] = value
                part = re.sub(r'\[.*?\]', '', part)
            
            # 解析nth选择器
            if ':nth(' in part:
                nth = re.search(r':nth\((\d+)\)', part)
                if nth:
                    data['nth'] = int(nth.group(1))
                part = re.sub(r':nth\(\d+\)', '', part)
            
            # 解析关键词匹配
            if '{' in part and '}' in part:
                keyword = re.search(r'\{(.*?)\}', part)
                if keyword:
                    data['keyword'] = keyword.group(1)
                part = re.sub(r'\{.*?\}', '', part)
            
            data['element'] = part.strip()
            parsed.append(data)
            
        return parsed

    @staticmethod
    def find_element(content: str, selector: List[Dict]) -> tuple[int, int]:
        """在文档中查找选择器匹配的元素位置"""
        lines = content.split('\n')
        current_level = 0
        current_match = None
        
        for i, line in enumerate(lines):
            # 检查每一级选择器
            if current_level < len(selector):
                sel = selector[current_level]
                
                # 检查元素类型
                if sel['element'] in line:
                    # 检查属性
                    if 'attributes' in sel:
                        matches = True
                        for key, value in sel['attributes'].items():
                            if f'[{key}={value}]' not in line:
                                matches = False
                                break
                        if not matches:
                            continue
                    
                    # 检查关键词
                    if 'keyword' in sel and sel['keyword'] not in line:
                        continue
                    
                    # 检查nth
                    if 'nth' in sel:
                        # 计算同级元素
                        count = 1
                        for prev_line in lines[:i]:
                            if prev_line.startswith(sel['element']):
                                count += 1
                        if count != sel['nth']:
                            continue
                    
                    current_level += 1
                    current_match = i
                    
                    # 找到完整匹配
                    if current_level == len(selector):
                        # 查找元素的结束位置
                        end = i + 1
                        while end < len(lines) and lines[end].startswith(sel['element']):
                            end += 1
                        return current_match, end
        
        raise ValueError(f"Cannot find element matching selector: {selector}")

class DocumentUpdater:
    """文档更新系统"""
    
    @staticmethod
    def parse_ai_response(response: str) -> List[UpdateOperation]:
        """解析AI响应为操作序列"""
        operations = []
        
        # 提取更新块
        updates_match = re.search(r'<UPDATES>(.*?)</UPDATES>', response, re.DOTALL)
        if not updates_match:
            raise ValueError("No valid updates found in AI response")
            
        updates_text = updates_match.group(1)
        
        # 解析每个操作
        operation_blocks = re.split(r'\[操作\d+\]', updates_text)
        for block in operation_blocks:
            if not block.strip():
                continue
                
            # 解析操作属性
            type_match = re.search(r'TYPE: (\w+)', block)
            selector_match = re.search(r'SELECTOR: (.+?)(?=\n)', block)
            content_match = re.search(r'CONTENT: (.+?)(?=\n|$)', block)
            new_selector_match = re.search(r'NEW_SELECTOR: (.+?)(?=\n)', block)
            reason_match = re.search(r'REASON: (.+?)(?=\n|$)', block)
            
            if not (type_match and selector_match):
                continue
                
            operations.append(UpdateOperation(
                type=UpdateType[type_match.group(1)],
                selector=selector_match.group(1),
                content=content_match.group(1) if content_match else None,
                new_selector=new_selector_match.group(1) if new_selector_match else None,
                reason=reason_match.group(1) if reason_match else None
            ))
            
        return operations

    @staticmethod
    def apply_operation(content: str, operation: UpdateOperation) -> str:
        """应用单个更新操作"""
        lines = content.split('\n')
        selector = MarkdownSelector.parse_selector(operation.selector)
        
        try:
            start, end = MarkdownSelector.find_element(content, selector)
            
            if operation.type == UpdateType.INSERT:
                lines.insert(start, operation.content)
            elif operation.type == UpdateType.DELETE:
                lines.pop(start)
            elif operation.type == UpdateType.REPLACE:
                lines[start] = operation.content
            elif operation.type == UpdateType.MOVE:
                # 保存要移动的内容
                moving_content = lines[start]
                # 删除原位置的内容
                lines.pop(start)
                # 找到新位置
                new_selector = MarkdownSelector.parse_selector(operation.new_selector)
                new_start, _ = MarkdownSelector.find_element(content, new_selector)
                # 在新位置插入
                lines.insert(new_start, moving_content)
                
            return '\n'.join(lines)
        except Exception as e:
            raise ValueError(f"Failed to apply operation: {str(e)}")

    @staticmethod
    def update_document(content: str, operations: List[UpdateOperation]) -> UpdateResult:
        """应用更新操作序列"""
        try:
            updated_content = content
            # 计算操作序列的哈希值
            ops_hash = hashlib.sha256(
                '\n'.join(str(op) for op in operations).encode()
            ).hexdigest()
            
            # 依次应用每个操作
            for op in operations:
                updated_content = DocumentUpdater.apply_operation(
                    updated_content, op
                )
                
            return UpdateResult(
                success=True,
                content=updated_content,
                operation_hash=ops_hash
            )
        except Exception as e:
            return UpdateResult(
                success=False,
                content=content,
                operation_hash='',
                error=str(e)
            )

def update_document_with_ai(
    current_doc: str,
    new_chats: str,
    task_instruction: str
) -> UpdateResult:
    """完整的AI文档更新流程"""
    try:
        # 1. 调用AI获取更新建议
        ai_response = call_ai_api(PROMPT_DOC_UPDATER.format(
            base_document=current_doc,
            new_chat_records=new_chats,
            task_instruction=task_instruction
        ))
        
        # 2. 解析AI响应
        operations = DocumentUpdater.parse_ai_response(ai_response)
        
        # 3. 应用更新操作
        return DocumentUpdater.update_document(current_doc, operations)
        
    except Exception as e:
        return UpdateResult(
            success=False,
            content=current_doc,
            operation_hash='',
            error=str(e)
        )

# 使用示例
def test_document_updater():
    original_doc = """# 产品文档
    
## 产品特性
### 基础功能
- 高性能：支持快速处理
- 易用性：简单直观的操作界面
- 可靠性：稳定运行

### 高级功能
- 数据分析
- 报表导出
"""

    # 模拟AI响应
    ai_response = """<UPDATES>
[操作1]
TYPE: REPLACE
SELECTOR: ## 产品特性 > ### 基础功能 > - {高性能}
CONTENT: - 超高性能：支持每秒处理100万请求
REASON: 更新了具体的性能指标

[操作2]
TYPE: INSERT
SELECTOR: ## 产品特性 > ### 高级功能
CONTENT: - 智能推荐：基于AI的个性化推荐
REASON: 添加了新的AI功能特性
</UPDATES>
"""

    # 解析并应用更新
    operations = DocumentUpdater.parse_ai_response(ai_response)
    result = DocumentUpdater.update_document(original_doc, operations)
    
    print("Update success:", result.success)
    if result.success:
        print("\nUpdated document:")
        print(result.content)
    else:
        print("\nUpdate failed:", result.error)

if __name__ == "__main__":
    test_document_updater()