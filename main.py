import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from db import DatabaseConnector
from bson import json_util

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


db_name = "insiderhood"
db_connector = DatabaseConnector(dbname=db_name)
db_connector.connect()


test_hood = ['Williamsburg']


base_directory = "Brooklyn_neighborhoods"

response_schemas = [
    ResponseSchema(name="History", description="History of the neighborhood"),
    ResponseSchema(name="Location", description="Geographic location and boundaries"),
    ResponseSchema(name="Neighborhood Introduction", description="Unique aspects of this neighborhood"),
    ResponseSchema(name="Interesting Facts", description="Interesting facts of this neighborhood"),
    ResponseSchema(name="Demographics", description="Key demographic information"),
    ResponseSchema(name="Restaurants", description="Dict of restaurants with descriptions"),
    ResponseSchema(name="Public Spaces", description="Dict of public spaces with descriptions"),
    ResponseSchema(name="Museums", description="Dict of museums with descriptions"),
    ResponseSchema(name="Night Life", description="Dict of night life spots with descriptions"),
    ResponseSchema(name="Attractions", description="Dict of attractions with descriptions"),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()


llm = ChatOpenAI(temperature=0)


template = """

    You are an expert storyteller that specializes on New York City neighborhoods. Paint a vivid picture of {neighborhood} for the category: {category}, using ONLY the provided context. Your words should transport the reader to the streets and the places. Be descriptive, engaging, and colorful in your language, but ensure every detail is grounded in the given information.

    {format_instructions}

    Context: {context}
    Question: Weave a captivating narrative about the {category} of {neighborhood}.

    Your response should be:
    - Vivid and immersive, bringing the neighborhood to life
    - Strictly limited to the context provided for the specific category
    - Rich in sensory details and local flavor
    - The given context should be rewritten in a way that is more engaging and colorful.
    - Avoid using imperative language such as "Embark", "Discover", "Explore", or phrases like "Step back in time..." or "Imagine..." or "Step into...". ONLY use descriptive language.
    - Begin sentences with factual statements or descriptions, not commands or suggestions.
    - Formatted as a JSON object with a single key matching the category name.

    For lists like restaurants, public spaces, museums, nightlife, and attractions, provide all items found in the contextand transform each item into an enticing description. Format as:
    "Actual Name of Place": "An enticing description that makes the reader want to visit"

    If no specific items are mentioned, state "No specific items mentioned in the context."

    Response (in JSON format):
"""

prompt = ChatPromptTemplate(
    messages=[
        HumanMessagePromptTemplate.from_template(template)
    ],
    input_variables=["neighborhood", "context", "category"],
    partial_variables={"format_instructions": format_instructions}
)

def get_relevant_documents(input_dict):
    neighborhood = input_dict["neighborhood"]
    category = input_dict["category"]
    
    json_path = os.path.join(base_directory, f"{neighborhood.lower()}.json")
    
    if not os.path.exists(json_path):
        print(f"Warning: The file {json_path} does not exist. Skipping this neighborhood.")
        return ""
    
    with open(json_path, 'r') as file:
        data = json.load(file)
    
    if neighborhood not in data:
        print(f"Warning: {neighborhood} not found in the JSON file.")
        return ""
    
    if category not in data[neighborhood]:
        print(f"Warning: {category} not found for {neighborhood} in the JSON file.")
        return ""
    
    return json.dumps(data[neighborhood][category])


chain = (
    {
        "context": get_relevant_documents,
        "neighborhood": lambda x: x["neighborhood"],
        "category": lambda x: x["category"],
    }
    | prompt
    | llm
    | StrOutputParser()
)

all_results = {}

def clean_json_string(json_string):
    if isinstance(json_string, str):
        
        return json_string.replace("```json", "").replace("```", "").strip()
    return json_string

def parse_llm_output(output, category):
    if isinstance(output, dict):
        return output.get(category, output)
    
    
    output = output.replace("```json", "").replace("```", "").strip()
    
    try:
        # Try to parse the entire output as JSON
        parsed = json.loads(output)
        if category in parsed:
            return parsed[category]
        else:
            # If the category is not found, return the entire parsed output
            return parsed
    except json.JSONDecodeError:
        # If JSON parsing fails, return the cleaned string
        return output.strip('"')
def prepare_for_mongodb(results):
    for neighborhood, categories in results.items():
        for category, value in categories.items():
            parsed_value = parse_llm_output(value, category)
            categories[category] = parsed_value
    return results

for neighborhood in test_hood:
    neighborhood_results = {}
    
    for category in [schema.name for schema in response_schemas]:
        print(category)
        res = chain.invoke({"neighborhood": neighborhood, "category": category})
        parsed_output = parse_llm_output(res, category)
        neighborhood_results[category] = parsed_output

    all_results[neighborhood] = neighborhood_results

    all_results = prepare_for_mongodb(all_results)

    mongo_ready = all_results[neighborhood]

    print(json_util.dumps(mongo_ready, indent=2))

    db_connector.replace_document(
        "neighborhood_summaries",
        {"neighborhood": neighborhood, "borough": "Brooklyn"},
        {
            "neighborhood": neighborhood,
            "information": mongo_ready, 
            "borough": "Brooklyn"
        },
        upsert=True
    )











 