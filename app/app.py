import streamlit as st
import os
import openai  # Make sure to install OpenAI library as well
import semantic_kernel.connectors.ai.open_ai as sk_oai
from semantic_kernel.utils.settings import azure_openai_settings_from_dot_env_as_dict
from dotenv import load_dotenv
# from weather import weather_report
from streamlit_extras.add_vertical_space import add_vertical_space
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
import requests
import asyncio

# Load environment variables if needed
load_dotenv()

kernel = sk.Kernel()

bing_search_api_key = os.getenv('BING_SEARCH_API_KEY') # Create an Azure Bing Search V7, this is the Keys of the resource
bing_search_endpoint = os.getenv('BING_SEARCH_ENDPOINT') # To filter top output, just simply add ?count=5 after /search, or you can put in the params in search function

deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()
kernel.add_chat_service("chat_completion", AzureChatCompletion(deployment, endpoint, api_key))

# Sidebar contents
with st.sidebar:
    st.title('🤗💬 Health Assistant')
    st.markdown("""
        <style>
               .st-emotion-cache-10oheav {
                    padding-top: 3rem;
                    padding-bottom: 3rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
        </style>
        """, unsafe_allow_html=True)
    st.markdown('''
    ## Hello and welcome! 🌟
    I can help you with your health issues. 
    ''')
    add_vertical_space(3)

    st.write('Made by Rackspace')

def search(problem):
    # Construct a request
    mkt = 'en-US' 
    customconfig = os.getenv('CUSTOM_CONFIG') # Go to this website to create list of websites you only want in the output: https://www.customsearch.ai/application/1820c32a-43aa-42c2-8a6c-09c0750cd7e3/staging/editor
    params = {'q': problem, 'customconfig': customconfig,'mkt': mkt}
    headers = {'Ocp-Apim-Subscription-Key': bing_search_api_key}

    # Call the API
    try:
        response = requests.get(bing_search_endpoint,
                                headers=headers, params=params)
        response.raise_for_status()
        json = response.json()
        return json["webPages"]["value"]
    except Exception as ex:
        raise ex

def create_prompt(problem):
    results = search("treatment of " + problem)
    results_prompts = [
        f"Source:\nTitle: {result['name']}\nURL: {result['url']}\nContent: {result['snippet']}" for result in results
    ]
    search_result = "\n\n".join(results_prompts)
    # weather_info = weather_report()
    sk_prompt = """
    You are a friendly and gentle AI assistant designed to assist with health concerns.

    Based on user issue {search_result} you will ask questions to clarify the issue.
    
    Do not ask 5 questions at the same time, you only ask 1 question each time.
    
    You can reference questions from this list:
        [1] What have you eaten or drunk in the last few hours?
        [2] Have you engaged in any physically strenuous activities today?
        [3] How have your stress levels been lately?
        [4] Respiratory symptoms, such as coughing, shortness of breath, or chest pain
        [5] Have you noticed any changes in your vision, hearing, or sense of smell?
        [6] Have you noticed any changes in your skin, such as rashes, itching, or discoloration?
        [7] Are there any significant changes in your stress levels or sleep patterns?
        [8] On a scale of 1 to 10, how would you rate the severity of your symptoms?
        [9] How has your sleep been recently? Any changes in your sleep schedule or disturbances?
        [10] Are you currently taking any medication or supplements?
        [11] Do you have any known allergies or have you been exposed to anything that might trigger an allergic reaction recently?
        [12] Have you been around anyone who's been ill lately, or have you had any exposure to contagious illnesses?
        [13] How much water have you been drinking lately?
        [14] Have you been exposed to extreme temperatures or any significant environmental changes?
        [15] Do you have any pre-existing medical conditions that might be related to your current symptoms?
    
    After a patient has described their symptoms, you have to recommend the most appropriate guidance to address user health issue using the following sources """ + search_result + """ 
    You will list the resources when answering.

    {{$chat_history}}
    user: {{$user_input}}
    assistant: 
    """

    # Initialize OpenAI API with your API key
    openai.api_key = os.getenv('AZURE_OPENAI_API_KEY')

    chat_service = sk_oai.AzureChatCompletion(
        **azure_openai_settings_from_dot_env_as_dict(include_api_version=True)
    )
    kernel.add_chat_service("chat-gpt", chat_service)

    prompt_config = sk.PromptTemplateConfig.from_completion_parameters(
        max_tokens=1000, temperature=0.002, top_p=0.4
    )

    prompt_template = sk.ChatPromptTemplate(
        sk_prompt, kernel.prompt_template_engine, prompt_config
    )

    function_config = sk.SemanticFunctionConfig(prompt_config, prompt_template)
    chat_function = kernel.register_semantic_function("ChatBot", "Chat", function_config)

    return chat_function

def turn_list_to_chat_history(list):
    s = ''
    for l in list:
        if l['role'] == 'assistant':
            content = l['content']
            s += f'\nassistant: {content}'
        elif l['role'] == 'user':
            content = l['content']
            s += f'\nuser: {content}'
    return s

async def chat_with_bot(problem):
    context_vars = sk.ContextVariables()
    if "messages" not in st.session_state.keys(): # Initialize the chat message history
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello, how can I assist you?"}
        ]
    if prompt := st.chat_input("Your question"): # Prompt for user input and save to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

    for message in st.session_state.messages: # Display the prior chat messages
        with st.chat_message(message["role"]):
            st.write(message["content"])

    context_vars["chat_history"] = turn_list_to_chat_history(st.session_state.messages)
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                context_vars["user_input"] = prompt
                answer = await kernel.run_async(create_prompt(problem), input_vars=context_vars)
                messages = {"role": "assistant", "content": str(answer)}
                st.session_state.messages.append(messages)
                st.write(str(answer))
                context_vars["chat_history"] = turn_list_to_chat_history(st.session_state.messages)

def main() -> None:
    id_input = st.sidebar.text_input('Please enter your ID: ')
    problem = st.sidebar.text_input('Please enter your problem: ')
    if "started_chat" not in st.session_state:
        st.session_state.started_chat = False
    if not st.session_state.started_chat and id_input and problem:
        if st.sidebar.button("Start chatting", key="start_button"):
            st.session_state.started_chat = True
    if st.session_state.started_chat:
        asyncio.run(chat_with_bot(problem))

if __name__ == "__main__":
    main()
