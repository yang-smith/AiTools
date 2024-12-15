from utils.ai_chat_client import ai_chat
from memory_manager import ConversationManager
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from tqdm import tqdm
import prompt_record2doc
import os 

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

def gen_structure(user_input, chat_records):
    structure_file = 'output/document_structure.txt'
    
    # 如果结构文件已存在，直接读取内容
    if os.path.exists(structure_file):
        with open(structure_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 如果文件不存在，生成新的结构
    combined_input = prompt_record2doc.PROMPT_GEN_DOC_STRUCTURE.format(user_input=user_input, chat_records=chat_records)

    result = ai_chat(message=combined_input, model="anthropic/claude-3.5-sonnet:beta")
    # result = ai_chat(message=combined_input, model="openai/gpt-4o-2024-11-20")
    print(result)
    
    # 确保输出目录存在并保存结果
    os.makedirs('output', exist_ok=True)
    with open(structure_file, 'w', encoding='utf-8') as f:
        f.write(result)
        f.write('\n')
    return result

def process_single_task(task_num, task, chat_records, output_path='output'):
    # 确保输出目录存在
    os.makedirs(output_path, exist_ok=True)
    
    prompt_gen_doc_content = prompt_record2doc.PROMPT_GEN_DOC_CONTENT.format(task_instruction=task, chat_records=chat_records)
    # 获取并保存 gpt-4o-mini 的结果
    gpt4_result = ai_chat(message=prompt_gen_doc_content, model="openai/gpt-4o-mini-2024-07-18")
    with open(f'{output_path}/result_task_{task_num}.md', 'a', encoding='utf-8') as f:
        f.write(gpt4_result)
        f.write('<page_end> \n')
    
    return task_num, gpt4_result


def merge_chapter_results(results: list[str]) -> str:
    """
    合并多个结果，按章节组织内容
    """
    # 用于存储每个章节的内容
    chapter_contents = {}
    
    for result in results:
        # 提取 info_start 和 info_end 之间的内容
        pattern = r'<info_start>(.*?)<info_end>'
        match = re.search(pattern, result, re.DOTALL)
        if not match:
            continue
            
        content = match.group(1).strip()
        
        # 按章节分割内容
        chapters = re.split(r'\n(?=[\d一二三四五六七八九十]+、)', content)
        
        for chapter in chapters:
            if not chapter.strip():
                continue
                
            # 提取章节标题
            chapter_title = chapter.split('\n')[0].strip()
            chapter_content = '\n'.join(chapter.split('\n')[1:]).strip()
            
            if chapter_title not in chapter_contents:
                chapter_contents[chapter_title] = []
            
            # 将内容分成独立的条目
            items = [item.strip() for item in chapter_content.split('\n') if item.strip()]
            chapter_contents[chapter_title].extend(items)
    
    # 组合最终结果
    merged_content = ['<info_start>']
    for title, items in chapter_contents.items():
        # 去重并保持顺序
        unique_items = list(dict.fromkeys(items))
        merged_content.append(f"{title}\n{chr(10).join(unique_items)}\n")
    merged_content.append('<info_end>')
    
    return '\n'.join(merged_content)

def test_update_doc():
    with open('DNyucun.txt', 'r', encoding='utf-8') as file:
        chat_text = file.read()
    segments = split_chat_records(chat_text, max_messages=1300, min_messages=1000, time_gap_minutes=100)
    
    # 打印总段数
    print(f"聊天记录被分割成 {len(segments)} 个部分\n")
    
    chat_records = segments[0]

    # user_input = "将聊天记录转为一份常见问答文档"
    user_input = "将聊天记录转为一份社区生活指南"
    result = gen_structure(user_input, chat_records)

    # tasks = split_tasks(result)
    pattern = r'<outline>\s*(.*?)\s*</outline>'
    match = re.search(pattern, result, re.DOTALL)
    if match:
        task = match.group(1).strip()
    else:
        task = result

    # 定义一个处理单个 segment 的函数
    def process_segment(segment):
        prompt_gen_doc_content = prompt_record2doc.PROMPT_GET_INFO.format(
            outline=task, 
            chat_records=segment
        )
        return ai_chat(
            message=prompt_gen_doc_content, 
            model="openai/gpt-4o-mini-2024-07-18"
        )

    all_results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        # 提交所有任务
        future_to_segment = {
            executor.submit(process_segment, segment): i 
            for i, segment in enumerate(segments)
        }
        
        # 使用 tqdm 显示进度
        for future in tqdm(
            concurrent.futures.as_completed(future_to_segment),
            total=len(future_to_segment),
            desc="Processing segments"
        ):
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                print(f"Segment processing failed: {str(e)}")


    # 合并结果
    merged_result = merge_chapter_results(all_results)
    print(merged_result)

    pattern = r'<info_start>(.*?)<info_end>'
    match = re.search(pattern, merged_result, re.DOTALL)
    if match:
        content = match.group(1).strip()
        chapters = re.split(r'\n(?=[\d一二三四五六七八九十]+、)', content)
    else:
        chapters = []

    print(chapters)

    # Process each chapter in parallel
    def process_chapter(chapter_content):
        return ai_chat(
            message=prompt_record2doc.PROMPT_GEN_END_DOC.format(
                outline=result,
                aggregated_info=f"<info_start>\n{chapter_content}\n<info_end>"
            ),
            model="openai/gpt-4o-mini-2024-07-18"
        )

    indexed_results = []
    with ThreadPoolExecutor(max_workers=len(chapters)) as executor:
        future_to_chapter = {
            executor.submit(process_chapter, chapter): i
            for i, chapter in enumerate(chapters) if chapter.strip()
        }

        for future in tqdm(
            concurrent.futures.as_completed(future_to_chapter),
            total=len(future_to_chapter),
            desc="Processing chapters"
        ):
            try:
                chapter_result = future.result()
                # 保存结果和对应的索引
                chapter_index = future_to_chapter[future]
                indexed_results.append((chapter_index, chapter_result))
            except Exception as e:
                print(f"Chapter processing failed: {str(e)}")

    # 按照原始索引排序并合并结果
    final_document = '\n\n'.join(
        result for _, result in sorted(indexed_results, key=lambda x: x[0])
    )
    # 去掉 <content> 标记
    cleaned_document = re.sub(r'<content>\s*|\s*</content>', '', final_document)
    
    # 写入文件
    output_file = 'output/final_document.md'
    os.makedirs('output', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_document)
    
    print(f"文档已保存到: {output_file}")




if __name__ == "__main__":
    
    test_update_doc()
    # main()
