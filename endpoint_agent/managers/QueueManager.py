from multiprocessing import Queue

import logging

# Static class for queue management
class QueueManager():

    # created queues
    queues = dict()


    # method to create a new queue with key
    @staticmethod
    def createQueue(key):
        if not key in QueueManager.queues:
            QueueManager.queues[key] = Queue()
            logging.getLogger('application').info("Created new queue with key: \'%s\'", key)


    # method to put data in queue with key
    @staticmethod
    def putOnQueue(key, data):
        if key in QueueManager.queues:
            QueueManager.queues[key].put(data)
            logging.getLogger('application').debug("Added new data to queue with key: \'%s\'", key)
            logging.getLogger('application').debug("Data value : %s", data)
        else:
            logging.error("key \'%s\' not found!", key)
            raise QueueManagerException(key)


    # method to know if a queue with key is empty
    @staticmethod
    def isEmpty(key):
        if key in QueueManager.queues:
            logging.getLogger('application').debug("Checking size of queue with key: \'%s\'", key)
            return QueueManager.queues[key].empty()
        else:
            logging.getLogger('application').error("key \'%s\' not found!", key)
            raise QueueManagerException(key)


    # method to get data from a queue with key
    @staticmethod
    def getItemFromQueue(key):
        if key in QueueManager.queues:
            logging.getLogger('application').debug("Get item from queue with key: \'%s\'", key)
            return QueueManager.queues[key].get()
        else:
            logging.getLogger('application').error("key \'%s\' not found!", key)
            raise QueueManagerException(key)


    # method to get queue with key
    @staticmethod
    def getQueue(key):
        if key in QueueManager.queues:
            logging.getLogger('application').debug("Get queue with key: \'%s\'", key)
            return QueueManager.queues[key]
        else:
            logging.getLogger('application').error("key \'%s\' not found!", key)
            raise QueueManagerException(key)



class QueueManagerException(Exception):

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return "%s not found!" % repr(self.key)