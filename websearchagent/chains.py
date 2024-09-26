from dotenv import load_dotenv
load_dotenv()
import datetime
from typing import List
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import json
# import openai
import os
import ast
from db import DatabaseConnector

# openai.api_key = os.getenv("OPENAI_API_KEY")
db_name = "insiderhood"
db_connector = DatabaseConnector(dbname=db_name)
db_connector.connect()



llm = ChatOpenAI(model="gpt-4-turbo-preview")
# parser = JsonOutputParser(pydantic_object='AnswerQuestion')


import json
from typing import Union, Dict, List
from openai import OpenAI

client = OpenAI()

def safe_get(data: Union[str, Dict, List], key: str) -> Union[str, Dict, List, None]:
    """Safely get a value from a dictionary or list."""
    if isinstance(data, dict):
        return data.get(key)
    elif isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            return data[0].get(key)
    return None

def extract_content(item: Union[str, Dict]) -> str:
    """Extract content from an item, whether it's a string or a dictionary."""
    if isinstance(item, str):
        return item
    elif isinstance(item, dict):
        return item.get('content', str(item))
    return str(item)

def refine_search_results(input_data: Union[str, Dict]) -> dict:
    """
    Refine and reformat the search results using OpenAI's API directly.
    """
    try:
        data = ast.literal_eval(input_data) if isinstance(input_data, str) else input_data
    except (ValueError, SyntaxError):
        print("Failed to parse input_data as a dictionary")
        return

    # Get the first key and its values
    first_key = next(iter(data))
    key_values = data[first_key]


    # Iterate through the keys of the dictionary
    refined_data = {}
    for key in key_values.keys():
        print(f"Processing: {key}")
        
        # Access the value for each key
        value = key_values[key]
        print("------------------------------")
        print("key", key)
        print("value", value)
        print("------------------------------")

        if key in ["Neighborhood Introduction", "Location", "History", "Interesting Facts", "Demographics"]:

            content_list = [item['content'] for result in value for item in result['result'] if 'content' in item]
            urls_list = [item['url'] for result in value for item in result['result'] if 'url' in item]

            prompt = f"""You are an expert writer who creates engaging and descriptive neighborhood introductions. 
            Use the following information to craft a captivating description that will entice visitors:

            {' '.join(content_list)}

            1. Use only the information provided in the text, but present it in a compelling way.
            2. Write as if you're a journalist composing an engaging report.
            3. The response should be about 3-4 paragraphs long.

            Format your response as a JSON object with the following structure:
            {{
              "content": "Your combined introduction text here",
              "urls": {urls_list}
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content
            parsed_content = json.loads(response_content)

            cleaned_content = parsed_content['content'].replace('\\n', '\n').strip()
            cleaned_content = cleaned_content.replace('\\"', '"')
                
            refined_data[key] = {
                    "content": cleaned_content,
                    "urls": parsed_content['urls']
            }
            

        if key in ["Restaurants", "Parks", "Night Life", "Main Attractions"]:
          refined_places = []
          for item in value:
            for result in item['result']:
              # print("result==>> ", result)
              # print("result['content']==>> ", result['content'])
              # print("result['url']==>> ", result['url'])
              # print("------------------------------")

              prompt = f"""
                    You are an expert writer who creates engaging descriptions of places. 
                    Extract the following information from the given content about a restaurant:
                    1. Name of the restaurant
                    2. A engaging, descriptive and captivating description of the restaurant
                    3. The address (if available, otherwise leave blank)

                    Content: {result['content']}

                    Format your response as a JSON object with the following structure:
                    {{
                      "name": "Restaurant Name",
                      "description": "Brief description of the restaurant",
                      "address": "Restaurant address (if available)"
                    }}
              """
              response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"}
              )
              parsed_response = json.loads(response.choices[0].message.content)
                    
              refined_places.append({
                        "url": result['url'],
                        "name": parsed_response['name'],
                        "description": parsed_response['description'],
                        "address": parsed_response['address']
                })
              
          refined_data[key] = refined_places

        # print("refined_data-->>>", refined_data)


    print("-----------------------------------")
    print("refined_data-->>>", refined_data)
    print("-----------------------------------")
    print("refined_data type-->>>", type(refined_data))
    print("-----------------------------------")


    db_connector.replace_document(
          "neighborhood_summaries",
          {"neighborhood": "DUMBO", "borough":"Brooklyn"},
          {
              "neighborhood":  "DUMBO",
              "information": refined_data, 
              "borough": "Brooklyn"
          },
          upsert=True
    )

    return refined_data