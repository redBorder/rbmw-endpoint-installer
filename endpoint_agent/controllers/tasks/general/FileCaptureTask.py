import json
import logging
import os
import time
from controllers.tasks.Task import Task
from managers.CacheManager import CacheManager
from managers.FileParameters import FileParameters
from managers.FilterManager import FilterManager
from managers.S3Manager import S3Manager
from managers.WindowsValueManager import WindowsValueManager
from managers.QueueManager import QueueManager


class FileCaptureTask(Task):

    def prepareImpl(self):
        pass

    def doTaskImpl(self):
        try:
            self.running = True

            while self.running:
                try:
                    fileStats = QueueManager.getItemFromQueue('file_capture')

                    filename = fileStats['filename']
                    action = fileStats['action']

                    if (os.path.exists(filename) and os.path.isfile(filename)):
                        self.treatFile(filename, action)
                        time.sleep(0.5)
                    elif (os.path.isdir(filename) and os.path.exists(filename)):

                        for dirpath, dirnames, filenames in os.walk(filename):

                            for files in filenames:
                                path = os.path.join(dirpath, files)

                                if os.path.exists(path):
                                    self.treatFile(path, action)
                                    time.sleep(0.5)
                except:
                    continue
        except Exception as e:
            logging.getLogger("application").info(str(e))
            pass


    def shutdownImpl(self):
        self.running = False


    def treatFile(self, filename, action):
        if os.path.exists(filename):
            timer = 2
            self.file_open(filename, timer)

            tamanio_result = FilterManager.get_tamanio_filter(filename)
            type_file = FileParameters.get_file_type(filename)
            time.sleep(1)

            # TODO review this line
            result_type = FilterManager.get_filter_type(type_file)
            if result_type == True or tamanio_result == True:
                file_slow_queue = dict()
                file_slow_queue['filename'] = filename
                file_slow_queue['action'] = action
                file_slow_queue['type'] = type_file
                QueueManager.putOnQueue('slow', file_slow_queue)
            else:
                bitacora_dict = dict()
                sha256 = FileParameters.get_sha256(filename, timer)
                time.sleep(2)

                if sha256 != None:
                    bitacora_dict['type'] = 'file_capture'
                    bitacora_dict['endpoint_uuid'] = str(Task.client_id)
                    bitacora_dict['namespace_uuid'] = str(Task.client_id)
                    bitacora_dict['action'] = action
                    bitacora_dict['filepath'] = filename
                    bitacora_dict['file_extension'] = os.path.splitext(filename)[1]
                    bitacora_dict['filename'] = os.path.basename(filename)
                    bitacora_dict['sha256'] = sha256

                if type_file != None and type_file != 'None':
                    bitacora_dict['file_type'] = type_file

                md5_hash = FileParameters.get_md5(filename, timer)
                if md5_hash != None:
                    bitacora_dict['md5'] = md5_hash

                acl = FileParameters.get_acl(filename)
                if acl != None:
                    bitacora_dict['acl'] = acl

                find_new = CacheManager.checkIfExists(sha256)
                if find_new == False:
                    result_s3 = S3Manager.upload_s3(filename, sha256)
                    if result_s3 == 'error_copy':
                        logging.getLogger('application').info('Error to create a temporally file to upload to S3')
                    elif result_s3 == 'error_upload':
                        logging.getLogger('application').info('Error to upload {0} to S3'.format(repr(filename)))
                    elif result_s3 == 'upload':
                        score = -1
                        bitacora_dict['cache_score'] = score
                        logging.getLogger('application').info('{0} uploaded to S3'.format(filename))
                        self.enrichment(filename, sha256, score)
                        time.sleep(1)
                else:
                        #si el fichero ya fue visto antes indicamos en la bitacora que fue visto poniendo si es limpio o malware y enviamos a kafka.
                    score = CacheManager.get_score(sha256)
                    if score != 1000:
                        bitacora_dict['cache_score'] = score
                        self.enrichment(filename, sha256, score)

                bitacora_dict['timestamp'] = int(time.time())

                string_json = json.dumps(bitacora_dict)

                logging.getLogger('binnacle').info(string_json)
                logging.getLogger('application').debug('Sending kafka info : {0}'.format(string_json))

                QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_json})

    def file_open(self,filename, tiempo):
        flag = False
        count = 0
        while (count < 50) and (flag == False):
            try:
                file_open = open(filename, 'rb')
                flag = True
                file_open.close()
            except:
                time.sleep(tiempo)
                count += 1
                file_open.close()
                continue


    # TODO review this method
    def enrichment(self, filename, sha256, score):
        values = WindowsValueManager.get_values()
        name_file = os.path.basename(filename)
        values['file_uri'] = filename
        values['file_name'] = name_file
        values['hash'] = sha256
        values['action'] = 'forward'
        values['timestamp'] = int(time.time())

        if score != 1000:
            values['score'] = score

        message = json.dumps(values)

        string_queue = dict()
        string_queue['content'] = message
        string_queue['topic'] = 'rb_endpoint'

        QueueManager.putOnQueue('kafka', string_queue)