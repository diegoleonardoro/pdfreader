import json
import random
from collections import defaultdict
from typing import List, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

# la la la la la 

# Initialize the Tavily search wrapper
search = TavilySearchAPIWrapper()

nhood = ['DUMBO', 'Brooklyn Heights', 'Park Slope', 'Williamsburg', 'Greenwich Village']
search_categories = [
    # ['Neighborhood Introduction DUMBO, Brooklyn', 'Neighborhood Introduction'],
    # ['DUMBO, Brooklyn, Location', 'Location'],
    # ['DUMBO, Brooklyn, History', 'History'],
    # ['DUMBO, Brooklyn, Interesting Facts', 'Interesting Facts'],
    # ['DUMBO, Brooklyn, Demographics', 'Demographics'],
    ['Restaurants DUMBO, Brooklyn, with their respective address and website', 'Restaurants'],
    # ['Public Spaces/Parks in DUMBO, Brooklyn, with their respective address', 'Public Spaces'],
    # ['Night Life spots in DUMBO, Brooklyn, with their respective address and website', 'Night Life'],
    # ['Main Attractions in DUMBO, Brooklyn, with their respective address', 'Main Attractions']
]

def execute_tavily_searches(categories: List[List[str]] = search_categories) -> Dict[str, List[Dict[str, str]]]:
    results = {}
    
    for category, key in categories:
        search_query = category
        search_result = search.results(search_query)
        
        results[key] = [
            {
                "query": search_query,
                "result": search_result
            }
        ]

    return results

# Example usage:
if __name__ == "__main__":
    search_results = execute_tavily_searches()


