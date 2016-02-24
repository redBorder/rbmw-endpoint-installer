from kafka import KafkaClient
from kafka import KeyedProducer
from kafka import HashedPartitioner

import time
import logging


class KafkaManager():


    # constructor
    def __init__(self, kafkaConfig):
        self.kafkaConfig = kafkaConfig
        self.init()
        logging.getLogger('application').info("Init new kafka manager")


    # init kafka producer
    def init(self):
        flag = False
        while flag == False:
            try:
                self.kafkaClient = KafkaClient(self.kafkaConfig['broker_kafka'])
                logging.getLogger('application').info("Connect with broker: {0}".format(self.kafkaConfig['broker_kafka']))

                logging.getLogger('application').info("Init new producer")
                self.kafkaProducer = KeyedProducer(self.kafkaClient, partitioner=HashedPartitioner, async=False)
                flag = True
            except Exception:
                logging.getLogger('application').info("Kafka server connect failed")
                time.sleep(5)
                continue



    # send message with or without key to topic
    def sendMessage(self, msg, topic, key=None):
        logging.getLogger('application').debug("Sending message to topic: %s", repr(topic))
        flag = False
        while flag == False:
            try:
                self.kafkaProducer.send_messages(topic, bytes(key, 'utf-8'), bytes(msg, 'utf-8'))
                flag = True
            except Exception:
                logging.getLogger('application').info("error to send message to kafka")
                time.sleep(0.5)
                continue

