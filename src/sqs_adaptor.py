import boto3
import logging

# tell boto to pipe down
logging.getLogger('botocore').setLevel(logging.WARN)
logging.getLogger('boto3').setLevel(logging.WARN) # CRITICAL)

LOG = logging.getLogger(__name__)

def conn():
    return boto3.resource('sqs')

def poll(queue_obj):
    """an infinite poll on the given queue object.
    blocks for 20 seconds before connection is dropped and re-established"""
    while True:
        messages = []
        while not messages:
            messages = queue_obj.receive_messages(
                MaxNumberOfMessages=1,
                VisibilityTimeout=60, # time allowed to call delete, can be increased
                WaitTimeSeconds=20 # maximum setting for long polling
            )
        message = messages[0]
        yield message.body
        message.delete()

class IncomingQueue(object):
    def __init__(self, queue_name):
        self.queue = conn().get_queue_by_name(QueueName=queue_name)

    def __iter__(self):
        """an infinite poll on the given queue object.
        blocks for 20 seconds before connection is dropped and re-established"""
        while True:
            messages = []
            while not messages:
                messages = self.queue.receive_messages(
                    MaxNumberOfMessages=1,
                    VisibilityTimeout=60, # time allowed to call delete, can be increased
                    WaitTimeSeconds=20 # maximum setting for long polling
                )
            LOG.debug("processing sqs message")
            message = messages[0]
            yield message.body
            message.delete()

    def close(self):
        # close the aws connection?
        pass

class OutgoingQueue(object):
    def __init__(self, queue_name):
        self.queue = conn().get_queue_by_name(QueueName=queue_name)

    def write(self, string):
        "called when given a validated response"
        self.queue.send_message(MessageBody=string)

    def error(self, string):
        "called when given an unroutable message"
        LOG.error("received unroutable message", extra={'unroutable-message': str(string)})

    def close(self):
        pass
