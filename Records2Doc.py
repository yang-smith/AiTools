from utils.ai_chat_client import ai_chat
from memory_manager import ConversationManager
from datetime import datetime
import re

class Worker:
    
    def __init__(self, 
                 description: str = "a worker that can do tasks",
                 system_prompt: str = "You are a worker that can do tasks",
                 model: str = "gpt-4-mini",
                 max_tokens: int = 2000,
                 tools: list = [],
                 ):
        self.description = description
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.tools = tools
        
        self.memory = ConversationManager(
            max_tokens=max_tokens,
            model=model,
            system_prompt=system_prompt
        )
    
    def handle_tool_call(self, tool_call: str):
        pass
    
    def run(self, task_info: str):
        self.memory.add_message("user", task_info)
        messages = self.memory.get_context()
        result = ai_chat(message=messages, model=self.model)
        self.memory.add_message("assistant", result)
        return result

def split_chat_records(chat_text, max_messages=500, min_messages=300, time_gap_minutes=100):
    """
    分割聊天记录
    
    参数:
    chat_text: 原始聊天记录文本
    max_messages: 每个片段最大消息数
    min_messages: 每个片段最小消息数（除最后一个片段外）
    time_gap_minutes: 判定为新会话的时间间隔（分钟）
    
    返回:
    list of str: 分割后的聊天记录片段列表
    """
    # 解析消息
    # 时间格式：2023-05-11 19:33:39
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*?)(?=\n\d{4}-\d{2}-\d{2}|\Z)'
    messages = re.findall(pattern, chat_text, re.DOTALL)
    
    if not messages:
        return []
    
    # 存储分割后的片段
    segments = []
    current_segment = []
    last_time = datetime.strptime(messages[0][0], '%Y-%m-%d %H:%M:%S')
    
    for i, (timestamp, content) in enumerate(messages):
        current_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        time_diff = (current_time - last_time).total_seconds() / 60
        
        # 判断是否需要分割
        should_split = False
        
        # 检查时间间隔和最小消息数要求
        if time_diff > time_gap_minutes and len(current_segment) >= min_messages:
            should_split = True
            
        # 检查消息数量
        if len(current_segment) >= max_messages:
            should_split = True
            
        if should_split and current_segment:
            segments.append('\n'.join(f"{t} {c}" for t, c in current_segment))
            current_segment = []
            
        current_segment.append((timestamp, content))
        last_time = current_time
    
    # 添加最后一个片段
    if current_segment:
        segments.append('\n'.join(f"{t} {c}" for t, c in current_segment))
    
    return segments

