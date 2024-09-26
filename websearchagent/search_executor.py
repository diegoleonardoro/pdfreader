import json
import random
from collections import defaultdict
from typing import List, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

# lelele le le le 
# Initialize the Tavily search wrapper
search = TavilySearchAPIWrapper()

neighborhoods = [
    ('DUMBO', 'Brooklyn'),
    # ('Brooklyn Heights', 'Brooklyn'),
    # ('Park Slope', 'Brooklyn'),
    # ('Williamsburg', 'Brooklyn'),
    # ('Greenwich Village', 'Manhattan'), 
]

search_categories = [
    ['{neighborhood}, {borough}, Neighborhood Introduction', 'Neighborhood Introduction'],
    ['{neighborhood}, {borough}, Location', 'Location'],
    ['{neighborhood}, {borough}, History', 'History'],
    ['{neighborhood}, {borough}, Interesting Facts', 'Interesting Facts'],
    ['{neighborhood}, {borough}, Demographics', 'Demographics'],
    ['Specific Restaurants in {neighborhood}, {borough}, with their respective address and website', 'Restaurants'],
    ['Parks in {neighborhood}, {borough}, with their respective address', 'Parks'],
    ['Night Life spots in {neighborhood}, {borough}, with their respective address and website', 'Night Life'],
    ['Main Attractions in {neighborhood}, {borough}, with their respective address', 'Main Attractions']
]

def execute_tavily_searches(categories: List[List[str]] = search_categories) -> Dict[str, List[Dict[str, str]]]:
    results = {}
    
    for neighborhood, borough in neighborhoods:
        neighborhood_results = {}
        for category_template, key in categories:
            search_query = category_template.format(neighborhood=neighborhood, borough=borough)
            search_result = search.results(search_query)
            
            neighborhood_results[key] = [
                {
                    "query": search_query,
                    "result": search_result
                }
            ]
        results[f"{neighborhood}, {borough}"] = neighborhood_results
      

    return results

# Example usage:
if __name__ == "__main__":
    search_results = execute_tavily_searches()


