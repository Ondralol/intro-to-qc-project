import json
import requests
from collections import Counter

from game.game_helper import Target


def send_to_quokka(program, count=1, my_quokka='quokka5'):
    request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
    data = {'script': program, 'count': count}
    result = requests.post(request_http, json=data, verify=True)
    try:
        json_obj = json.loads(result.content)
    except json.JSONDecodeError:
        raise RuntimeError("Quokka quantum computer is currently unavailable (HTTP {})".format(result.status_code))
    raw_data = json_obj['result']['c']
    counts = Counter(["".join(map(str, shot)) for shot in raw_data])
    print(dict(counts))
    return dict(counts)


def fire_shot(target1: Target, target2: Target) -> str:
    """Run one entangled measurement. Returns a 2bit string -  bit 0 = target1, bit 1 = target2.
    With CNOT entanglement only "00" and "11" are possible outcomes."""
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        'qreg q[2];\n'
        'creg c[2];\n'
        f'ry({target1.theta}) q[0];\n'
        'cx q[0], q[1];\n'
        'measure q[0] -> c[0];\n'
        'measure q[1] -> c[1];\n'
    )
    counts = send_to_quokka(qasm, count=1)
    # Either returns "00" or "11" in our case
    return max(counts, key=counts.get)