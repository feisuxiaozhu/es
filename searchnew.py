import re
import os
import json
import platform
import subprocess
from tempfile import NamedTemporaryFile
import elasticsearch 
from config import *

def parse_raw_queires(raw_data):
	queires = []
	raw_queries = re.split(r'</topic>',raw_data)

	for raw_query in raw_queries:

		q_number = re.search(r'number="(\d*)"',raw_query)
		if bool(q_number)==True:
			q_number=q_number.group(1)		
			q_description = re.search(r'<description>([\s\w\W]+)</description>',raw_query).group(1)
			q_summary = re.search(r'<summary>([\s\w\W]+)</summary>',raw_query).group(1)

			queires.append(
			{'_number': q_number, 'description': q_description, 'summary': q_summary})
		
	return queires

def make_query_dsl(s):

    query = {
        #'fields': [],
        'query': {
            'match': {
                'abstract': {
                    'query': s,
                    'operator': 'or'
                }
            }
        }
    }
    return query

def search_queries(queries, index_name, es_host, es_port):
    es_client = elasticsearch.client.Elasticsearch(
        'http://{}:{}'.format(es_host, es_port))

    results={}

    for query in queries:
        query_dsl = make_query_dsl(query['summary'])
        raw_results = es_client.search(index=index_name, body=query_dsl, size=100)
        results[query['_number']]=raw_results['hits']['hits']

    return results

def main():
	with open(QUERIES_FP) as f:
		queries = parse_raw_queires(f.read())

	results = search_queries(queries,INDEX_NAME, ES_HOST, ES_PORT)




if __name__ == '__main__':
    main()
