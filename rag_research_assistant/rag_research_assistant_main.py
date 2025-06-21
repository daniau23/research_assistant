import warnings
warnings.filterwarnings("ignore")
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
# Prompts and retriever
from langchain.prompts import PromptTemplate
from langchain.vectorstores import DeepLake
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereEmbeddings, \
    CohereRerank as langchain_cohere_reranker
import os
import time
from dotenv import load_dotenv

# loading .env
load_dotenv('../.env')

# The Prompt
def prompt():
    prompt_template_researcher = """
    As an NLP researcher with over 20 years of experience. Your knowledge of the NLP research space is highly respected by all.
    \nAlways answer the user's questions concisely and disregard any unuseful information by leveraging on the text provided.
    \nAlways be brief but highlight key and important information only; THIS IS VERY IMPORTANT!
    DO NOT REPEAT BUT BE IN DEPTH AND BRIEF. AT LEAST 5 bullet points where needed. For example:
    Question: Why did Mehedi Tajrian analyse child development and what was the best classifier?
    Answer:
        -
        -
        -
        -
        -
    \nIf Bullent points are not needed, summarise in one short paragraph
    If the text is a straightforward answer, be brief and simply answer without any form  deep explanation\n
    For example:
    Who authored the paper with Daniel Ihenacho?
    List of co-authors:
     - Naruto Uzumaki
     - David Dike
     - Victor Peters
     - Jerry Peters
     - Bobby M. The First
    If the answer is not in the resource, vector database. Simply reply, I do not know the answer to this question👀
    Question: {question}
    Retrieved Text: {text}
    \n\n\n
    Answer:

    """
    prompt_researcher_input_variables = ['text','question']
    prompt_researcher = PromptTemplate(
        template=prompt_template_researcher,
        input_variables=prompt_researcher_input_variables
    )
    return prompt_researcher

# Creating Vector Database
def vector_database(cohere_key, my_activeloop_org_id, my_activeloop_dataset_name, activeloop_token):
    cohere_embeddings = CohereEmbeddings(
        model="embed-english-v3.0",
        cohere_api_key=cohere_key
    )

    dataset_path = f"hub://{my_activeloop_org_id}/{my_activeloop_dataset_name}"
    # Pass activeloop_token if it's needed for authentication with the hub.
    try:
        db = DeepLake(read_only=True,overwrite=False,dataset_path=dataset_path, embedding=cohere_embeddings)
        return db
    except ConnectionError as e:
        print(f"Error: {e}\nCannot connect to deeplake")

# Setting up the base retriever
def base_retriever(db):
    search_kwargs = {"k":4} # Top 4 retrieved docs
    retriever = db.as_retriever(search_kwargs=search_kwargs)
    return retriever

# Setting up the Reranker
def reranker_retriever(retriever):
    compressor = langchain_cohere_reranker(model='rerank-english-v3.0')
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,base_retriever=retriever
    )
    return compression_retriever

# Retrieving question, final answer and source docs
def compressed_docs(compression_retriever, question:str):
    compressed_docs = compression_retriever.invoke(question)
    retrieved_chunks = [doc.page_content for doc in compressed_docs]
    final_answer = "\n\n".join(retrieved_chunks).strip()
    return question, final_answer, compressed_docs

# The Final Researcher answers
def final_formatted_answer(question,prompt_researcher,final_answer,compressed_docs,chat_model):
    researcher_input_data = {"text":final_answer.strip(),"question":question.strip()}
    llm_researcher_chain = prompt_researcher | chat_model
    researcher_response = llm_researcher_chain.invoke(researcher_input_data)
    print(f"Researcher answer:\n{researcher_response.content}")
    try:
        sources = []
        for i in range(len(compressed_docs)):
            source = compressed_docs[i].metadata.get('source', 'Unknown Source')
            if source not in sources:
                sources.append(source)
    except IndexError as error:
        print("No sources")
        sources.append("No sources")

    print("Source(s):")
    for source in sources:
        print(f"- {source}")

