import json
import logging
import os
import time
from controllers.tasks.Task import Task
from managers.FileParameters import FileParameters
from managers.QueueManager import QueueManager


class FileCaptureSlowTask(Task):

    def prepareImpl(self, config=None):
        pass

    def doTaskImpl(self):

        self.running = True

        while self.running:

            try:
                fileStats = QueueManager.getItemFromQueue('slow')

                filename = fileStats['filename']
                file_type = fileStats['type']
                action = fileStats['action']

                file_dict = dict()

                if os.path.exists(filename):
                    timer = 10

                    #TODO review this line
                    sha256 = FileParameters.get_sha256(filename, timer)

                    time.sleep(2)

                    if sha256:
                        file_dict['type'] = 'file_capture'
                        file_dict['endpoint_uuid'] = str(Task.client_id)
                        file_dict['namespace_uuid'] = str(Task.client_id)
                        file_dict['action'] = action
                        file_dict['filepath'] = filename
                        file_dict['file_extension'] = os.path.splitext(filename)[1]
                        file_dict['filename'] = os.path.basename(filename)
                        file_dict['sha256'] = sha256


                    if file_type != None and file_type != 'None':
                        file_dict['file_type'] = file_type

                    md5_hash = FileParameters.get_md5(filename, timer)

                    if md5_hash:
                        file_dict['md5'] = md5_hash

                    acl = FileParameters.get_acl(filename)

                    if acl != None:
                        file_dict['acl'] = acl

                    file_dict['timestamp'] = int(time.time())
                    string_binnacle = json.dumps(file_dict)

                    logging.getLogger('binnacle').info(string_binnacle)
                    QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_binnacle})

                else:
                    logging.getLogger('application').info('File {0} not exists'.format(filename))

            except Exception:
                continue
    def shutdownImpl(self):
        self.running = False
