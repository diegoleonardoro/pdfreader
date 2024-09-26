from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import END, StateGraph
from search_executor import execute_tavily_searches
from chains import refine_search_results

# Define the state type
class State(Dict[str, Any]):
    """The state of the workflow."""

    messages: List[HumanMessage | AIMessage]

# Create the graph
graph = StateGraph(State)

# Define the tavily_searches node
def tavily_searches(state: State) -> Dict[str, Any]:
    search_results = execute_tavily_searches()
    state["messages"].append(AIMessage(content=str(search_results)))
    return {"messages": state["messages"]}

# Define the refine_results node
def refine_results(state: State) -> Dict[str, Any]:
    last_message = state["messages"][-1]
    refined_results = refine_search_results(last_message.content)
    state["messages"].append(AIMessage(content=str(refined_results)))
    return {"messages": state["messages"]}

# Add nodes to the graph
graph.add_node("tavily_searches", tavily_searches)
graph.add_node("refine_results", refine_results)

# Define the edges
graph.add_edge("tavily_searches", "refine_results")
graph.add_edge("refine_results", END)

# Set the entry point
graph.set_entry_point("tavily_searches")

# Compile the graph
workflow = graph.compile()

# Function to run the graph
def run_graph():
    inputs = State(messages=[HumanMessage(content="Tell me about DUMBO, Brooklyn")])
    result = workflow.invoke(inputs)
    return result

# Example usage
if __name__ == "__main__":
    result = run_graph()
  

