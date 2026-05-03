import json
import requests
from collections import Counter
import math


def send_to_quokka(program, count=1, my_quokka='quokka5'):
   request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
   data = {'script': program, 'count': count}
   result = requests.post(request_http, json=data, verify=True)
   json_obj = json.loads(result.content)
   raw_data = json_obj['result']['c']
   counts = Counter(["".join(map(str, shot)) for shot in raw_data])
   print(dict(counts))
   return dict(counts)