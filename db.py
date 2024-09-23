from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

class DatabaseConnector:
    def __init__(self, dbname):
        uri = os.getenv("MONGODB_URI")
        print("Connecting to URI:", uri)
        # Set directConnection=True to use the 'isMaster' command for legacy MongoDB versions
        self.client = MongoClient(uri, loadBalanced=True)
        self.dbname = dbname
        self.db_connection = None
        
    def test_connection(self):
        try:
            # Using 'ping' command to test connection
            self.client.admin.command('ping')
            print("MongoDB connection successful.")
        except Exception as e:
            print("MongoDB connection failed:", e)
            raise e

    def connect(self):
        if not self.db_connection:
            self.db_connection = self.client[self.dbname]
        return self.db_connection

    def add_data(self, collection_name, data):
        if isinstance(data, dict):
            result = self.db_connection[collection_name].insert_one(data)
        elif isinstance(data, list):
            result = self.db_connection[collection_name].insert_many(data)
        else:
            raise ValueError("Data must be a dictionary or a list of dictionaries.")
        return result

    def replace_document(self, collection_name, filter_doc, new_data, upsert=True):
        # This method will replace an existing document or insert a new one if no matching document is found
        result = self.db_connection[collection_name].replace_one(filter_doc, new_data, upsert=upsert)
        return result

    def close(self):
        if self.client:
            self.client.close()

# # Usage
# db_connector = DatabaseConnector("insiderhood")
# db_connector.test_connection()
# db = db_connector.connect()

# data_to_insert = {"name": "John Doe", "age": 30}
# insert_result = db_connector.add_data("userssss", data_to_insert)
# print("Inserted Document ID:", insert_result.inserted_id)

# users_data = [
#     {"name": "Alice", "age": 25},
#     {"name": "Bob", "age": 28}
# ]
# insert_result = db_connector.add_data("userssss", users_data)
# print("Inserted Document IDs:", insert_result.inserted_ids)

# db_connector.close()