import logging
import sys

from controllers.tasks.Task import Task
from managers.KafkaManager import KafkaManager

from managers.QueueManager import QueueManager

class KafkaSenderTask(Task):


    def prepareImpl(self):

        # create new kafka manager
        try:
            self.kafkaManager = KafkaManager(self.configuration)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.getLogger('application').error(e)

        # set flag to true
        self.running = True


    def doTaskImpl(self):
        try:
            while self.running:
                message = QueueManager.getItemFromQueue('kafka')
                logging.getLogger('application').debug('Received message : {0}'.format(message))
                self.kafkaManager.sendMessage(key=Task.client_id, msg=message['content'], topic=message['topic'])
        except Exception as e:
            logging.getLogger('application').error(e)


    def shutdownImpl(self):
        self.running = False