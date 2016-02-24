import os, sys
import logging.config
from config.Config import Config
from controllers.MonitorController import MonitorController
from managers.CacheManager import CacheManager
from managers.WindowsValueManager import WindowsValueManager
from controllers.tasks.general.KafkaSenderTask import KafkaSenderTask
from controllers.tasks.general.FileCaptureEventTask import FileCaptureEventTask
from controllers.tasks.general.FileCaptureSlowTask import FileCaptureSlowTask
from controllers.tasks.general.FileCaptureTask import FileCaptureTask
from controllers.tasks.windows.CreationProcessTask import CreationProcessTask
from controllers.tasks.windows.WebProcessTask import WebProcessTask
from controllers.tasks.windows.DeletionProcessTask import DeletionProcessTask
from controllers.tasks.windows.AntivirusAnalysisTask import AntivirusAnalysisTask
from controllers.tasks.windows.MonitorDiskPartition import MonitorDiskPartition
from managers.QueueManager import QueueManager
from managers.FilterManager import FilterManager
from managers.FileParameters import FileParameters
from managers.S3Manager import S3Manager

S3_FOLDER_NAME = "s3"
LOGS_FOLDER_NAME = "logs"
CONFIG_FOLDER_NAME = "config"
DATABASES_FOLDER_NAME = "db"

class endpoint_agent():

        def main(self):

            # init logging system
            self.initLog()

            # check if environment is completed
            self.initEnvironment()

            rootPath = os.path.abspath(os.path.dirname(__file__)).rstrip('endpoint_agent')

            # main thread configuration
            configuration = Config(path=os.path.join(rootPath, 'config/parameters.yaml'))

            # init windows variables
            self.initWindowsValues()

            # init file parameters
            self.initFileParametersConfig()

            # init s3 configuration
            self.S3Config(configuration)

            # init filter list
            self.initFilterLists(configuration)

            # create queues
            QueueManager.createQueue('slow')
            QueueManager.createQueue('file_event')
            QueueManager.createQueue('kafka')
            QueueManager.createQueue('file_capture')

            # init cache manager
            CacheManager.initCache(configuration.getConfigProperties())
            CacheManager.start()

            # create monitor controller
            controller = MonitorController()

            # running task kafka sender
            kafkaTask = KafkaSenderTask(taskName='KafkaSender', config=configuration.getConfigProperties())
            controller.runTask(kafkaTask)

            # running task antivirus analysis
            antivirusAnalysis = AntivirusAnalysisTask(taskName='AntivirusAnalysis', config=configuration.getConfigProperties())
            controller.runTask(antivirusAnalysis)

            # running task creation process
            creationProcess = CreationProcessTask(taskName='creationProcess')
            controller.runTask(creationProcess)

            # running task deletion process
            deletionProcess = DeletionProcessTask(taskName='deletionProcess')
            controller.runTask(deletionProcess)

            # running task web process
            webProcess = WebProcessTask(taskName='webProcess')
            controller.runTask(webProcess)

            # runnning task file capture slow
            slowTask = FileCaptureSlowTask(taskName='slowTask')
            controller.runTask(slowTask)

            # running task file capture
            normalTask = FileCaptureTask(taskName='normalTask')
            controller.runTask(normalTask)

            normalTask_2 = FileCaptureTask(taskName='normalTask_2')
            controller.runTask(normalTask_2)

            normalTask_3 = FileCaptureTask(taskName='normalTask_3')
            controller.runTask(normalTask_3)

            # running task file capture event
            eventTask = FileCaptureEventTask(taskName='eventTask')
            controller.runTask(eventTask)

            # runnning task monitor process
            monitorProcess = MonitorDiskPartition(taskName='MonitorProcess')
            controller.runTask(monitorProcess)

        def initEnvironment(self):

            # get aboslute path
            rootPath = os.path.dirname(__file__)

            # create path for s3
            path_s3 = os.path.join(rootPath, S3_FOLDER_NAME)

            # check if exist path for s3
            if not os.path.exists(path_s3):
                os.mkdir(path_s3)
                logging.getLogger('application').info("Created new folder : {0}".format(path_s3))

            # create path for logs
            path_logs = os.path.join(rootPath, LOGS_FOLDER_NAME)

            # check if exist path for logs
            if not os.path.exists(path_logs):
                os.mkdir(path_logs)
                logging.getLogger('application').info("Created new folder : {0}".format(path_logs))

            # create path for databases
            path_cache = os.path.join(rootPath, DATABASES_FOLDER_NAME)

            # check if exist path for databases
            if not os.path.exists(path_cache):
                os.mkdir(path_cache)
                logging.getLogger('application').info("Created new folder : {0}".format(path_cache))


        def initLog(self):
            rootPath = os.path.abspath(os.path.dirname(__file__)).rstrip('endpoint_agent')
            logging.config.fileConfig(os.path.join(rootPath, 'config/logconf.conf'))

        def initWindowsValues(self):
            WindowsValueManager.set_values()

        def initFilterLists(self, config):
            path = os.path.abspath(os.path.dirname(__file__))
            FilterManager.load_config(config, path)

        def S3Config(self, config):
            path = os.path.abspath(os.path.dirname(__file__))
            S3Manager.load_config(config, path)

        def initFileParametersConfig(self):
            path = os.path.abspath(os.path.dirname(__file__))
            FileParameters.config(path)


if __name__ == '__main__':
    try:
        endpoint_object = endpoint_agent()
        endpoint_object.main()
    except KeyboardInterrupt:
        logging.getLogger('application').info("endpoint agent closing")
        sys.exit(0)


