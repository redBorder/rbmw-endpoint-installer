import json
import logging
import time

import wmi
import pythoncom

from controllers.tasks.Task import Task

from managers.QueueManager import QueueManager


class DeletionProcessTask(Task):


    def prepareImpl(self, config=None):
        pass


    def doTaskImpl(self):

        self.running = True

        try:
            pythoncom.CoInitialize()

            connection = wmi.WMI()
            watcher = connection.Win32_Process.watch_for("deletion")

            while self.running:
                try:
                    deletedProcess = watcher()

                    #obtenemos informacion necesaria del proceso y la metemos en la bitacora
                    bitacora_string = dict()
                    bitacora_string['namespace_uuid'] = str(Task.client_id)
                    bitacora_string['endpoint_uuid'] = str(Task.client_id)
                    bitacora_string['type'] = 'process'
                    bitacora_string['action'] = 'deletion'
                    bitacora_string['name'] = deletedProcess.Caption
                    bitacora_string['pid'] = deletedProcess.ProcessID
                    bitacora_string['timestamp'] = int(time.time())

                    string_json = json.dumps(bitacora_string)
                    logging.getLogger('binnacle').info(string_json)
                    QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_json})
                except Exception:
                    continue

        except Exception as e:
            logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()


    def shutdownImpl(self):
        self.running = False
