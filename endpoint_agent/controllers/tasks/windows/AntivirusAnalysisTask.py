import json
import logging
import time
import wmi
from controllers.tasks.Task import Task
from managers.QueueManager import QueueManager
import pythoncom


class AntivirusAnalysisTask(Task):


    def prepareImpl(self, config=None):
        pass


    def doTaskImpl(self):


        pythoncom.CoInitialize()
        self.running = True

        try:
            connection = wmi.WMI()

            # Init connection with {W}indows {M}anagement {I}nstrumentation

            # Antivirus list
            antivirusList = ["McAFee"]

            # Do loop each 60 seconds
            while self.running==True:

                try:
                    for antivirus in antivirusList:

                        logging.getLogger('application').debug("Do analysis for antivirus : {0}".format(antivirus))

                        bitacora_string = dict()
                        bitacora_string['namespace_uuid'] = Task.client_id
                        bitacora_string['endpoint_uuid'] = Task.client_id
                        bitacora_string['type'] = 'antivirus'
                        bitacora_string['antivirus'] = antivirus
                        bitacora_string['status'] = 'not installed'

                        for services in connection.Win32_Service():
                            if antivirus in services.Caption:
                                bitacora_string['antivirus'] = services.Caption
                                bitacora_string['status'] = services.State
                                bitacora_string['mode'] = 'Windows Service'


                        for startup_program in connection.Win32_StartupCommand():
                            if antivirus in startup_program.Caption:
                                bitacora_string['antivirus'] = startup_program.Caption
                                bitacora_string['status'] = 'Running'
                                bitacora_string['mode'] = 'Startup Windows Program'

                        bitacora_string['timestamp'] = int(time.time())

                        string_json = json.dumps(bitacora_string)

                        logging.getLogger('binnacle').info(string_json)

                        QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_json})

                    time.sleep(60)

                except Exception:
                    continue

        except Exception as e:
                logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()

    def shutdownImpl(self):
        self.running = False