def read_chat_records(filename='ToAnotherCountry.txt', max_lines=300):
    """
    读取聊天记录文件的前N行并返回格式化的字符串
    
    Args:
        filename (str): 要读取的文件名
        max_lines (int): 要读取的最大行数
        
    Returns:
        str: 格式化的聊天记录字符串，如果出错则返回None
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = []
            for _ in range(max_lines):
                try:
                    line = next(file).strip()
                    if line:  # 只添加非空行
                        lines.append(line)
                except StopIteration:
                    break
            
            # 直接将所有行用换行符连接
            return '\n'.join(lines)
            
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{filename}'")
        return None
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
        return None

def segment_test():

    with open('ToAnotherCountry.txt', 'r', encoding='utf-8') as file:
        chat_text = file.read()
    segments = split_chat_records(chat_text)
    
    # 打印总段数
    print(f"聊天记录被分割成 {len(segments)} 个部分\n")

    # 打印分割结果
    for i, segment in enumerate(segments, 1):
        # 计算该片段中的消息数量（通过计算时间戳的数量）
        message_count = len(re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', segment))
        print(f"=== Segment {i} (包含 {message_count} 条消息) ===")
        print("\n")

def split_tasks(task_text: str) -> list[str]:
    """
    将任务说明文本分割成独立的任务字符串列表
    
    Args:
        task_text (str): 包含多个任务的文本
        
    Returns:
        list[str]: 任务字符串列表，每个字符串包含完整的任务描述
    """
    # 分割任务块并去掉第一个空元素
    tasks = task_text.split('<task_start>')[1:]
    
    # 处理每个任务块，去掉结束标记并清理空白
    parsed_tasks = [
        task.split('<task_end>')[0].strip()
        for task in tasks
        if task.strip()  # 只保留非空任务
    ]
    
    return parsed_tasks


def main():    
    import prompt_record2doc

    # with open('ToAnotherCountry.txt', 'r', encoding='utf-8') as file:
    with open('ToAnotherCountry.txt', 'r', encoding='utf-8') as file:
        chat_text = file.read()
    segments = split_chat_records(chat_text)
    
    # 打印总段数
    print(f"聊天记录被分割成 {len(segments)} 个部分\n")
    
    chat_records = segments[0]
    user_input = "将聊天记录转为一份常见问答文档"
    combined_input = prompt_record2doc.PROMPT_GEN_DOC_STRUCTURE.format(user_input=user_input, chat_records=chat_records)

    result = ai_chat(message=combined_input, model="anthropic/claude-3.5-sonnet:beta")
    print(result)

    # task_instruction = prompt_record2doc.PROMPT_GEN_TASK_INSTRUCTION.format(doc_structure=result)

    # result = ai_chat(message=task_instruction, model="anthropic/claude-3.5-sonnet:beta")

    tasks = split_tasks(result)
    for task in tasks:
        print("\n-----\n")
        print(task)
        
        prompt_gen_doc_content = prompt_record2doc.PROMPT_GEN_DOC_CONTENT.format(task_instruction=task, chat_records=chat_records)
        # 获取并保存 gpt-4o-mini 的结果
        gpt4_result = ai_chat(message=prompt_gen_doc_content, model="openai/gpt-4o-mini-2024-07-18")
        with open('result_gpt4o.md', 'a', encoding='utf-8') as f:
            f.write(gpt4_result)
    return 

    # 将结果转为文档
    prompt_gen_doc_content = prompt_record2doc.PROMPT_GEN_DOC_CONTENT.format(task_instruction=tasks[0], chat_records=chat_records)
    # 获取并保存 deepseek-chat 的结果
    deepseek_result = ai_chat(message=prompt_gen_doc_content, model="deepseek-chat")
    with open('result_deepseek.txt', 'a', encoding='utf-8') as f:
        f.write(deepseek_result)
    
    # 获取并保存 gpt-4o-mini 的结果
    gpt4_result = ai_chat(message=prompt_gen_doc_content, model="openai/gpt-4o-mini-2024-07-18")
    with open('result_gpt4o.txt', 'a', encoding='utf-8') as f:
        f.write(gpt4_result)
    
    # gpt4_result = ai_chat(message=prompt_gen_doc_content, model="gpt-4o-mini")
    # with open('result_gpt4o_yyds.txt', 'w', encoding='utf-8') as f:
    #     f.write(gpt4_result)

    print("Deepseek Chat 结果已保存到 result_deepseek.txt")
    print("GPT-4o-mini 结果已保存到 result_gpt4o.txt")



    # 创建一个Worker实例后，添加交互式循环
    # print("欢迎使用AI助手！输入 'quit' 或 'exit' 退出程序")
    
    # while True:
    #     # 获取用户输入
    #     user_input = input("\n请输入您的问题: ").strip()
        
    #     # 检查是否退出
    #     if user_input.lower() in ['quit', 'exit']:
    #         print("感谢使用，再见！")
    #         break
            
    #     # 如果输入不为空，则处理请求
    #     if user_input:
    #         combined_input = f"# 这是用户输入：{user_input}\n\n # 这是聊天记录：{chat_records}"
    #         print(combined_input)
    #         result = worker.run(combined_input)
    #         print("\n获得回答:", result)
    #     else:
    #         print("输入不能为空，请重新输入")
    

if __name__ == "__main__":
    # 创建一个Worker实例
    
    main()
