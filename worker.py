from utils.ai_chat_client import ai_chat
from memory_manager import ConversationManager


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

if __name__ == "__main__":
    # 创建一个Worker实例
    import prompt
    tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_summary_report",
                    "description": "当信息收集完成时，生成一份总结报告",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "总结报告"
                            }
                        },
                        "required": ["summary"]
                    }
                }
            }
        ]
    worker = Worker(
        description="测试工作者",
        system_prompt=prompt.PROMPT_GET_TASK_INFO,
        model="gpt-4o",
        tools=tools
    )
    
    # 创建一个Worker实例后，添加交互式循环
    print("欢迎使用AI助手！输入 'quit' 或 'exit' 退出程序")
    while True:
        # 获取用户输入
        user_input = input("\n请输入您的问题: ").strip()
        
        # 检查是否退出
        if user_input.lower() in ['quit', 'exit']:
            print("感谢使用，再见！")
            break
            
        # 如果输入不为空，则处理请求
        if user_input:
            result = worker.run(user_input)
            print("\n获得回答:", result)
        else:
            print("输入不能为空，请重新输入")
    
