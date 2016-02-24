import os
import re
from managers.FileManager import FileManager

class FilterManager():

    configuration = None
    path_filter_list = ['PyCharm50','System Volume Information','SPP','TREN', "endpoint",'config', 'ntuser', 'AppData', 'Temp', 'AVG2015', 'repository', 'ProgramData', 'Windows', 'Recycle', 'NTUSER', 'Config', 'Program Files', 'version', 'RECYCLE']
    type_filter_list = []

    @staticmethod
    def load_config(config, path):
        FilterManager.configuration = config.getConfigProperties()
        filter_type = os.path.join(path, 'filters', "filter_type.txt")
        path_filter = os.path.join(path, 'filters', "path.txt")
        FileManager.openFile(filter_type, 'type_filter', FileManager.READ_MODE)
        FileManager.openFile(path_filter, 'path_filter', FileManager.READ_MODE)
        content_type = FileManager.readFileContentLines('type_filter')
        content_path = FileManager.readFileContentLines('path_filter')

        for line in content_type:
            words = line.split()[0]
            FilterManager.type_filter_list.append(words)

        for lines in content_path:
            word_line = lines.split()[0]
            word_line.replace("\\", "\\\\")
            FilterManager.path_filter_list.append(word_line)

    @staticmethod
    def get_parameter(parameter):
        return FilterManager.configuration[parameter]

    @staticmethod
    def get_filter_type(type_string):
        match = False
        #se comprueba que no este filtrado por ruta el evento asociado a un directorio
        for element in FilterManager.type_filter_list:
            try:
                if element == type_string:
                    match = True
            except:
                match = False
        return match

    @staticmethod
    def get_filter_path(filename):
        match = False
        #se comprueba que no este filtrado por ruta el evento asociado a un directorio
        for element in FilterManager.path_filter_list:
          if re.search(element, filename):
            match = True

        return match


    @staticmethod
    def get_tamanio_filter(filename):
        match = False
        tamanio_config = int(FilterManager.get_parameter('file_size'))
        tamanio = os.stat(filename).st_size
        if tamanio:
            if tamanio > tamanio_config:
                match = True
        else:
            match = "error"

        return match
