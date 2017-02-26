import os
import re
import json
import codecs
from time import time
import elasticsearch
from config import *



def create_index(index_name, index_settings, es_host, es_port):
    es_client = elasticsearch.client.Elasticsearch('http://{}:{}'.format(es_host, es_port))

    if es_client.indices.exists(index=index_name):
        es_client.indices.delete(index=index_name)

    es_client.indices.create(index=index_name, body=index_settings)

def main():

	with open(INDEX_SETTINGS_FP) as f:
	 	index_settings = json.load(f)

	create_index(INDEX_NAME, index_settings, ES_HOST, ES_PORT)
	es_client = elasticsearch.client.Elasticsearch(
        'http://{}:{}'.format(ES_HOST, ES_PORT), timeout=120
    )

	documents = {}

	start_time = time()
	counter=1
	for i in os.listdir(DATA_DIR):
		
		for j in os.listdir(DATA_DIR+"/"+i):

			for k in os.listdir(DATA_DIR+"/"+i+"/"+j):
				fp=DATA_DIR+"/"+i+"/"+j+"/"+k
				with open(fp) as f:
					temp=f.read()

					doc_pmc = re.search(r'<article-id pub-id-type="pmc">(\d+)</article-id>',temp).group(1)
					
					doc_pmid = re.search(r'<article-id pub-id-type="pmid">(\d+)</article-id>',temp)
					if bool(doc_pmid)==True:
						doc_pmid = doc_pmid.group(1)
					else:
						doc_pmid = ''
					
					doc_title = re.search(r'<article-title>([\w\s]*)</article-title>',temp)
					if bool(doc_title)==True:
						doc_title = doc_title.group(1)
					else:
						doc_title = re.search(r'<journal-title>([\w\s]*)</journal-title>',temp)
						if bool(doc_title)==True:
							doc_title = doc_title.group(1)
						else:
							doc_title = ''
					
					
					raw_abstract = re.search(r'<abstract>([\w\s\W]*)</abstract>',temp)
					if bool(raw_abstract) == True:
						raw_abstract = raw_abstract.group(1)
					else:
						raw_abstract = ''
					
					raw_body = re.search(r'<body>([\w\s\W]*)</body>',temp)
					if bool(raw_body) == True:
						raw_body = raw_body.group(1)
					else:
						raw_body = ''
					
					cnt_ops=0
					opts=[]
					bulk_max_ops_cnt=BULK_MAX_OPS_CNT

					opts.append({'create':
						{'_index': INDEX_NAME, '_type': 'paper', '_id': doc_pmc}})
					opts.append({'title': doc_title, 'abstract': raw_abstract, 'pmc': doc_pmc, 'pmid':doc_pmid, 
							  'body': raw_body})
					cnt_ops+=1

					if cnt_ops==bulk_max_ops_cnt:
						es_client.bulk(body=opts)

						del opts[:]
						cnt_ops=0

					es_client.bulk(body=opts)



				# es_client.create(
				# 	index=INDEX_NAME, id=doc_pmc, doc_type='paper',
				# 	body={'title': doc_title, 'abstract': raw_abstract, 'pmc': doc_pmc, 'pmid':doc_pmid, 
				# 		  'body': raw_body
				# 	}
				# 	)
				
	end_time= time()

	print(end_time-start_time)	

if __name__ == '__main__':
    main()