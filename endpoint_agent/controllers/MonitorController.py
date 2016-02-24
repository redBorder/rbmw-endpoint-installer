from concurrent.futures import ThreadPoolExecutor
import logging

class MonitorController():

    # Constructor
    def __init__(self):
        self.executorService = ThreadPoolExecutor(max_workers=100)
        self.workerList = list()
        logging.getLogger('application').info("Created new monitor controller")


    # Reload monitor controller
    def reload(self):
        pass


    # Run single task
    def runTask(self, task, replication=1):
        # Deploy task with replication

        task.prepare()

        for replica in range(replication):
            self.workerList.append(self.executorService.submit(task.doTask))
            logging.getLogger('application').info("Worker for task {0} created".format(repr(task.getTaskName())))


    # Get result from every worker and return a list
    def getWorkersResult(self):
        results = list()
        for worker in self.workerList:
            results.append(worker.result())

        return results


    def stopWorkers(self):

        logging.getLogger('application').info("Stopping workers")

        up_workers = len(self.workerList)
        down_workers = 0

        for worker in self.workerList:
            worker.cancel()
            down_workers += 1

        logging.getLogger('application').info("Stopped %d of %d workers", down_workers, up_workers)


    def getWorkersStatus(self):
        pass