# The LLM model
def llm_model(huggingface_token):
    # repo_id = "microsoft/Phi-4-mini-instruct"
    # repo_id = "mistralai/Mistral-7B-Instruct-v0.3"
    repo_id = "mistralai/Mistral-Small-24B-Instruct-2501" # This model works on Huggingface inference point free version
    # repo_id = "mistralai/Magistral-Small-2506" # This model doesn't work on Huggingface inference point free version
    model_kwargs = {
        "max_new_tokens": 1000, # Maximum tokens to generate
        "max_length": 4000, # Maximum length of input + output
        "temperature": 0.1, 
        "timeout": 6000,
    }
    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        huggingfacehub_api_token = huggingface_token,
        **model_kwargs,
    )
    chat_model = ChatHuggingFace(llm=llm)
    return chat_model

# Environment checker
def get_env_key(enivronment_name, env_key):
    value = os.getenv(env_key)
    if value:
        print(f"{env_key} found in environment.")
    else:
        value = input(f"{env_key} not found. Please enter your {enivronment_name}: ")
    return value

# Main loop
while True:
    try:
        print("\nHi there! This is Ugomma,\nI'm your research assistant and here to help! 😊")
        time.sleep(3)
        print("But let me check your environment first.\n")

        # Collect keys and IDs
        COHERE_API_KEY = get_env_key("Cohere API Key", "COHERE_API_KEY")
        ACTIVELOOP_TOKEN = get_env_key("Activeloop Token", "ACTIVELOOP_TOKEN")
        HUGGINGFACEHUB_API_TOKEN = get_env_key("Huggingface token", "HUGGINGFACEHUB_API_TOKEN")
        
        # Attempt initial connections to validate credentials
        if not COHERE_API_KEY:
            raise ValueError("Cohere API Key is missing.")
        if not ACTIVELOOP_TOKEN:
            raise ValueError("Activeloop Token is missing.")
        if not HUGGINGFACEHUB_API_TOKEN:
            raise ValueError("Huggingface token is missing.")

        my_activeloop_org_id = input("Your Active Loop ID > ").strip()
        my_activeloop_dataset_name = input("Active Loop Dataset Name > ").strip()

        if not my_activeloop_org_id or not my_activeloop_dataset_name:
            raise ValueError("Active Loop Organization ID and Dataset Name are required.")


        print("\nAttempting to connect to services...")
        time.sleep(2)
        print("\n✅ You're all set and connected!")
        
        # Calling all functions
        chat_model = llm_model(HUGGINGFACEHUB_API_TOKEN)
        prompt_researcher = prompt()
        db = vector_database(COHERE_API_KEY, my_activeloop_org_id, my_activeloop_dataset_name, ACTIVELOOP_TOKEN)
        retriever = base_retriever(db)
        reranker = reranker_retriever(retriever)

        # Asking for questions
        while True:
            time.sleep(2)
            question = input("\nAsk me anything (or type 'no' to exit) > ").strip().lower()
            if question == 'no':
                confirm_exit = input("Are you sure you want to exit? (yes/no): ").strip().lower()
                if confirm_exit == 'yes':
                    print("Goodbye for now! 🙂")
                    exit()
                continue

            try:
                # Catching any unexpected Error
                time.sleep(3)
                print("Almost there!")
                question, final_answer, compressed_docs_ = compressed_docs(reranker, question)
                # Final Answers
                final_formatted_answer(question,prompt_researcher, final_answer, compressed_docs_, chat_model)
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: \n{e}\n")
                print("Something went wrong during question processing. Please try again.")
                leave = input("Want to leave? Type 'exit' or 'leave'. Otherwise, press Enter > ").strip().lower()
                if leave in ['exit', 'leave']:
                    print("Exiting program. Bye 🙂")
                    exit()
                continue
            
            # Do you want to Exit the program?
            stop = input("\nType 'STOP' to exit or press Enter to ask another question: ").strip().upper()
            if stop == "STOP":
                print("See you next time! 👋")
                exit()

    # General Exceptions
    except Exception as general_err:
        print(f"\n❌ A critical error occurred during application setup: {general_err}\n")
        print("The program cannot continue. Please review your setup and try again.")
        exit()