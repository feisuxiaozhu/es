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

def run_treceval(results, qrels_fp, treceval_fp):

	with NamedTemporaryFile(delete=False, mode='w') as tmp:
		tmp_fn = tmp.name

		for q_id, docs in sorted(results.items()):
			for i, doc in enumerate(docs):	#several returned docs for one query
				
				tmp.write('{q_id} 0 {d_id} {i} {score:.5f} ES_DEMO\n'.format(
					q_id=q_id, d_id=doc['_id'], i=i, score=doc['_score']))

	platform_name = platform.system()
	treceval_fp='{}_{}'.format(treceval_fp, platform_name)


	cmd = ['./{}'.format(treceval_fp), qrels_fp, tmp_fn]

	try:
		proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		resp = proc.communicate()
		msg_out, msg_err = (msg.decode('utf-8') for msg in resp)

	except Exception:
		raise
	finally:
		os.remove(tmp_fn)

	return msg_out.strip()


def main():
	with open(QUERIES_FP) as f:
		queries = parse_raw_queires(f.read())

	results = search_queries(queries,INDEX_NAME, ES_HOST, ES_PORT)
	output_treceval =  run_treceval(results, QRELS_FP, TRECEVAL_FP)
	print(output_treceval)



if __name__ == '__main__':
    main()
