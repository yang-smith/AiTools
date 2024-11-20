from utils.ai_chat_client import ai_chat, ai_chat_async
from prompt import PROMPT_PDF2TXT
import re
import asyncio
from typing import List, Dict, Optional
from tqdm import tqdm
import json
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures


def split_pages(text):
    """Split text into pages based on page markers."""
    # 使用正则表达式匹配页码标记 ≦ xxx ≧
    pattern = r'≦\s*(\d+)\s*≧'
    
    # 分割文本
    pages = re.split(pattern, text)
    
    # 移除空字符串和处理页码
    result = []
    page_num = 1  # 从1开始按顺序编号
    
    # pages[0] 是文本开始到第一个页码标记之前的内容（如果存在）
    # 如果第一部分有内容，将其作为第1页
    if pages[0].strip():
        result.append({
            'page': page_num,
            'content': pages[0].strip()
        })
        page_num += 1
    
    # 处理剩余的页面
    for i in range(2, len(pages), 2):
        content = pages[i].strip()
        if content:
            result.append({
                'page': page_num,
                'content': content
            })
            page_num += 1
    
    return result

def read_txt_file(file_path="needs.txt"):
    """Read text content from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return None

def extract_markdown_content(text):
    """Extract markdown content from AI response."""
    try:
        print(text)
        data = json.loads(text)
        return data.get('formatted_content', '')

    except Exception as e:
        print(f"Error extracting markdown content: {str(e)}")
        return ''
    return ''

def process_single_page(page_data: dict) -> tuple[int, str]:
    """Process a single page."""
    try:
        prompt = PROMPT_PDF2TXT.format(page_data['content'])
        result = ai_chat(prompt, model="gpt-4o-mini", response_format="json") 
        markdown_content = extract_markdown_content(result)
        return page_data['page'], markdown_content
    except Exception as e:
        print(f"Error processing page {page_data['page']}: {str(e)}")
        return page_data['page'], ""

def process_pdf_text(content: str, max_workers: int = 3) -> Dict[int, str]:
    """Process PDF text using thread pool."""
    contents = split_pages(content)
    # 合并前9页内容
    if len(contents) >= 9:
        combined_content = {
            'page': 1,
            'content': ' '.join(doc['content'] for doc in contents[:9])
        }
        contents = [combined_content] + contents[9:]
   
    contents = contents[100:]

    all_pages: Dict[int, str] = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_page = {
            executor.submit(process_single_page, doc): doc['page'] 
            for doc in contents
        }
        
        # 使用 tqdm 显示进度
        for future in tqdm(
            concurrent.futures.as_completed(future_to_page),
            total=len(contents),
            desc="Processing pages"
        ):
            try:
                page, result = future.result()
                all_pages[page] = result
            except Exception as e:
                print(f"Task failed: {str(e)}")
                
    return dict(sorted(all_pages.items()))  # 返回按页码排序的结果

def write_to_markdown(content: Dict[int, str], output_file: str = "merged_content.md") -> None:
    """Write content to a markdown file with page numbers.
    
    Args:
        content: Dictionary with page numbers as keys and content as values
        output_file: The output file path, defaults to 'merged_content.md'
    """
    try:
        with open(output_file, 'a', encoding='utf-8') as file:
            # Sort pages by page number and write content
            for page_num in sorted(content.keys()):
                file.write(f"{content[page_num]}\n")
    except Exception as e:
        print(f"Error writing to file: {str(e)}")
        raise
    

def main():
    """Main function to process the text file."""
    try:
        content = read_txt_file()
        if content is None:
            return
        
        results = process_pdf_text(content)
        print(sorted(results.keys()))
        write_to_markdown(results)
        print("\nProcessing complete. Results saved to 'merged_content.md'")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()




