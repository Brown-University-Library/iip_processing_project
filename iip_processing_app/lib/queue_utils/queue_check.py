"""
Under construction.

This code checks that expected queues exist and that expected workers are running.
"""

expectation = {
    'queues': [ 'aa', 'bb', 'cc' ],
    'workers': [ 'xx', 'yy', 'zz']
}

import subprocess

def get_rqinfo():
    # Run the rqinfo command and get the output
    result = subprocess.run(['rqinfo'], stdout=subprocess.PIPE)
    output = result.stdout.decode()

    # Split the output into lines
    lines = output.split('\n')

    # Initialize empty lists for queues and workers
    queues = []
    workers = []

    # Iterate over each line in the output
    for line in lines:
        if line.strip() == '':
            continue

        # If line contains queue info, add it to the queues list
        if '|' in line:
            queue_name = line.split('|')[0].strip()
            queues.append(queue_name)

        # If line contains worker info, add it to the workers list
        if 'idle:' in line:
            worker_name = line.split(' ')[0].strip()
            workers.append(worker_name)

    return queues, workers

if __name__ == '__main__':
    queues, workers = get_rqinfo()
    print('Queues:', queues)
    print('Workers:', workers)
