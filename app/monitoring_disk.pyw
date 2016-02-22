import os
import win32file
import win32con
import time
import threading
import wmi
import sys
import subprocess
from kafka.client import KafkaClient
from kafka.producer import SimpleProducer
from kafka import KafkaClient, KeyedProducer, HashedPartitioner, RoundRobinPartitioner
from endpoint_functions import *
from queue import Queue
import re
import pythoncom
import psutil
import json
import urllib
import urllib.parse
import urllib.request
import codecs
import yaml

def delete_files():
        path = os.path.abspath(os.path.dirname(__file__))
        path_config = os.path.join(path, "archivos")
        if os.path.exists(path_config):
                for dirpath, dirnames, filenames in os.walk(path_config):
                      for files in filenames:
                          path = os.path.join(dirpath, files)
                          if os.path.exists(path):
                                  try:
                                          os.remove(path)
                                  except:
                                          pass
        
        

#clase que comprueba de forma periodica si cierto programa antivirus esta activo
def search_antivirus(kafka_queue, bitacora_size, client_id):
        #se deja constancia en la bitacora el inicio de la clase
        bitacora_string = "Starting antivirus process"
        logs_function(bitacora_string)
        pythoncom.CoInitialize()
        #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
        exit_program = 1
        #Se obtiene la ruta del fichero desde el que se ordena parar el endpoint
        path = os.path.abspath(os.path.dirname(__file__))
        path_config = os.path.join(path, "configuration", "config.txt")
        #contador para realizar una funcionalidad cada cierto tiempo
        counter = 0
        try:
            c = wmi.WMI()
            while exit_program == 1:
                try:
                    if (counter == 0) or (counter == 300):
                        #variables que identifican el programa o servicio antimalware y que cambiaran de valor en caso que esten activos
                        #defender = 0
                        #ccleaner = 0
                        mcafee = 0
                        for services in c.Win32_Service():
                            #se obtienen los procesos de windows y se busca si coincide con los que buscamos.
                            #En caso afirmativo se deja constancia en bitacora del estado del mismo y se cambia el valor de las variables.
                            if "McAfee" in services.Caption:
                                service_state = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"antivirus\",\"antivirus\":\"" + str(services.Caption) + "\",\"status\":\"" + str(services.State) + "\",\"mode\":\"Windows Service\"}"
                                bitacora_writer('antivirus', service_state, kafka_queue, bitacora_size)
                                mcafee = 1
                            #elif "CCleaner" in services.Caption:
                            #    service_state = "\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"antivirus\",\"antivirus\":\"" + str(services.Caption) + "\",\"status\":\"" + str(services.State) + "\",\"mode\":\"Windows Service\"}"
                            #    bitacora_writer('antivirus', service_state, kafka_producer, bitacora_size)
                            #    ccleaner = 1
                                
                        for startup_program in c.Win32_StartupCommand():
                            #Se obtienen todos los programas que windows ejecuta al arrancar el sistema.
                            #En caso de coincidir con los antivirus que buscamos sabremos dicho programa se ejecuta al inicio, dejando constancia de ello en la bitacora.
                            if "McAfee" in startup_program.Caption:
                                program_state = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"antivirus\",\"antivirus\":\"" + str(startup_program.Caption) + "\",\"status\":\"Running\",\"mode\":\"Startup Windows Program\"}"
                                bitacora_writer('antivirus', program_state, kafka_queue, bitacora_size)
                                mcafee = 1

                        #En caso de no encontrar los antivirus que buscamos, debemos advertir a traves de la bitacora que no existen.        
                        if mcafee == 0:
                            program_state = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"antivirus\",\"antivirus\":\"McAfee\",\"status\":\"not installed\"}"
                            bitacora_writer('antivirus', program_state, kafka_queue, bitacora_size)
                            
                        #if ccleaner == 0:
                        #    program_state = "\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"antivirus\",\"antivirus\":\"CCleaner\",\"status\":\"stopped\",\"mode\":\"Startup Windows Program\"}"
                        #    bitacora_writer('antivirus', program_state, kafka_producer, bitacora_size)

                        #Si llegamos al minuto reiniciamos el contador.        
                        if counter == 300:
                            counter = 0
                except:
                    #En caso de que algun fallo sea capturado, comprobamos el contador.
                    if counter == 300:
                        counter = 0
                #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.         
                file_stop = open(path_config, 'r').readlines()
                for lines in file_stop:
                    if 'stop' in lines:
                        exit_program = 0
                        bitacora_string = "Exiting to antivirus process"
                        logs_function(bitacora_string)
                #aumentamos el contador.        
                counter += 1
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            raise
        except:	    
            raise
        finally:
            pythoncom.CoUninitialize ()
        

