import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain import hub
from langchain.chains.combine_documents import create_stuff_documents_chain
import re
import time 
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from db import DatabaseConnector
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
import json
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from langchain.schema import Document

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize the db connection:
db_name = "insiderhood"
db_connector = DatabaseConnector(dbname=db_name)
db_connector.connect()

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Your existing neighborhood lists here...
test_hood = ['Williamsburg']

# Base directory containing neighborhood PDFs
base_directory = "Brooklyn_Neighborhoods_pdfs"

response_schemas = [
    ResponseSchema(name="History", description="History of the neighborhood"),
    ResponseSchema(name="Location", description="Geographic location and boundaries"),
    ResponseSchema(name="Neighborhood", description="Unique aspects of this neighborhood"),
    ResponseSchema(name="Demographics", description="Key demographic information"),
    ResponseSchema(name="Restaurants", description="Dict of restaurants with descriptions"),
    ResponseSchema(name="Public Spaces", description="Dict of public spaces with descriptions"),
    ResponseSchema(name="Museums", description="Dict of museums with descriptions"),
    ResponseSchema(name="Night Life", description="Dict of night life spots with descriptions"),
]
  
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

# Create LLM
llm = ChatOpenAI(temperature=0)

# Modify the prompt template
template = """
You are an expert on New York City neighborhoods. Based ONLY on the provided context, answer the question about {neighborhood}. Do not include any information that is not explicitly stated in the context.

{format_instructions}

Context: {context}
Question: {question}

For lists like restaurants, public spaces, museums, and nightlife, provide all items found in the context as a bullet point list. Each item should be in the format:
- Name: Description

If no specific items are mentioned, state "No specific items mentioned in the context."

Response:
"""

prompt = ChatPromptTemplate(
    messages=[
        HumanMessagePromptTemplate.from_template(template)
    ],
    input_variables=["neighborhood", "context", "question"],
    partial_variables={"format_instructions": format_instructions}
)

def semantic_text_split(text, max_chunk_size=2000):
    sentences = text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]

    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(sentences)

    clustering_model = AgglomerativeClustering(n_clusters=None, distance_threshold=1.5)
    clustering_model.fit(embeddings)

    clusters = {}
    for sentence, cluster in zip(sentences, clustering_model.labels_):
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(sentence)

    chunks = []
    current_chunk = ""
    for cluster in sorted(clusters.keys()):
        cluster_text = ' '.join(clusters[cluster])
        if len(current_chunk) + len(cluster_text) <= max_chunk_size:
            current_chunk += ' ' + cluster_text
        else:
            chunks.append(current_chunk.strip())
            current_chunk = cluster_text
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def keyword_retriever(vectorstore, query, keywords, k=30):
    docs = vectorstore.similarity_search(query, k=k)
    filtered_docs = [doc for doc in docs if any(keyword in doc.page_content.lower() for keyword in keywords)]
    return filtered_docs

def get_relevant_documents(input_dict):
    query = input_dict["neighborhood"]
    
    # Always retrieve documents for all categories
    restaurant_docs = keyword_retriever(new_vectorstore, query, ["restaurant", "dining", "eatery"])
    public_space_docs = keyword_retriever(new_vectorstore, query, ["park", "square", "public space"])
    museum_docs = keyword_retriever(new_vectorstore, query, ["museum", "gallery", "exhibition"])
    nightlife_docs = keyword_retriever(new_vectorstore, query, ["bar", "club", "nightlife"])
    
    # Combine all documents
    all_docs = restaurant_docs + public_space_docs + museum_docs + nightlife_docs
    
    print(f"Retrieved {len(all_docs)} total documents for {query}")
    return all_docs

for neighborhood in test_hood:
    pdf_path = os.path.join(base_directory, f"{neighborhood} — CityNeighborhoods.NYC.pdf")

    if not os.path.exists(pdf_path):
        print(f"Warning: The file {pdf_path} does not exist. Skipping this neighborhood.")
        continue 

    loader = PyPDFLoader(file_path=pdf_path)
    raw_documents = loader.load()
    text = ' '.join([doc.page_content for doc in raw_documents])
    semantic_chunks = semantic_text_split(text)
    docs = [Document(page_content=chunk) for chunk in semantic_chunks]
    print(f"Split into {len(docs)} semantic chunks")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(docs, embeddings)

    vectorstore_name = f"faiss_index_BROOKLYN_{neighborhood.replace(' ', '_').lower()}"
    vectorstore.save_local(vectorstore_name)
    new_vectorstore = FAISS.load_local(
        vectorstore_name, embeddings, allow_dangerous_deserialization=True
    )

    compressor = LLMChainExtractor.from_llm(llm)
    retriever = new_vectorstore.as_retriever(search_kwargs={"k": 20})
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=retriever
    )

    chain = (
        {
            "context": get_relevant_documents,
            "neighborhood": lambda x: x["neighborhood"],
            "question": lambda x: x["question"],
            "format_instructions": lambda _: format_instructions
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # Run the chain for different questions
    questions = [
        "Provide a list of all restaurants mentioned for this neighborhood.",
        "Provide a list of all public spaces mentioned for this neighborhood.",
        "Provide a list of all museums mentioned for this neighborhood.",
        "Provide a list of all nightlife spots mentioned for this neighborhood."
    ]

    all_results = {}
    for question in questions:
        res = chain.invoke({"neighborhood": neighborhood, "question": question})
        print(f"Results for {neighborhood} - {question}:")
        print(res)
        print("\n" + "="*50 + "\n")
        
        # Parse the result and update all_results
        try:
            parsed_res = json.loads(res)
            for key, value in parsed_res.items():
                if key not in all_results:
                    all_results[key] = value
                elif isinstance(value, dict):
                    all_results[key].update(value)
        except json.JSONDecodeError:
            print(f"Error parsing result for question: {question}")

    # Print the combined results
    print(f"Combined results for {neighborhood}:")
    print(json.dumps(all_results, indent=2))

    time.sleep(6)  

print("Processing complete.")



#   try:
#         parsed_output = output_parser.parse(res)
#         print(f"Results for {neighborhood}:")
#         print(json.dumps(parsed_output, indent=2))
#     except Exception as e:
#         print(f"Error parsing output: {e}")
#         print("Raw output:", res)

#     # Store in database
#     db_connector.replace_document(
#         "neighborhood_summaries",
#         {"neighborhood": neighborhood, "borough": "Brooklyn"},
#         {
#             "neighborhood": neighborhood,
#             "response": parsed_output,
#             "borough": "Brooklyn"
#         },
#         upsert=True
#     )

#     time.sleep(6)  