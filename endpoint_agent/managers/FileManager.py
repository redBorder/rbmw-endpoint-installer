import logging
import os


# Static class for file management
class FileManager():

    # modes
    WRITE_MODE = 'w'
    READ_MODE = 'r'
    APPEND_MODE = 'a'
    WRITE_BINARY_MODE = 'wb'
    READ_BINARY_MODE = 'rb'

    # dict of files
    openedfiles = dict()

    # method to open files and add to dict
    @staticmethod
    def openFile(path, key, mode):

        if key and path and mode:
            if not key in FileManager.openedfiles:
                file = open(path, mode=mode)
                FileManager.openedfiles[key] = file
                logging.getLogger('application').info("Created new file with key \'%s\' and mode \'%s\' in path \'%s\'", key, mode, path)
            else:
                logging.getLogger('application').error("Key \'%s\' exist", key)
        elif path and mode and not key:
            return open(path, mode=mode)


    # method to close file with key
    @staticmethod
    def closeFile(key):
        if key in FileManager.openedfiles:
            FileManager.openedfiles[key].close()
            FileManager.openedfiles.__delitem__(key)
            logging.getLogger('application').info("Closed file with key \'%s\'", key)
        else:
            logging.getLogger('application').error("Key \'%s\' not found", key)
            raise FileManagerException(key)


    # method to write to file with key
    @staticmethod
    def writeInFile(key, msg):
        if key in  FileManager.openedfiles:
            FileManager.openedfiles[key].write("%s\n" % msg)
            logging.getLogger('application').info("Write new message in file with key: \'%s\'", key)
            logging.getLogger('application').debug("Message: %s", msg)
        else:
            logging.getLogger('application').error("Key \'%s\' not found", key)
            raise FileManagerException(key)


    # method to read from file with key
    @staticmethod
    def readFileContent(key):
        if key in FileManager.openedfiles:
            logging.getLogger('application').info("Readed content from file with key: \'%s\'", key)
            return FileManager.openedfiles[key].read()
        else:
            logging.getLogger('application').error("Key \'%s\' not found", key)
            raise FileManagerException(key)

    # method to read from file with key
    @staticmethod
    def readFileContentLines(key):
        if key in FileManager.openedfiles:
            logging.getLogger('application').info("Readed content from file with key: \'%s\'", key)
            return FileManager.openedfiles[key].readlines()
        else:
            logging.getLogger('application').error("Key \'%s\' not found", key)
            raise FileManagerException(key)

    # method to get file descriptor with key
    @staticmethod
    def getFileDescriptor(key):
        if key in FileManager.openedfiles:
            logging.getLogger('application').info("Getted file descriptor with key: \'%s\'", key)
            return FileManager.openedfiles[key]
        else:
            logging.getLogger('application').error("Key \'%s\' not found", key)
            raise FileManagerException(key)


    # method to get file status
    # return:
    #   st_mode         :    File mode
    #   st_ino          :     Inode number
    #   st_dev          :     Identifier of the device on which this file resides.
    #   st_nlink        :   Number of hard links.
    #   st_uid          :     User identifier of the file owner.
    #   st_gid          :     Group identifier of the file owner.
    #   st_size         :    Size of the file in bytes
    #   st_atime        :   Time of most recent access expressed in seconds
    #   st_mtime        :   Time of most recent content modification expressed in seconds.
    #   st_ctime        :   Platform dependent
    #                           * the time of most recent metadata change on Unix
    #                           * the time of creation on Windows, expressed in seconds
    #   st_atime_ns     :   Time of most recent access expressed in nanoseconds as an integer
    #   st_mtime_ns     :   Time of most recent content modification expressed in nanoseconds as an integer
    #   st_ctime_ns     :   Platform dependent
    #                           * the time of most recent metadata change on Unix
    #                           * the time of creation on Windows, expressed in nanoseconds as an integer
    @staticmethod
    def getFileInfo(path=None, key=None):

        if key:
            if key in FileManager.openedfiles:
                fileDescriptor = FileManager.openedfiles[key]
                return os.fstat(fileDescriptor)
        elif path:
            return os.stat(path)

    # method to close all opened files
    @staticmethod
    def closeAllFiles():
        if bool(FileManager.openedfiles):
            logging.getLogger('application').info("Close all files ...")
            for fileKey in FileManager.openedfiles:
                FileManager.openedfiles[fileKey].close()
                logging.getLogger('application').info("Closed file with key: \'%s\'", fileKey)

            FileManager.openedfiles.clear()


class FileManagerException(Exception):

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return "%s not found!" % repr(self.key)