#Clase que periodicamente hace una consulta al Manager de Malware de redBorder y autoalimenta la cache local.
class local_cache(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        #Al ser la primera clase que se ejecuta del cargador, se crean los directorios necesarios para que el cargador funcione de forma correcta.
        error = create_directory()
        if error == 1:
            #se deja constancia en la bitacora el inicio de la clase
            bitacora_string = "Starting cache process"
            logs_function(bitacora_string)
        pythoncom.CoInitialize()
        #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
        exit_program = 1
        #Obtemos la ruta de los ficheros de parametros, de la cache y del fichero donde se ordenara parar el endpoint.
        path = os.path.abspath(os.path.dirname(__file__))
        path_config = os.path.join(path, "configuration", "config.txt")
        path_parameters = os.path.join(path, "configuration", "parameters.yaml")
        path_cache = os.path.join(path, "cache", "Malware_cache.txt")
        counter = 0
        try:
            while exit_program == 1 and error == 1:
                try:
                    delete_files()
                    error = 1
                    #cada 10 minutos realizaremos la consulta al Manager.
                    if (counter == 0) or (counter == 36000):
                        #leemos el fichero de parametros y buscamos la url del manager junto a la version de la cache.
                        file_open = open(path_parameters, 'r').read()
                        cache_parameters = yaml.load(file_open)
                        url_server = cache_parameters['cache_direction']
                        version = cache_parameters['version_cache']

                        #se construye la url completa        
                        url = "http://" + url_server + "/reputation/" + version + "/malware/total/hash"
                        #Se envia la peticion al manager y guardamos la respuesta completa en la variable data.
                        req = urllib.request.Request(url)
                        with urllib.request.urlopen(req) as response:
                            json_response = response.read().decode('utf-8')
                            data = json.loads(json_response)
                        #Escribimos la los hashes y scores (unicos datos de interes) de la respuesta en la cache local.  
                        cache_file = open(path_cache, "w")    
                        for json_new in data['data']:
                            try:
                                hash_bbdd = json_new["hash"]
                                score_bbdd = json_new["score"]
                                cache_file.write(str(hash_bbdd) + '\t' + str(score_bbdd) + '\n')
                            except:
                                continue
                        cache_file.close()
                        #A los 10 minutos restauramos el contador de tiempo.
                        if counter == 3600:
                            counter = 0
                except:
                    #En caso de que algun fallo sea capturado, comprobamos el contador.
                    if counter == 3600:
                        counter = 0

                #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.  
                file_stop = open(path_config, 'r').readlines()
                for lines in file_stop:
                    if 'stop' in lines:
                        exit_program = 0
                        bitacora_string = "Exiting to cache process"
                        logs_function(bitacora_string)
                #Aumentamos el contador.        
                counter += 1
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            raise
        except:	    
            raise
        finally:
            pythoncom.CoUninitialize ()

#Clase que monitoriza los procesos web y captura las conexiones de red del endpoint en tiempo real.
def webs_process(kafka_queue, bitacora_size, client_id):
        #se deja constancia en la bitacora el inicio de la clase
        bitacora_string = "Starting web monitor"
        logs_function(bitacora_string)
        pythoncom.CoInitialize()
        try:
            #Se incia la interfaz de python que interactua con windows.
            c = wmi.WMI()
            #Se inicia la monitoricion de procesos en tiempo real, en este caso se monitorizaran los procesos que se crean.
            watcher = c.Win32_Process.watch_for("creation")
            #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
            exit_program = 1
            #Se obtiene la ruta del fichero donde GRR metera un stop para parar el cargador endpoint.
            path = os.path.abspath(os.path.dirname(__file__))
            path_config = os.path.join(path, "configuration", "config.txt")
            while exit_program == 1:
                try:
                    #Cuando un nuevo proceso se cree en el sistema entra en el try anterior y capturamos el proceso creado.
                    new_process = watcher()
                    try:
                       #obtenemos el PID y en nombre de su proceso padre. 
                       pid_process = psutil.pids()
                       parent_process = psutil.Process(new_process.ParentProcessId)
                       soon_process = psutil.Process(new_process.ProcessID)
                       connections_opened = ''
                       try:
                           if parent_process:
                               #si el proceso padre existe, capturamos sus conexiones de red.
                               #Si el proceso es de red tendra conexiones, sino dara un error y se ignorara el proceso.
                               connections_opened = parent_process.connections(kind="all")
                           else:
                               if soon_process:
                                   connections_opened = soon_process.connections(kind="all")
                           ip_list = []
                           ip_non_repeat_list = []
                           for tupla in connections_opened:
                           #recorremos conexion a conexion, se coge la IP y puerto y se mete en la lista de IP.
                               try:
                                   conexion = tupla[4]
                                   ip = conexion[0]
                                   puerto = conexion[1]
                                   if ip != None and ip !='' and puerto != None and puerto !='':
                                       ip_string = str(ip) + ":" + str(puerto)
                                       ip_list.append(ip_string)
                               except:
                                   continue
                           #Recorremos la lista de conexiones para coger las no repetidas, ya que hay algunas redundantes.
                           #Para saber si esta repetida usaremos una bandera a 0 o 1.
                           for element in ip_list:
                               flag = 0
                               for element_ip in ip_non_repeat_list:
                                   if element == element_ip:
                                       flag = 1
                               #Si la conexion no se repite se guarda en la lista de las no repetidas.        
                               if flag == 0:
                                   ip_non_repeat_list.append(element)
                           new_string = ''
                           #Como cada proceso puede tener varias conexiones pues enviamos a la bitacora todas.
                           for ip_connection in ip_non_repeat_list:
                               new_string += str(ip_connection) + '; '
                           if len(ip_non_repeat_list) > 0:
                               bitacora_string = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + '\",\"type\":\"connection\",\"application\":\"' + str(new_process.Caption) + '\",\"pid\":' +  str(new_process.ProcessID) + ',\"connections\":\"' + new_string + '\"}'
                               bitacora_writer('connection', bitacora_string, kafka_queue, bitacora_size)
                       except:
                           continue
                    except:
                        continue
                    
                    #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                    #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.
                    file_stop = open(path_config, 'r').readlines()
                    for lines in file_stop:
                        if 'stop' in lines:
                            exit_program = 0
                            bitacora_string = "Exiting to web process"
                            logs_function(bitacora_string)   
                except:
                    continue
        except KeyboardInterrupt:
            pass
            raise
        except:	    
            raise
        finally:
            pythoncom.CoUninitialize ()

#Clase que monitoriza la creacion de procesos en el sistema en tiempo real
def monitor_creation_process(kafka_queue, bitacora_size, client_id):
        #se deja constancia en la bitacora el inicio de la clase
        bitacora_string = "Starting creation monitor process"
        logs_function(bitacora_string)
        pythoncom.CoInitialize()
        try:
            #Se incia la interfaz de python que interactua con windows.
            c = wmi.WMI()
            #Se inicia la monitoricion de procesos en tiempo real, en este caso se monitorizaran los procesos que se crean.
            watcher = c.Win32_Process.watch_for("creation")
            #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
            exit_program = 1
            #Se obtiene la ruta del fichero donde GRR metera un stop para parar el cargador endpoint.
            path = os.path.abspath(os.path.dirname(__file__))
            path_config = os.path.join(path, "configuration", "config.txt")
            while exit_program == 1:
                try:
                    #Cuando un nuevo proceso se cree en el sistema entra en el try anterior y capturamos el proceso creado.
                    new_process = watcher()
                    #obtenemos el ejecutable binario que ejecuta dicho proceso
                    executable = get_executable(new_process, new_process.ProcessID, new_process.Caption, new_process.CommandLine, new_process.Description)
                    #obtenemos caracteristicas adicionales del proceso.
                    lista_caracteristicas = characterist(new_process)
                    #formamos un string informativo para la bitacora.
                    if new_process.ProcessID != None and new_process.Caption != None and executable != None:
                        process_information = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"process\",\"action\":\"creation\",\"name\":\"" + new_process.Caption + "\",\"pid\":" + str(new_process.ProcessID) + ",\"application\":\"" + executable + "\""
                    else:
                        process_information = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"process\",\"action\":\"creation\",\"name\":\"" + new_process.Caption + "\",\"application\":\"" + executable + "\""
                    for element in lista_caracteristicas:
                        process_information += element
                    try:
                       #obtenemos el proceso padre en caso de existir
                       process_pid = psutil.pids()
                       parent_process = psutil.Process(new_process.ParentProcessId)
                       if parent_process:
                           process_information += '\"parent_pid\":' + str(new_process.ParentProcessId) + ",\"parent_name\":\"" + parent_process.name() + '\"'
                           try:
                               #obtenemos el ejecutable binario del proceso padre y metemos en la bitacora la informacion del proceso hijo y padre.
                               executable_parent = get_parent_executable(new_process.ParentProcessId, parent_process.name())
                               process_information += ",\"parent_application\":\"" + executable_parent + '\"}'
                               bitacora_writer('process_creation', process_information, kafka_queue, bitacora_size)
                           except:
                               #si no existe el ejecutable padre no se indica en la bitacora.
                               process_information += "}"
                               bitacora_writer('process_creation', process_information, kafka_queue, bitacora_size)
                               continue
                    except:
                       #si no existe el proceso padre se indica en la bitacora.
                       process_information += "}"
                       bitacora_writer('process_creation', process_information, kafka_queue, bitacora_size)
                       continue

                    #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                    #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.
                    file_stop = open(path_config, 'r').readlines()
                    for lines in file_stop:
                        if 'stop' in lines:
                            exit_program = 0
                            bitacora_string = "Exit to process monitor"
                            logs_function(bitacora_string)
                            
                except:
                    continue
        except KeyboardInterrupt:
            pass
            raise
        except:	    
            raise
        finally:
            pythoncom.CoUninitialize ()


#Clase que monitoriza la destruccion de procesos en el sistema en tiempo real
def monitor_deletion_process(kafka_queue, bitacora_size, client_id):
        #se deja constancia en la bitacora el inicio de la clase
        bitacora_string = "Starting deletion process monitor"
        logs_function(bitacora_string)
        pythoncom.CoInitialize()
        try:
            #Se incia la interfaz de python que interactua con windows.
            c = wmi.WMI()
            #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
            exit_program = 1
            #Se inicia la monitoricion de procesos en tiempo real, en este caso se monitorizaran los procesos que se eliminan.
            watcher = c.Win32_Process.watch_for("deletion")
            #Se obtiene la ruta del fichero donde GRR metera un stop para parar el cargador endpoint.
            path = os.path.abspath(os.path.dirname(__file__))
            path_config = os.path.join(path, "configuration", "config.txt")
            while exit_program == 1:
                try:
                    #Cuando un nuevo proceso se destruye en el sistema entra en el try anterior y capturamos el proceso creado.
                    process_deletion = watcher()
                    #obtenemos informacion necesaria del proceso y la metemos en la bitacora
                    bitacora_string = "\"namespace_uuid\":\"" + str(client_id) + "\",\"endpoint_uuid\":\"" + str(client_id) + "\",\"type\":\"process\",\"action\":\"deletion\",\"name\":\"" + process_deletion.Caption + "\",\"pid\":" + str(process_deletion.ProcessID) + '}'
                    bitacora_writer('process_delete', bitacora_string, kafka_queue, bitacora_size)
                    #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                    #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.
                    file_stop = open(path_config, 'r').readlines()
                    for lines in file_stop:
                        if 'stop' in lines:
                            exit_program = 0
                            bitacora_string = "Exiting to deletion process monitor"
                            logs_function(bitacora_string)
                except:
                    continue
        except KeyboardInterrupt:
            pass
            raise
        except:	    
            raise
        finally:
            pythoncom.CoUninitialize ()

#Clase que monitoriza las particiones fisicas del equipo y la entrada y salida de USB
class file_monitor_change(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
            #creamos un bucle para cargar la configuracion necesaria para los filtros del cargador endpoint.
            flag_init = 0
            while flag_init == 0:
                path = os.path.abspath(os.path.dirname(__file__))
                try:
                    #lista que controla que particion logica del disco existe y esta activo en el sistema y cual no
                    threads_state = []
                    #lista de particion logica del disco.
                    threads_list = []
                    pythoncom.CoInitialize()
                    #Se incia la interfaz de python que interactua con windows.
                    c = wmi.WMI ()
                    #lista con las posibles particiones logicas del discos del sistema
                    partitions_logical_disk = []
                    #contador para realizar la consulta de los valores del PC
                    count = 0
                    #lista de filtros por defecto
                    filter_list = ['System Volume Information','SPP','TREN', "Program Files\\endpoint",'config', 'ntuser', 'AppData', 'Temp', 'AVG2015', 'repository', 'ProgramData', 'Windows', 'Recycle', 'NTUSER', 'Config', 'Program Files', 'version', 'RECYCLE']
                    #lista de filtros por tipo de fichero.
                    type_list = []
                    #obtenemos las direcciones de los ficheros donde se encuentran los filtros por ruta y tipo de fichero.
                    filter_type = os.path.join(path, 'filters', "filter_type.txt")
                    path_filter = os.path.join(path, 'filters', "path.txt")
                    filter_type_file = open(filter_type, "r").readlines()
                    path_filter_file = open(path_filter, "r").readlines()
                    #leemos los ficheros de filtros de extensiones y rutas y los adjuntamos a la lista
                    for line in filter_type_file:
                        words = line.split()
                        word = words[0]
                        type_list.append(word)
                    for lines in path_filter_file:
                        word_line = lines.split()[0]
                        word_line.replace("\\", "\\\\")
                        filter_list.append(word_line)#kafka_producer = KeyedProducer(kafka_client, partitioner=HashedPartitioner,async_retry_on_timeouts=True, async_queue_maxsize=0, async_retry_backoff_ms=100, async_retry_limit=None, async=True, batch_send=True, batch_send_every_n=500, batch_send_every_t=5)
                    #se crea un productor de mensajes para el cliente 
                    flag_init = 1
                except:   
                    continue
                
            #inicializamos los hilos que llamaran a las funciones de monitorizacion de procesos, conexiones y el que comprueba el estado del antivirus.
            config_path = os.path.join(path, 'configuration', "parameters.yaml")
            config_path_file = open(config_path, "r").read()
            parameters_config = yaml.load(config_path_file)
            file_size = parameters_config['file_size']
            bit_size = parameters_config['bitacora_size']
            flag = True
            while flag == True:
                    try:
                            client_id = parameters_config['client_id']
                            flag = False
                    except:
                            time.sleep(10)
                            continue
            #se crean los hilos necesarios para poder capturar procesos y ficheros                
            bitacora_size = int(bit_size)            
            file_size_logs = int(file_size)
            kafka_queue = Queue()
            kafka_thread = threading.Thread(target=kafka_send, args=(kafka_queue,client_id,))
            kafka_thread.setDaemon(True)
            kafka_thread.start()
            creation_process_thread = threading.Thread(target=monitor_deletion_process, args=(kafka_queue,bitacora_size,client_id,))
            creation_process_thread.setDaemon(True)
            creation_process_thread.start()
            deletion_process_thread = threading.Thread(target=monitor_creation_process, args=(kafka_queue,bitacora_size,client_id,))
            deletion_process_thread.setDaemon(True)
            deletion_process_thread.start()
            antivirus_thread = threading.Thread(target=webs_process, args=(kafka_queue,bitacora_size,client_id,))
            antivirus_thread.setDaemon(True)
            antivirus_thread.start()
            connection_thread = threading.Thread(target=search_antivirus, args=(kafka_queue,bitacora_size,client_id,))
            connection_thread.setDaemon(True)
            connection_thread.start()
            #creamos colas, una para encolar y analizar ficheros, otra para describir el tipo de evento y una cola lenta para los ficheros filtrados.
            normal_queue = Queue()
            description_queue = Queue()
            slow_queue = Queue()
            #creamos un pool de hilos no bloqueante entre ellos y los enviamos a la funcion de analisis de fichero.            
            for x in range(3):
                normal_thread = threading.Thread(target=threader, args=(normal_queue,filter_list,slow_queue,type_list,kafka_queue,file_size_logs,bitacora_size,client_id,))
                normal_thread.setDaemon(True)
                normal_thread.start()
            #creamos un pool de hilos no bloqueante entre ellos y los enviamos a la funcion de descripcion de eventos de ficheros.
            for y in range(2):
                event_thread = threading.Thread(target=threader_log, args=(description_queue,filter_list,kafka_queue,bitacora_size,client_id,))
                event_thread.setDaemon(True)
                event_thread.start()
                
            #creamos un unico hilo que analizara los ficheros filtrados de forma mas lenta que la otra cola debido a que la prioridad es menor.
            slow_thread = threading.Thread(target=threader_slow, args=(slow_queue,kafka_queue,bitacora_size,client_id,))
            slow_thread.setDaemon(True)
            slow_thread.start()
                
            try:
                #Se obtiene la ruta del fichero donde GRR metera un stop para parar el cargador endpoint.
                path = os.path.abspath(os.path.dirname(__file__))
                path_config = os.path.join(path, "configuration", "config.txt")
                #inicializamos la variable exit_program, encargada de cambiar en caso que al enpoint se le ordene pararse.
                exit_program = 1
                error = create_directory()
                if error == 1:
                    #se deja constancia en la bitacora el inicio de la clase de forma satisfactoria.
                    bitacora_string = 'File change process has been started succesfully'
                    logs_function(bitacora_string)
                while exit_program == 1 and error == 1:
                    try:
                        error = 1
                        #cada cierto tiempo se consultan los datos del equipo y se almacenan para la consulta del cargador endpoint.
                        if count==0 or count==60:
                            put_file()
                            if count==60:
                                count = 0
                    
                        #si es una particion logica del disco fisico se incluira a la lista para monitorizarlo y evitar asi los discos de red    
                        for physical_disk in c.Win32_DiskDrive ():
                          for partition in physical_disk.associators ("Win32_DiskDriveToDiskPartition"):
                            for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
                              if len(partitions_logical_disk)==0:
                                  #si la lista de discos esta vacia es porque acabamos de empezar
                                  #se introducen en la lista el disco encontrado
                                  disk_partition = logical_disk.Caption + "\\"
                                  partitions_logical_disk.append(disk_partition)
                                  threads_state.append(0)
                              else:
                                  #si existe en la lista algun disco se compara
                                  #si coincide no se introduce en la lista (match = 1)
                                  #si no existe ningun disco en la lista igual que ese, se introduce y se mete en la lista de estados en su misma posicion un 0.
                                  match = 0
                                  for element in partitions_logical_disk:
                                      disk_partition = logical_disk.Caption + "\\"
                                      if disk_partition==disk_partition:
                                          match = 1
                                  if match==0:
                                      disk_partition = logical_disk.Caption + "\\"
                                      partitions_logical_disk.append(disk_partition)
                                      threads_state.append(0)
                        threads_position = 0
                        #se recorre la lista de discos y comprobamos que su ruta existe
                        for path_logical_disk in partitions_logical_disk:
                            if os.path.exists(path_logical_disk):
                                #si existe la ruta y el disco estaba inactivo se crea hilo
                                #como estaba inactivo ponemos un uno en referencia a que ahora si lo esta en su posicion correspondiente
                                if threads_state[threads_position] == 0:
                                    thread_monitor_disk = threading.Thread(target=ppal, args=(path_logical_disk,filter_list,normal_queue,description_queue,), name=path_logical_disk)
                                    threads_list.append(thread_monitor_disk)
                                    thread_monitor_disk.start()
                                threads_state[threads_position] = 1
                            #Si no existe la ruta pero el disco estaba activo en la ultima comprobacion se pone como inactivo en su posicion correspondiente.        
                            else:
                                if threads_state[threads_position] == 1:
                                    threads_state[threads_position] = 0
                            threads_position = threads_position + 1
                        #Esperamos 1 segundo para chequear de nuevo. (Chequeo del sistema cada segundo)
                        #Se lee el fichero donde GRR metera un stop para parar el cargador endpoint.
                        #Si existe stop en el fichero se acaba la ejecucion de la clase, ya que termina el bucle al cambiar la condicion.
                        file_stop = open(path_config, 'r').readlines()
                        for lines in file_stop:
                            if 'stop' in lines:
                                exit_program = 0
                                bitacora_string = "Exiting to files changes process"
                                logs_function(bitacora_string)
                        time.sleep(2)
                        count += 1
                    except:
                        continue
            except KeyboardInterrupt:
                pass
                raise
            except:
                raise
            finally:
                pythoncom.CoUninitialize ()

if __name__ == '__main__':

    #Se obtiene la ruta del fichero donde GRR metera un stop para parar el cargador endpoint.
    path = os.path.abspath(os.path.dirname(__file__))
    path_config = os.path.join(path, "configuration", "config.txt")

    #se inician las clases
    local_cache().start()
    time.sleep(2)
    file_monitor_change().start()
    
    try:
        #se comprueba si el endpoint esta parado.
        check_state = 0
        while True:
            file_stop = open(path_config, 'r').readlines()
            for lines in file_stop:
                if 'stop' in lines:
                    check_state = 1
            if check_state == 1:
                #si esta el enpoint parado, esperaremos a que se reactive.
                while check_state == 1:
                    match_state = 0
                    file_state = open(path_config, 'r').readlines()
                    for lines in file_state:
                        if 'stop' in lines:
                            match_state = 1
                    #si se levanta la condicion de endpoint parado, se reinicia.
                    if match_state == 0:
                        check_state = 0
                        local_cache().start()
                        time.sleep(2)
                        file_monitor_change().start()
                    else:
                        time.sleep(2)
            time.sleep(1)
    except KeyboardInterrupt:
        print ("Exiting")
        exit(0)                
