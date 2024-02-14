import sys
import os
from pymongo import MongoClient
import time

def get_mongo_client():
    try:
        mongo_endpoint, mongo_endpoint_port = os.environ["MONGO_ENDPOINT"].split(":")
        mongo_endpoint_username = os.environ["MONGO_INITDB_ROOT_USERNAME"]
        mongo_endpoint_password = os.environ["MONGO_INITDB_ROOT_PASSWORD"]
    except KeyError as e:
        sys.exit(f"Environment variable {str(e)} not set.")
    
    return MongoClient(mongo_endpoint, int(mongo_endpoint_port), username=mongo_endpoint_username, password=mongo_endpoint_password)

client = get_mongo_client()

def fetch_predicate_labels(predicate_ids, collection):
    predicates = collection.find({"entity": {"$in": predicate_ids}}, {"entity": 1, "labels.en": 1})
    predicate_labels = {predicate["entity"]: predicate.get("labels", {}).get("en", "Unknown Label") for predicate in predicates}
    return predicate_labels

def enhance_and_store_results(db_name, collection_name, summary_collection_name, pipeline, label_resolver_collection):
    db = client[db_name]
    collection = db[collection_name]
    results = collection.aggregate(pipeline)
    aggregated_results = list(results)
    
    unique_predicates = {result['_id'] for result in aggregated_results} if collection_name == "objects" else \
                         {result['_id']['predicate'] for result in aggregated_results}
    
    predicate_labels = fetch_predicate_labels(list(unique_predicates), db[label_resolver_collection])
    
    enhanced_results = [{
        'literalType': result['_id']['literalType'] if collection_name != "objects" else None,
        'predicate': result['_id']['predicate'] if collection_name != "objects" else result['_id'],
        'label': predicate_labels.get(result['_id']['predicate'] if collection_name != "objects" else result['_id'], "Unknown Label"),
        'count': result['count']
    } for result in aggregated_results]
    
    summary_collection = db[summary_collection_name]
    summary_collection.insert_many(enhanced_results)
    summary_collection.create_index([("count", -1)])

def main(db_name):
    start_time_objects = time.time()
    pipeline_objects = [
        { "$project": {
            "relationPairs": {
                "$objectToArray": "$objects"
            }
        }},
        { "$unwind": "$relationPairs" },
        { "$unwind": "$relationPairs.v" },
        {
            "$group": {
                "_id": "$relationPairs.v",
                "count": { "$sum": 1 }
            }
        },
        { "$sort": { "count": -1 } }
    ]
    enhance_and_store_results(db_name, "objects", "objectsSummary", pipeline_objects, "items")

    end_time_objects = time.time()
    print(f"Time taken for objects: {end_time_objects - start_time_objects} seconds")

    start_time_literals = time.time()
    pipeline_literals = [
        {
            "$project": {
                "literals": {"$objectToArray": "$literals"}
            }
        },
        {"$unwind": "$literals"},
        {"$unwind": "$literals.v"},
        {"$project": {
            "literalType": "$literals.k",
            "predicateValuePairs": {"$objectToArray": "$literals.v"}
        }},
        {"$unwind": "$predicateValuePairs"},
        {"$group": {
            "_id": {
                "literalType": "$literalType",
                "predicate": "$predicateValuePairs.k"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    enhance_and_store_results(db_name, "literals", "literalsSummary", pipeline_literals, "items")

    end_time_literals = time.time()
    print(f"Time taken for literals: {end_time_literals - start_time_literals} seconds")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_name = sys.argv[1]
        main(db_name)
    else:
        sys.exit("Please provide a DB name as an argument.")
