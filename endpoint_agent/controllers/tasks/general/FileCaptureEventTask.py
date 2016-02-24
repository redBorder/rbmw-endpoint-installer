import logging
import os
import json
from controllers.tasks.Task import Task
from managers.FilterManager import FilterManager
from managers.QueueManager import QueueManager


class FileCaptureEventTask(Task):

    def prepare(self, config=None):
        pass


    def doTaskImpl(self):
        self.running = True

        while self.running:

            try:
                # sacamos un trabajo de la cola, si esta vacia se queda bloqueado hasta que la cola deja de estar vacia.
                event = QueueManager.getItemFromQueue('file_event')

                for elements in event:
                    # en elemts[0] estara el tipo de evento del 1-5.
                    # lo que haremos es que dependiendo del tipo de evento sacaremos un log a la bitacora distinto.
                    if elements[0] == 2:
                        valor = FilterManager.get_filter_path(elements[1])
                        if valor == False:
                            bitacora_string = dict()
                            bitacora_string['namespace_uuid'] = Task.client_id
                            bitacora_string['endpoint_uuid'] = Task.client_id
                            bitacora_string['type'] = 'file_information'
                            bitacora_string['filename'] = elements[1]
                            bitacora_string['action'] = 'deleted'
                            json_string = json.dumps(bitacora_string)
                            kafka_dict = dict()
                            kafka_dict['topic'] = 'rb_ioc'
                            kafka_dict['content'] = json_string
                            logging.getLogger('binnacle').info(json_string)
                            QueueManager.putOnQueue('kafka', kafka_dict)
                            # TODO review this line
                            # bitacoraEnrichment(bitacora_string)
                    if elements[0] == 4:
                        valor = FilterManager.get_filter_path(elements[1])
                        if valor == False:
                            bitacora_string = dict()
                            bitacora_string['namespace_uuid'] = Task.client_id
                            bitacora_string['endpoint_uuid'] = Task.client_id
                            bitacora_string['type'] = 'file_information'
                            action = 'file ' + elements[1] +' renamed to '
                    if elements[0] == 5:
                        valor = FilterManager.get_filter_path(elements[1])
                        if valor == False and (os.path.isfile(elements[1]) or os.path.isdir(elements[1])):
                            action += elements[1]
                            bitacora_string['filename'] = elements[1]
                            bitacora_string['action'] = action
                            json_string = json.dumps(bitacora_string)
                            kafka_dict = dict()
                            kafka_dict['topic'] = 'rb_ioc'
                            kafka_dict['content'] = json_string
                            logging.getLogger('binnacle').info(json_string)
                            QueueManager.putOnQueue('kafka', kafka_dict)
            except:
                logging.getLogger('application').info('Error to get event from queue')
                continue

    def shutdownImpl(self):
        self.running = False

