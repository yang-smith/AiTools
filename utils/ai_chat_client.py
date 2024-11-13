import os
import httpx
import tiktoken
import asyncio
from aiolimiter import AsyncLimiter
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import json

load_dotenv()
# 常量配置
DEFAULT_TEMPERATURE = 0.05
DEFAULT_SYSTEM_MESSAGE = "You are a helpful assistant."
RATE_LIMITER = AsyncLimiter(4, 1)  # 4 requests per second

def _get_client(model: str, is_async: bool = False) -> OpenAI | AsyncOpenAI:
    """Return appropriate OpenAI client based on model and type."""
    client_class = AsyncOpenAI if is_async else OpenAI
    
    if model == 'deepseek-chat':
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("DEEPSEEK_API_BASE")
        if not api_key or not base_url:
            raise ValueError(
                "Missing required environment variables for Deepseek: "
                "DEEPSEEK_API_KEY and DEEPSEEK_API_BASE must be set"
            )
        return client_class(api_key=api_key, base_url=base_url)
    
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_API_BASE")
    if not api_key:
        raise ValueError("Missing required environment variable: OPENAI_API_KEY")
    
    return client_class(
        api_key=api_key,
        base_url=base_url or "https://api.openai.com/v1"
    )

def _prepare_messages(message, system_message: str = DEFAULT_SYSTEM_MESSAGE):
    """Prepare messages for chat completion."""
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": message}
    ]

async def ai_chat_async(message, model="gpt-4o-mini", response_format='NOT_GIVEN', retries=3):
    timeout = httpx.Timeout(20.0, read=50.0)  
    async with httpx.AsyncClient(timeout=timeout) as client:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message}
        ]

        params = {
            "messages": messages,
            "model": model,
            "temperature": 0.05,
        }

        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"
        }

        if response_format == 'json':
            params["response_format"] = {"type": "json_object"}

        url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1") + "/chat/completions"

        for attempt in range(retries + 1):
            try:
                # 使用速率限制
                async with RATE_LIMITER:
                    response = await client.post(url, json=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # 处理请求过多的情况
                    await asyncio.sleep((2 ** attempt) * 60)  # 指数级退避
                elif e.response.status_code >= 500:  # 处理服务器错误
                    await asyncio.sleep(2 ** attempt)  # 短暂退避
                else:
                    raise  # 其他错误不重试
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # 网络问题的指数级退避
                else:
                    raise  

def ai_chat(message: str | list, model: str = "gpt-4o-mini", response_format: str = 'NOT_GIVEN', tools: list = None) -> str:
    """
    Synchronous chat completion using OpenAI API.
    
    Args:
        message: User message (str) or full messages list
        model: Model to use for completion
        response_format: Optional response format (e.g., 'json')
        tools: Optional list of function definitions for function calling
    
    Returns:
        str: AI response content
    """
    client = _get_client(model)
    messages = message if isinstance(message, list) else _prepare_messages(message)
    
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": DEFAULT_TEMPERATURE
    }
    
    if response_format == 'json':
        kwargs["response_format"] = {"type": "json_object"}
    
    # 添加 function calling 支持
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    
    chat_completion = client.chat.completions.create(**kwargs)
    
    # 处理函数调用响应
    response_message = chat_completion.choices[0].message
    
    # 检查是否有函数调用
    if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
        tool_call = response_message.tool_calls[0]  # 获取第一个工具调用
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # 返回函数调用的结果
        return json.dumps({
            "function_call": {
                "name": function_name,
                "arguments": function_args
            }
        })
    
    return response_message.content

async def ai_chat_AsyncOpenAI(message: str, model: str = "gpt-3.5-turbo", 
                            response_format: str = 'NOT_GIVEN') -> str:
    """Asynchronous chat completion using AsyncOpenAI client."""
    client = _get_client(model, is_async=True)
    messages = _prepare_messages(message)
    
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": DEFAULT_TEMPERATURE
    }
    
    if response_format == 'json':
        kwargs["response_format"] = {"type": "json_object"}
    
    async with client as aclient:
        chat_completion = await aclient.chat.completions.create(**kwargs)
    
    return chat_completion.choices[0].message.content

# Token handling utilities
def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))

def truncate_list_by_token_size(list_data: list, max_token_size: int) -> list:
    """
    Truncate a list of data by token size.
    
    Args:
        list_data: List of strings to truncate
        max_token_size: Maximum allowed tokens
    
    Returns:
        list: Truncated list
    """
    tokens = 0
    for i, data in enumerate(list_data):
        tokens += num_tokens_from_string(data)
        if tokens > max_token_size:
            return list_data[:i]
    return list_data
