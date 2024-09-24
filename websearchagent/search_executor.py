import json
import random
from collections import defaultdict
from typing import List
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

# Initialize the Tavily search wrapper
search = TavilySearchAPIWrapper()

nhood = ['DUMBO', 'Brooklyn Heights', 'Park Slope', 'Williamsburg', 'Greenwich Village']
search_categories = [
    'Neighborhood Introduction DUMBO, Brooklyn', 
    'DUMBO, Brooklyn, Location', 
    'DUMBO, Brooklyn, History', 
    'DUMBO, Brooklyn, Interesting Facts', 
    'DUMBO, Brooklyn, Demographics', 
    'Restaurants DUMBO, Brooklyn, with their respective address and website', 
    'Public Spaces/Parks in DUMBO, Brooklyn, with their respective address', 
    'Night Life spots in DUMBO, Brooklyn, with their respective address and website',
    'Main Attractions in DUMBO, Brooklyn, with their respective address'
]

def execute_tavily_searches(categories: List[str] = search_categories):
    results = defaultdict(list)
    
    for category in categories:
        search_query = f"{category} in {random.choice(nhood)}"
        search_result = search.results(search_query)  # Changed from search.run to search.results
        
        results[category].append({
            "query": search_query,
            "result": search_result
        })
    
    return dict(results)

# Example usage:
if __name__ == "__main__":
    search_results = execute_tavily_searches()
    print(json.dumps(search_results, indent=2))