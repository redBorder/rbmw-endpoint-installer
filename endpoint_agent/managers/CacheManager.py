import requests
import logging

from concurrent.futures import ThreadPoolExecutor

import time
import sqlite3
import os

class CacheManager():

    URL_REPUTATION_TOTAL = "http://{0}/reputation/{1}/malware/total{2}"
    URL_REPUTATION_INCREMENTAL = "http://{0}/reputation/{1}/malware/incremental"
    URL_REPUTATION_INCREMENTAL_LIST = "http://{0}/reputation/{1}/malware/incremental/{2}{3}"

    DATABASE_NAME = 'cache.db'

    # path where cache saves information
    path_cache = None

    # running cache manager
    running = False

    # server address
    url_server = None

    # cache version
    version = None

    # connection to sqlite
    dbConnection = None

    # lastest incremental list query
    last_incremental_query = 'r.i'

    # init local cache with config file
    @staticmethod
    def initCache(config):
        logging.getLogger('application').info("Init cache client")
        # load configuration
        CacheManager.url_server = config['cache_direction']
        CacheManager.version = config['version_cache']
        rootPath = os.path.abspath(os.path.dirname(__file__)).rstrip('endpoint_agent/managers')

        CacheManager.dbConnection = sqlite3.connect(os.path.join(rootPath, 'db', CacheManager.DATABASE_NAME), check_same_thread=False)

        if CacheManager.dbConnection:
            logging.getLogger('application').debug("Connected to local cache database: {0}".format(CacheManager.DATABASE_NAME))
            CacheManager.dbConnection.cursor().execute('CREATE TABLE IF NOT EXISTS cache (hash text PRIMARY KEY, score integer)')
            CacheManager.dbConnection.commit()


    @staticmethod
    def start():

        CacheManager.running = True
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(CacheManager.doPetitions)

        logging.getLogger('application').info("Started cache client!")

    @staticmethod
    def doPetitions():
        logging.getLogger('application').debug("Doing total petition to remote cache")
        # first time get total with filter hash
        CacheManager.getTotal("hash")

        logging.getLogger('application').debug("Doing incremental petition to remote cache")
        # first time get incremental
        CacheManager.getIncremental("hash")

        # every X seconds get incremental with filter hash
        while CacheManager.running and not time.sleep(900):
            CacheManager.getIncremental("hash")
            logging.getLogger('application').debug("Do incremental petition to remote cache")



    @staticmethod
    def getTotal(filter):
        # build url
        url = CacheManager.URL_REPUTATION_TOTAL.format(CacheManager.url_server, CacheManager.version, "/%s" % filter if filter else "")

        try:
            response = requests.get(url)

            logging.getLogger('application').debug("Response in total petition : {0}".format(response.status_code))

            if response.status_code is 200:

                data = response.json()['data']

                for entry in data:
                    hashValue = entry['hash']
                    scoreValue = entry['score']
                    CacheManager.dbConnection.cursor().execute('INSERT OR REPLACE INTO cache VALUES ({0},{1})'.format(repr(hashValue), scoreValue))
                    CacheManager.dbConnection.commit()
                    logging.getLogger('application').debug("Updated database : hash {0} with score {1}.".format(repr(hashValue), scoreValue))

                logging.getLogger('application').info("Updated local cache database with total list")
            else:
                logging.getLogger('application').warning("Unable to get total list from : {1}".format(CacheManager.url_server))

        except:
            logging.getLogger('application').error('Error to get total list from remote cache')


    @staticmethod
    def getIncremental(filter):

        url = CacheManager.URL_REPUTATION_INCREMENTAL.format(CacheManager.url_server, CacheManager.version)

        try:
            response = requests.get(url)

            logging.getLogger('application').debug("Response in last incremental petition : {0}".format(response.status_code))

            if response.status_code is 200:

                lastRelease = response.json()['last_release']

                if not lastRelease == CacheManager.last_incremental_query and not CacheManager.last_incremental_query == '0.0':

                    CacheManager.last_incremental_query = lastRelease

                    url = CacheManager.URL_REPUTATION_INCREMENTAL_LIST.format(CacheManager.url_server, CacheManager.version, lastRelease, "/%s" % filter if filter else "")

                    response = requests.get(url)

                    logging.getLogger('application').debug("Response in incremental list petition : {0}".format(response.status_code))

                    if response.status_code is 200:

                        data = response.json()['data']

                        for entry in data:
                            hashValue = entry['hash']
                            scoreValue = entry['score']

                            CacheManager.dbConnection.cursor().execute('INSERT OR REPLACE INTO cache VALUES ({0},{1})'.format(repr(hashValue), scoreValue))
                            CacheManager.dbConnection.commit()
                            logging.getLogger('application').debug("Updated database incremental list {0} : hash {1} with score {2}".format(repr(lastRelease), repr(hashValue), str(scoreValue)))

                        logging.getLogger('application').info("Updated local cache database with incremental list : {0}".format(repr(lastRelease)))
        except:
            logging.getLogger('application').error('Error to get incremental list from remote cache')


    @staticmethod
    def get_score(hashvalue):
        try:
            cursor = CacheManager.dbConnection.cursor()

            cursor.execute('SELECT score FROM cache WHERE hash=?', (hashvalue,))

            result = cursor.fetchone()

            if result:
                logging.getLogger('application').debug("Result for hash {0} : {1}".format(hashvalue, result[0]))
                return result[0]
            else:
                logging.getLogger('application').debug("Results not found for hash %s" % hashvalue)
        except:
            logging.getLogger('application').error("Error to query hash {0}".format(hashvalue))
            return 1000


    @staticmethod
    def checkIfExists(hashvalue):
        cursor = CacheManager.dbConnection.cursor()

        cursor.execute("SELECT EXISTS(SELECT 1 FROM cache WHERE hash={0} LIMIT 1)".format(repr(hashvalue)))

        result = cursor.fetchone()[0]

        if bool(result):
            logging.getLogger('application').debug("Value {0} exists in database".format(hashvalue))
        else:
            logging.getLogger('application').debug("Value {0} doesn't exists in database".format(hashvalue))

        return bool(result)
