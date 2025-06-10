from langchain.vectorstores import DeepLake
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain_cohere import CohereEmbeddings
import os
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv

# loading .env
load_dotenv('.env')

desktop = os.path.expanduser("~\Desktop")
research_assistant = os.path.join(desktop,'research_assistant')
research_articles = os.path.join(research_assistant,"research_articles")

# Collecting all pdfs files
pdf_files = []
for root, dirs, files in os.walk(research_articles):
    for file in files:
        if file.lower().endswith(".pdf"):
            pdf_files.append(os.path.join(root,file))

# Loading, splitting and appending each pdf file
all_pages = []
for pdf in pdf_files:
    loader = PyPDFLoader(pdf)
    pages = loader.load_and_split()
    all_pages.extend(pages)

# Chunking 
text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=700)
docs = text_splitter.split_documents(all_pages)


all_texts, all_metadatas = [], []
for i in range(len(docs)):
    all_texts.append(docs[i].page_content)
    filename = os.path.splitext(os.path.basename(docs[i].metadata['source']))[0]
    all_metadatas.append({'source':f"Title: {filename}, Page: {docs[i].metadata['page_label']}"})

# vector database creation
def vector_database(all_texts,all_metadatas,cohere_key\
                    ,my_activeloop_org_id\
                        ,my_activeloop_dataset_name):
    # Cohere Embeddings
    cohere_embeddings = CohereEmbeddings(
        model="embed-english-v3.0",
        # model="embed-english-v2.0",
        cohere_api_key=cohere_key)

    # Create Deep Lake Vector Store
    my_activeloop_org_id = my_activeloop_org_id
    my_activeloop_dataset_name = my_activeloop_dataset_name
    dataset_path = f"hub://{my_activeloop_org_id}/{my_activeloop_dataset_name}"
    db = DeepLake(dataset_path=dataset_path, embedding=cohere_embeddings,overwrite=True)
    db.add_texts(all_texts,all_metadatas)
    print(f"\nVector Store is created: {my_activeloop_org_id}/{my_activeloop_dataset_name}")



# getting all environment keys
def get_env_key(prompt_name, env_key):
    value = os.getenv(env_key)
    if value:
        print(f"{env_key} found in environment.")
    else:
        value = input(f"{env_key} not found. Please enter your {prompt_name}: ")
    return value

# Main program execution
while True:
    try:
        COHERE_API_KEY = get_env_key("Cohere API Key", "COHERE_API_KEY")
        ACTIVELOOP_TOKEN = get_env_key("Activeloop Token", "ACTIVELOOP_TOKEN")
        
        my_activeloop_org_id = input("Your Active Loop ID > ")
        my_activeloop_dataset_name = input("Active Loop Dataset Name > ")

        vector_database(
            all_texts,
            all_metadatas,
            COHERE_API_KEY,
            my_activeloop_org_id,
            my_activeloop_dataset_name
        )
        break  # Exit loop if everything runs successfully
    except Exception as e:
        print("\nError:", e)
        print("You must provide all required keys and dataset information.")
        leave = input("Want to leave, type 'exit' or 'leave'. If not, then hit enter> ").strip().lower()
        if leave in ['exit','leave']:
            print("Exiting program, bye 🙂")
            break