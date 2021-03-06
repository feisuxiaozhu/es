import re
import os
import json
import platform
import subprocess
from tempfile import NamedTemporaryFile
import elasticsearch 
from config import *

import sys
sys.path.insert(0, '/home/ubuntu/Desktop/QuickUMLS')

from quickumls import *

from collections import Counter
from collections import defaultdict
import math
import operator 

def parse_raw_queires(raw_data):
	queires = []
	raw_queries = re.split(r'</topic>',raw_data)
	matcher = QuickUMLS('umlsdata/')

	for raw_query in raw_queries:

		q_number = re.search(r'number="(\d*)"',raw_query)
		if bool(q_number)==True:
			q_number=q_number.group(1)		
			q_description = re.search(r'<description>([\s\w\W]+)</description>',raw_query).group(1)
			q_summary = re.search(r'<summary>([\s\w\W]+)</summary>',raw_query).group(1)
			q_summaryumls = matcher.match(q_summary)
			b=''
			for i in q_summaryumls:		
				b = b+i[0]['term']+" "
			q_summaryumls = b

			b=''
			q_descriptionumls=matcher.match(q_description)
			for i in q_descriptionumls:
				b = b+i[0]['term']+ " "
			q_descriptionumls=b
			q_summarydescriptionumls = q_summary + " "+ q_descriptionumls
			q_summaryumlsdescriptionumls = q_summaryumls +" "+ q_descriptionumls
			queires.append(
			{'_number': q_number, 'description': q_description, 'summary': q_summary,
			'summaryumls': q_summaryumls,'descriptionumls':q_descriptionumls,
			'summarydescriptionumls': q_summarydescriptionumls,
			'summaryumlsdescriptionumls': q_summaryumlsdescriptionumls})
		
	return queires
def make_pseudo_query_dsl(s):
	query = {
		#'fields': [],
		'query': {
			'bool': {
				'should': [{
					'match': {
						'body': {
							'query': s,
							"boost": 10,
							'operator': 'or'

						}
					}
				},{
					'match': {
						'abstract': {
							'query': s,
							'operator': 'or'
						}
					}
				}

				]
				}
		}
	}  



	return query
def make_query_dsl(s,t):

	query = {
		#'fields': [],
		'query': {
			'bool': {
				'should': [{
					'match': {
						'body': {
							'query': s,
							"boost": 10,
							'operator': 'or'

						}
					}
				},{
					'match': {
						'abstract': {
							'query': t,
							'operator': 'or'
						}
					}
				}

				]
				}
		}
	}  



	return query

def search_queries(queries, index_name, es_host, es_port):
	#first return pseudo feedback
	prf_results = pseudo_feedback(queries, index_name, es_host, es_port)
	es_client = elasticsearch.client.Elasticsearch(
		'http://{}:{}'.format(es_host, es_port), timeout=30)

	results={}

	for query in queries:
		query_dsl = make_query_dsl(query['summarydescriptionumls'],prf_results[query['_number']])
		raw_results = es_client.search(index=index_name, body=query_dsl, size=1000)
		results[query['_number']]=raw_results['hits']['hits']

	

	return results

def pseudo_feedback(queries, index_name, es_host, es_port):
	es_client = elasticsearch.client.Elasticsearch(
		'http://{}:{}'.format(es_host,es_port),timeout=30)
	results={}


	for query in queries:
		query_dsl = make_pseudo_query_dsl(query['summarydescriptionumls'])
		raw_results = es_client.search(index=index_name, body=query_dsl, size=10)
		results[query['_number']]=raw_results['hits']['hits']

		#find top words from top 10 retrieved docs
		temp=""	
		for i in results[query['_number']]:
			temp = temp + i['_source']['body'] + " "
		words = re.findall(r'\w+', temp)
		dict_tf = Counter(words).most_common(100) 
		
		#find the df for top terms
		dict_df={}
		for x, y in dict_tf:
			count = 0
			for i in results[query['_number']]:
				if x in i['_source']['body']:
					count += 1
			dict_df[x]=count

		#calculate idf for top terms
		dict_idf={}
		for x, y in dict_tf:
			df = dict_df[x]
			idf = math.log10(11/(1+df))
			dict_idf[x] = idf

		#find if term appear in query
		dict_query={}
		for x, y in dict_tf:
			if x in query['summaryumlsdescriptionumls']:
				dict_query[x]=1
			else:
				dict_query[x]=0

		#give different weight to terms based on idf
		dict_return={}
		for x,y in dict_tf:
			weight = 2*dict_query[x]*y +0.075*dict_df[x]* dict_idf[x]
			dict_return[x] = weight
		#dict_return=sorted(dict_return.items(), key=operator.itemgetter(1))

		#clean the dictionary's integer entry and entries of length less than 5
		temp=[]
		for key, value in dict_return.items():
			if len(key)<5:
				temp.append(key)
			if hasNumbers(key):
				temp.append(key)

		evil_words=['right','lower','center','italic','align','caption','Table']
		temp=temp+evil_words
		for x in temp:
			if x in dict_return.keys():
				dict_return.pop(x)

		#output the top terms in dict_return
		temp = ''
		for x,y in Counter(dict_return).most_common(10):
			temp = temp + x +' '

		results[query['_number']]=temp

	return results
		



def hasNumbers(inputString):
	return any(char.isdigit() for char in inputString)


def run_treceval(results, qrels_fp, treceval_fp):

	with NamedTemporaryFile(delete=False, mode='w') as tmp:
		tmp_fn = tmp.name

		for q_id, docs in sorted(results.items()):
			for i, doc in enumerate(docs):	#several returned docs for one query
				
				tmp.write('{q_id} 0 {d_id} {i} {score:.5f} ES_DEMO\n'.format(
					q_id=q_id, d_id=doc['_id'], i=i, score=doc['_score']))

	platform_name = platform.system()
	treceval_fp='{}_{}'.format(treceval_fp, platform_name)


	# cmd = ['./{}'.format(treceval_fp), qrels_fp, tmp_fn]
	# try:
	# 	proc = subprocess.Popen(
	# 		cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# 	resp = proc.communicate()
	# 	msg_out, msg_err = (msg.decode('utf-8') for msg in resp)

	# except Exception:
	# 	raise
	# finally:
	# 	os.remove(tmp_fn)

	# return msg_out.strip()
	pipe = subprocess.Popen(["perl", "./bin/trec_eval_Linux", qrels_fp, tmp_fn])

def main():
	with open(QUERIES_FP) as f:
		queries = parse_raw_queires(f.read())

	#pseudo_feedback(queries,INDEX_NAME,ES_HOST,ES_PORT)

	results = search_queries(queries,INDEX_NAME, ES_HOST, ES_PORT)

	output_treceval =  run_treceval(results, QRELS_FP, TRECEVAL_FP)
	print(output_treceval)



if __name__ == '__main__':
	main()
