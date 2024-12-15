const PROMPT_GENERATE_TRUTHS = `You are a professional data analyst and truth extraction expert, skilled at identifying and extracting key facts from complex data.

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
3. List similar truths with slight differences separately`;

async function testPrompt(inputData) {
    const promptWithInput = PROMPT_GENERATE_TRUTHS.replace("{input_data}", inputData);
    try {
        const response = await fetch("https://api.red-pill.ai/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": "Bearer <YOUR-REDPILL-API-KEY>",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": promptWithInput
                    }
                ]
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Response:", data);
        return data;

    } catch (error) {
        console.error("Error:", error);
        throw error;
    }
}

// Example usage
const testData = `
Sample data point 1: User activity logged at 2024-03-15 14:30:00
Sample data point 2: System performance metrics show 95% uptime
Sample data point 3: User feedback rating: 4.5/5
`;

testPrompt(testData)
    .then(result => {
        console.log("Analysis complete");
        console.log("Response message:", result.choices[0].message.content);
    })
    .catch(error => console.error("Analysis failed:", error));