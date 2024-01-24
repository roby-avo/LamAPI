MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 0
        },
        "analysis": {
            "analyzer": {
                "my_analyzer": {
                    "type": "custom",
                    "tokenizer": "whitespace",
                    "filter": [
                        "lowercase"
                    ]
                }
            }
        }
    }, 
    "mappings": {
        "properties": {
            "id": {"type": "text"},
            "name": {
                "type": "text",
                "analyzer": "my_analyzer"
            },
            "description": {"type": "text"},
            "types": {"type": "keyword"},
            "length": {"type": "long"},
            "ntoken": {"type": "long"},
            "popularity": {
                "type": "rank_feature",
                "positive_score_impact": True
            }
        }
    }
}

