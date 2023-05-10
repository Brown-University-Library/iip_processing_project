"""
This code checks:
- that redis is running.
- that expected queues exist
- that expected workers are running.
"""

import subprocess

expectation = {
    'expected_queues': [ 'aa', 'bb', 'cc' ],
    'expected_workers': [ 'xx', 'yy', 'zz']
}

def run_code():
    redis_check, queues, workers = get_rqinfo()
    assert type(redis_check) == str
    assert type(queues) == list
    assert type(workers) == list
    print('Queues:', queues)
    print('Workers:', workers)
    print('Redis:', redis_check)


def get_rqinfo():
    ## Run the rqinfo command and get the output
    result = subprocess.run(['rqinfo'], stdout=subprocess.PIPE)
    output = result.stdout.decode()

    ## Split the output into lines
    lines = output.split('\n')

    ## Initialize empty lists for queues and workers
    redis_check = 'init'
    queues = []
    workers = []

    # Iterate over each line in the output
    for (i, line) in enumerate(lines):
        ## check for redis-server connection error
        if i == 0:
            if '6379' in line and 'connection refused' in line.lower():  # `Error 111 connecting to localhost:6379. Connection refused.`
                redis_check = 'redis_down'
                break
            else:
                redis_check = 'redis_ok'

        if line.strip() == '':
            continue

        ## If line contains queue info, add it to the queues list
        if '|' in line:
            queue_name = line.split('|')[0].strip()
            queues.append(queue_name)

        ## If line contains worker info, add it to the workers list
        if 'idle:' in line:
            worker_name = line.split(' ')[0].strip()
            workers.append(worker_name)

    return redis_check, queues, workers

if __name__ == '__main__':
    run_code()
