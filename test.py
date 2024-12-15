import requests
import json

PROMPT_GENERATE_TRUTHS = """
You are a professional data analyst and truth extraction expert, skilled at identifying and extracting key facts from complex data.

# Input Data
{input_data}

# Thought Process
1. Data Analysis
   - Identify the type and structure of the data
   - Determine the credibility of the data
   - Mark key information points and patterns

2. Pattern Recognition
   - Look for repeating patterns in the data
   - Identify outliers and special cases
   - Establish relationships between data points

3. Truth Extraction
   - Derive facts based on evidence
   - Distinguish between certain and speculative conclusions
   - Verify the consistency of the truths

4. Cross-Verification
   - Use multiple data points to verify each truth
   - Check the logical relationships between truths
   - Eliminate contradictory conclusions

5. Quality Check
   - Verify the reliability of each truth
   - Ensure accuracy and objectivity in expression
   - Check for over-interpretation

# Extraction Requirements
1. Truth Standards
   - Must be clearly supported by data
   - Avoid subjective judgments and speculation
   - Use precise and neutral language

2. Completeness Requirements
   - Include key information on time, place, and objects
   - Clearly indicate the source of information
   - Indicate the level of confidence

3. Format Specifications
   - Each truth should be in a separate paragraph
   - Include supporting evidence
   - Indicate the confidence level

# Output Format
<truths_start>
truth: [Truth 1]
evidence: [Specific data supporting the truth]
confidence: [High/Medium/Low]
source: [Data location/number]

truth: [Truth 2]
evidence: [Specific data supporting the truth]
confidence: [High/Medium/Low]
source: [Data location/number]

...
<truths_end>

# Notes
1. Only output truths with sufficient evidence
2. Clearly mark uncertain inferences
3. List similar truths with slight differences separately
"""

# 需求，

def test_local_api():
    # 设置请求参数
    server_port = 3000
    agent_id = "07b6bf73-fe56-0327-ad9a-9be8fa688dc3"  # 替换为实际的agent_id
    
    # 构建URL
    url = f"http://localhost:{server_port}/{agent_id}/message"
    
    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    # 设置请求体数据
    payload = {
        "text": "测试消息",
        "userId": "user",
        "userName": "Usernponderingdemocritus"
    }
    
    try:
        # 发送POST请求
        response = requests.post(
            url=url,
            headers=headers,
            json=payload
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        # 打印响应结果
        print("状态码:", response.status_code)
        print("响应内容:", response.json())
        
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

if __name__ == "__main__":
    test_local_api()
