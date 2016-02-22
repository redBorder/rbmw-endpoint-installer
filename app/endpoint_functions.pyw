import socket
import wmi
import sys
import os
import time
import shutil
import string
import random
from kafka import KafkaClient, KeyedProducer, HashedPartitioner, RoundRobinPartitioner
import hashlib
import win32security
import win32con
import ntsecuritycon as con
from queue import Queue
import binascii
import re
import boto
from boto.s3 import connect_to_region
from boto.s3.connection import Location
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import win32security
import sha3
import psutil
import json
import win32file
import threading
import yaml

#funcion que busca si un fichero esta filtrado por ruta.
def search_in_list(filename, filter_list):
  try:
    match = 0
    for element in filter_list:
      #si esta filtrado cambia el valor de la variable y retorna un valor, sino retorna otro.
      if element in filename:
        match = 1
    if match == 1:
      return 1
    elif match == 0:
      return 0
  except:
    return 0

def ppal (logical_disk, filter_list, normal_queue, decription_queue):
  #Acciones que pueden ocurrir para que salte un evento
  ACTIONS = {
    1 : "Created",
    2 : "Deleted",
    3 : "Updated",
    4 : "Renamed from something",
    5 : "Renamed to something"
  }

  FILE_LIST_DIRECTORY = 0x0001
    
  #Ruta a monitorizar
  path_to_watch = logical_disk
  #configuracion de la monitorizacion
  hDir = win32file.CreateFile (
    path_to_watch,
    FILE_LIST_DIRECTORY,
    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
    None,
    win32file.OPEN_EXISTING,
    win32con.FILE_FLAG_OVERLAPPED | win32con.FILE_FLAG_BACKUP_SEMANTICS,
    None
  )
  exit_thread = 1
  while exit_thread == 1:

    # Monitorizacion (ruta, buffer, subcarpetas a monitorizar (si o no), cambios con los que salta el evento) 
    results = win32file.ReadDirectoryChangesW (
      hDir,
      5012,
      True,
      win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
      win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
      #win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
      #win32con.FILE_NOTIFY_CHANGE_SIZE |
      win32con.FILE_NOTIFY_CHANGE_LAST_WRITE,
      #win32con.FILE_NOTIFY_CHANGE_SECURITY,
      None,
      None
    )
    #mientras exista resultados asociados a un evento
    send_list = []

    #Del evento capturado se coge la accion y el archivo implicado en el evento.  
    for action, file in results:
      #completamos el nombre del fichero implicado en un evento.
      full_filename = os.path.join (path_to_watch, file)
      temporal_list = [action, full_filename]
      #introducimos en la lista de eventos la accion y el fichero implicado.
      send_list.append(temporal_list)
      #si la ruta existe y es un fichero.     
      if os.path.exists(full_filename) and os.path.isfile(full_filename):
        match = 0
        #comprobamos si el fichero esta filtrado por ruta, si lo esta se ignora y si no se encola.
        for element_list in filter_list:
          if re.search(element_list, full_filename):
            match = 1
        #si el fichero no esta filtrado por ruta y la accion no es borrar, es decir, el fichero existe para trabajar con el mismo.    
        if match == 0 and action != 2:
          file_action = ''
          #se asigna una accion dependiendo del numero relacionado a la accion
          if action == 1:
            file_action = full_filename + '|' + 'created'
          else:
            file_action = full_filename + '|' + 'updated'
          #se encola el evento en la cola normal  
          normal_queue.put(file_action)

      #en caso de ser un directorio solo se mandara el evento si es nuevo.    
      elif os.path.isdir(full_filename) and action == 1:
        match = 0
        #se comprueba que no este filtrado por ruta el evento asociado a un directorio
        for recorre in filter_list:
          if re.search(recorre, full_filename):
            match = 1
        #si no esta filtrado se le asocia la accion y se encola en la cola normal
        if match == 0:
          file_action = full_filename + '|' + 'created'
          normal_queue.put(file_action)
    #se mete toda la informacion asociado a un evento en la cola de informacion      
    decription_queue.put(send_list)
    #si la ruta raiz (en este caso la particion de windows, ya que puede ser un usb y desaparecer) deja de existir se acaba el bucle.
    if not os.path.exists(path_to_watch):
      exit_thread = 0



#Funcion que obtiene el tamanio de un fichero.
def get_size_file(filename):
  exception = None
  try:
    if os.path.exists(filename):
      tamanio = os.path.getsize(filename)
      return tamanio
    else:
      return exception
  except:
    return exception

#funcion que genera una cadena aleatoria    
def id_generator():
  size=6
  chars=string.ascii_uppercase + string.digits
  return ''.join(random.choice(chars) for _ in range(size))


def kafka_broker_search():
  #obtenemos la direccion del fichero de parametros
  path_execution = os.path.abspath(os.path.dirname(__file__))
  path_config = os.path.join(path_execution, "configuration", "parameters.yaml")
  #buscamos en el fichero de parametros la direccion del manager de malware
  parameters_file = open(path_config, 'r').read()
  direction_kafka = yaml.load(parameters_file)
  direction = direction_kafka['broker_kafka']
  return direction

#funcion que envia a kafka
def kafka_send(kafka_queue, client_id):
      flag_kafka = True
      #convertimos a bytes el id del cliente por exigencias de la libreria kafka-python
      field_client_id = bytes(client_id, 'utf-8')
      while flag_kafka == True:
        try:
          #obtenemos el broker de kafka al que enviar
          kafka_broker = kafka_broker_search()
          #intentamos conectarnos al broker hasta conseguirlo, es decir hasta que este disponible
          kafka_client = KafkaClient(kafka_broker)
          kafka_producer = KeyedProducer(kafka_client, partitioner=HashedPartitioner, async=False)
          flag_kafka = False
        except:
          time.sleep(2)
      while True:
        try:
            #se lee de la cola
            worker = kafka_queue.get()
            kafka_table = worker.split("|")
            #Dependiendo de donde este el None, significa que sera un evento de tipo fichero o de tipo bitacora
            if "None" in kafka_table[1]:
              path = kafka_table[0].replace('\\\\', '\\')
              topic = "rb_endpoint"
            else:
              path = kafka_table[1].replace('\\\\', '\\')
              topic = "rb_ioc"
            #se obtiene el mensaje a enviar y se pasa a bytes.  
            content = open(path,"r+").read()
            message = bytes(content, 'utf-8')
            flag = True
            #En caso que falle el broker de kafka el mensaje se reintentara hasta que este disponible
            while flag == True:
              try:
                kafka_producer.send(topic, field_client_id, message)
                #Se borra el fichero temporal.
                if os.path.exists(path):
                  os.remove(path)
                flag = False
              except Exception:
                time.sleep(10) 
        except:
          continue

def bitacora_writer(type_event, bitacora_string, kafka_queue, bitacora_size):
  #se obtiene la direccion de la bitacora
  path = os.path.abspath(os.path.dirname(__file__))
  path_bitacora = os.path.join(path, "grr", "bitacora.json")
  #para cada evento que se produzca se crea un fichero temporal(solucion por bugs en libreria kafka-python con formato json)
  name_file = id_generator()
  name_file += "_kafka.json"
  path_new_file = os.path.join(path, "archivos", name_file)
  #adaptacion para iocs
  bitacora_string = bitacora_string.replace('\\','\\\\')
  bitacora_string = bitacora_string.replace('\n','')
  try:
      timestamp = int(time.time())
      string = ''
      if not os.path.exists(path_bitacora):
        tamanio = 0
      else:
        #se obtiene el tamanio de la bitacora
        tamanio = get_size_file(path_bitacora)
      if tamanio != "" and tamanio != None:
        #si la bitacora no existe se crea y si se sobrepasa el tamanio fijado tambien.
        if not os.path.exists(path_bitacora) or tamanio >= bitacora_size:
          bitacora_file = open(path_bitacora, 'w')
          string = '{\"timestamp\":' + str(timestamp) + ',' + str(bitacora_string)
          bitacora_file.write(str(string) + '\n')
          bitacora_file.close()  
        else:
          bitacora_file = open(path_bitacora, 'a')
          string = '{\"timestamp\":' + str(timestamp) + ',' + str(bitacora_string)
          bitacora_file.write(str(string) + '\n')
          bitacora_file.close()
            
      #se escribe en el fichero temporal para enviar a kafka.    
      file_bit = open(path_new_file, 'w')
      file_bit.write(str(string))
      file_bit.close()
      #upload_kafka('None', kafka_producer, path_new_file)
      string_queue = str("None|" + path_new_file)
      kafka_queue.put(string_queue)
  except:
    pass

  

#Funcion que genera los logs en la bitacora.
def logs_function(log_string):
  #se obtiene la direccion de los logs
  path = os.path.abspath(os.path.dirname(__file__))
  path_logs = os.path.join(path, "logs", "endpoint_logs.txt")
  #se obtiene la direccion del fichero de parametros para coger el tamanio fijado maximo para los logs
  config_path = os.path.join(path, 'configuration', "parameters.yaml")
  config_path_file = open(config_path, "r").read()
  #se obtiene el tamanio maximo
  logs_size_param = yaml.load(config_path_file)
  logs_size =  logs_size_param['logs_size']
  try:
      tamanio = get_size_file(path_logs)
      if tamanio != "" and tamanio != None:
        file_logs_size = int(logs_size)
        timestamp = time.asctime(time.localtime(time.time()))
        #si la bitacora no existe se crea y se escribe en ella.
        if not os.path.exists(path_logs) or tamanio >= file_logs_size:
          logs_file = open(path_logs, 'w')
          logs_file.write(str(timestamp + ' ' + log_string + '\n'))
          logs_file.close()
        #si existe se comprueba el tamaño y si sobrepasa el limite se crea una copia de seguridad y se escribe si no se escribe.  
        else:
          logs_file = open(path_logs, 'a')
          logs_file.write(str(timestamp) + ' ' + log_string + '\n')
          logs_file.close()    
  except:
    pass

#Funcion que obtiene las diferentes caracteristicas de un proceso.
def characterist(process):
   characterist_list = []
   try:
       #se obtiene la prioridad del proceso
      if process.Priority:
         characterist_list.append(",\"priority\":" + str(process.Priority) + ",")
      #se obtiene el identificador del usuario que ha creado el proceso   
      if process.SessionId:
         characterist_list.append("\"sessionId\":" + str(process.SessionId) + ',')
      return characterist_list
   except:
      return characterist_list
      pass

#funcion que obtiene el ejecutable binario padre de un proceso.    
def get_parent_executable(pid, name):
   try:
      executable = get_process_executable(pid)
      if not executable:
          executable = get_process_executable_by_name(name)
      if not executable:
          return None
      else:
           return executable
   except:
      pass

#Funcion que obtiene el ejecutable binario de un proceso a traves del nombre.
def get_process_executable_by_name(filename,cmdline=None):
    try:
        if not cmdline:
            system_path = os.environ['WINDIR'] + "\\System32\\"
            full_path = system_path + filename
            if os.path.exists(full_path):
                executable = full_path
            else:
                executable = None
        else:
            if "\\SystemRoot\\".lower() in cmdline.lower():                
                os_path = os.environ['WINDIR'] 
                system_path = cmdline.replace("\\SystemRoot",os_path)[:cmdline.rfind("\\")] 
                full_path = system_path + filename
                if os.path.exists(full_path):
                    executable = full_path
                else:
                    executable = None
            else:
                executable = None
    except:
        executable = None
    return executable

#Funcion que obtiene el ejecutable binario de un proceso a traves del pid.
def get_process_executable(pid):
    if not pid or pid == 4:
        return None
    try:
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
        executable = win32process.GetModuleFileNameEx(handle,0)
        win32api.CloseHandle(handle)
        if "\\SystemRoot\\".lower() in executable.lower():
            executable = None
        if "\\??\\" in executable:
            executable = executable.replace("\\??\\", "") 
    except:
        executable = None
    return executable

#funcion que es la main() para obtener el ejecutable de un proceso.
def get_executable(process, pid, name, commandLine, description):
   try:
      #se intenta obtener el ejecutable binario de forma facil.
      executable = process.ExecutablePath
      if not executable:
          #se intenta obtener el ejecutable binario a traves del PID.
          executable = get_process_executable(pid)
          if not executable:
              #si no se obtiene, se reintenta, debido a la suceptibilidad a errores.
              executable = process.ExecutablePath
          if not executable:
               #se intenta obtener el ejecutable binario a traves del nombre.
               executable = get_process_executable_by_name(name)
          if not executable:
              if commandLine:
                  #si en los parametros existe la variable commandLine se intenta obtener a traves de ella y el nombre.
                  executable = get_process_executable_by_name(name, commandLine)
          if not executable:
              if commandLine:
                  #si no se puede obtener con metodos anteriores pues se intenta obtener a traves de la descripcion y el commandLine.
                  executable = get_process_executable_by_name(description, commandLine)
      #si por lo que sea no se obtiene porque no existe pues retornamos None, sino el ejecutable binario.
      if not executable:
          return None
      else:
           return executable
   except:
      pass


#funcion que en caso de que los directorios necesarios no existe los crea
def create_directory():
  bitacora_string = ''
  try:
      #definimos la ruta de la carpeta donde guardaremos temporalmente los ficheros a subir a s3
      path = os.path.abspath(os.path.dirname(__file__))
      path_s3 = os.path.join(path, "s3")
      #si no existe la crea el directorio temporal de los ficheros que se subiran a s3
      if not os.path.exists(path_s3):
        os.mkdir(path_s3)
      #definimos la ruta de la carpeta donde guardaremos temporalmente los ficheros a enviar a kafka  
      path_kafka = os.path.join(path, "archivos")
      if not os.path.exists(path_kafka):
        os.mkdir(path_kafka)
      #se crea los logs
      path_logs = os.path.join(path, "logs")
      path_logs_file = os.path.join(path_logs, "endpoint_logs.txt")
      if not os.path.exists(path_logs):
        os.mkdir(path_logs)
        bitacora = open(path_logs_file, 'wb')
        bitacora.close()
      #se crea la bitacora  
      path_grr = os.path.join(path, "grr")
      if not os.path.exists(path_grr):
        os.mkdir(path_grr)
      #se crea la carpeta de la cache y la cache  
      path_cache = os.path.join(path, "cache")
      file_cache = os.path.join(path_cache, "Malware_cache.txt")
      if not os.path.exists(path_cache):
        os.mkdir(path_cache)
        file_cache = open(file_cache, "wb")
        file_cache.close()
      bitacora_string = 'Endpoint\'s directories have been created.'
      logs_function(bitacora_string)
      return 1
  except:
      return 0
      pass  

#Funcion que escribe en un fichero que definimos los parametros del endpoint que se usaran en comun en todos los mensajes Kafka.
def put_file():
    try:
      hostname = ''
      MAC = ''
      DNSDomain = ''
      IP = ''
      IP_Subred = ''
      Name = ''
      #con la libreria socket cogemos el nombre del host o nombre del pc
      hostname = socket.gethostbyname_ex (socket.gethostname ())[0]
      #Mientras existan y no sean nulas, se cogen la MAC, IP e IP de Subred del PC, la union de todas que no son nulas da las del PC
      for parameters_network in wmi.WMI ().Win32_NetworkAdapterConfiguration ():
          if parameters_network.MACAddress != None and parameters_network.DNSDomain != None and parameters_network.IPAddress != None and parameters_network.IPSubnet != None and parameters_network.DefaultIPGateway != None:
              MAC = parameters_network.MACAddress
              DNSDomain = parameters_network.DNSDomain
              IP = parameters_network.IPAddress
              IP_Subred = parameters_network.IPSubnet
      #Mientras existan y no sean nulas, se cogen el nombre de la cuenta de usuario, su perfil asociado y el tipo de cuenta de usuario        
      for parameters_profile in wmi.WMI ().Win32_NetworkLoginProfile ():
          if parameters_profile.Name != None:
              Name = parameters_profile.Name
      path = os.path.abspath(os.path.dirname(__file__))
      full_path = os.path.join (path, 'windows_value.txt')
      #si existe se sobrescribe sino se crea nuevo y se incluyen los datos comunes a los ficheros malwares capturados y enviados a kafka y s3
      file_windows_parameters = open(full_path, "w")   
      file_windows_parameters.write("{\"" + "sensor_name" + "\":" + "\"")
      file_windows_parameters.write(hostname + "\",")
      file_windows_parameters.write("\"" + "client_id" + "\":" + "\"")
      file_windows_parameters.write(Name + "\",")
      file_windows_parameters.write("\"" + "client_mac:" + "\":" + "\"")
      file_windows_parameters.write(MAC.lower() + "\",")
      file_windows_parameters.write("\"" + "domain_name" + "\":" + "\"")
      file_windows_parameters.write(DNSDomain + "\",")
      file_windows_parameters.write("\"" + "src" + "\":" + "\"")
      file_windows_parameters.write(IP[0] + "\",")
      file_windows_parameters.write("\"" + "src_net_name" + "\":" + "\"")
      file_windows_parameters.write(IP_Subred[0] + "\",")
      file_windows_parameters.close()
      bitacora_string = 'The EndPoint\'s data have been updated'
      logs_function(bitacora_string)
    except:
      bitacora_string = 'Error getting the EndPoint\'s data'
      logs_function(bitacora_string)

#funcion que obtiene el sha256
def create_sha_256(filename, tiempo):
    if os.path.exists(filename):
        #flag para el numero de intentos de hacer el sha256
        flag = True
        #Mientras nos de errores de permisos
        sha_256 = None
        while flag==True or sha_256 is None:
            try:
                #MUY IMPORTANTE HACER LAS OPERACIONES POR SEPARADO PORQUE EL RENDIMIENTO DE LA CPU MEJORA EN TORNO AL 30 PORCIENTO
                file_open = open(filename, "rb")
                content = file_open.read()
                #una vez que tenemos el contenido hacemos el sha256 con la libreria pysha3 que lo hace en la SSE
                sha_normal = hashlib.sha3_256(content)
                #pasamos a hexadecimal el sha256
                sha_256 = sha_normal.hexdigest()
                file_open.close()
                flag = False
                return sha_256
            except:
                time.sleep(tiempo)

#obtenemos el md5 de un fichero.
def create_md5(filename, tiempo):
    if os.path.exists(filename):
        #flag para el numero de intentos de hacer el sha256
        flag = True
        #Mientras nos de errores de permisos
        md5_hash = None
        while flag==True or md5_hash is None:
            try:
                file_open = open(filename, "r+b")
                #MUY IMPORTANTE HACER LAS OPERACIONES POR SEPARADO PORQUE EL RENDIMIENTO DE LA CPU MEJORA EN TORNO AL 30 PORCIENTO
                content = file_open.read()
                #se crean los hash en hexadecimal
                md5_normal = hashlib.md5(content)
                md5_hash = md5_normal.hexdigest()
                file_open.close()
                #print ("md5: ", md5_hash)
                flag = False
                return md5_hash
            except:
                time.sleep(tiempo)

#funcion que obtiene los permisos de los ficheros e imprime toda la informacion del fichero en la bitacora.
def get_acl(path_file, action, sha256, hash_md5, type_file, filter_file, cache_status, kafka_queue, bitacora_size, client_id):
  name_file = os.path.basename(path_file)
  extension = os.path.splitext(path_file)[1]
  #metemos en la bitacora toda la informacion de un evento asociado a un fichero.
  bitacora_string = "\"namespace_uuid\":\"" + str(client_id) + '\",\"endpoint_uuid\":\"' + str(client_id) + '\",\"type\":\"file_capture\",\"filename\":\"' + name_file + '\",\"filepath\":\"' + path_file + '\",\"file_extension\":\"' + extension + '\",\"action\":\"' + action + '\",\"sha256\":\"' + sha256 + '\",\"md5\":\"' + hash_md5 + "\""
  #ponemos los datos en la bitacora si no estan vacios, solo se pondran aquellos que contengan informacion
  if type_file != None and type_file != 'None':
    bitacora_string += ",\"file_type\":\"" + str(type_file) + '\"'
  if filter_file != None:
    bitacora_string += ",\"filter\":\"" + str(filter_file) + '\"'  
  try:
    #Obtenemos toda la seguridad del fichero, es decir, las dacl(data access control list) y la seguridad para la gestion.
    security_file = win32security.GetFileSecurity(path_file, win32security.DACL_SECURITY_INFORMATION)
    #De toda la seguridad obtenemos las DACL.
    dacl = security_file.GetSecurityDescriptorDacl()
    if dacl != None and dacl != '':
      #pasamos la dacl a formato string.
      string_dacl = str(dacl)
      #cogemos el ultimo parametro, que es una lista.
      parameter_dacl = string_dacl.split()[-1]
      #cogemos todos los permisos, que en realidad es solo uno y lo pasamos a decimal.
      permission = parameter_dacl[0:-1]
      permission_decimal_format = int(permission, 16)
      bitacora_string += ',\"acl\":\"' + str(permission_decimal_format) + '\",\"cache\":\"' + str(cache_status) + '\"}'
      bitacora_writer('capture', bitacora_string, kafka_queue, bitacora_size)
  except:
    #si entra en except es porque ha fallado al coger el acl, por tanto no se introduce en la bitacora.
    bitacora_string += '\",\"cache\":\"' + str(cache_status) + '\"}'
    bitacora_writer('capture', bitacora_string, kafka_queue, bitacora_size)
    pass

#Funcion que busca el score asociado a un sha256.
def find_score(sha256):
  #obtenemos la cache
  path = os.path.abspath(os.path.dirname(__file__))
  path_cache = os.path.join(path, "cache", "Malware_cache.txt")
  try:
    if os.path.exists(path_cache):
      #obtenemos todas las lineas de la cache.
      cache_file = open(path_cache, 'r')
      cache_lines = cache_file.readlines()
      cache_file.close()
      for lines in cache_lines:
        #si el sha256 esta en la linea cogemos el score asociado.
        #el sha256 siempre va a existir porque si no existiera anteriormente lo metimos en la cache.
        if (sha256 in lines):
          words = lines.split()
          score = int(words[1])
          return score
  except:
    #En caso de error metemos un score desorbitado para no tenerlo en cuenta.
    return 1000

#buscamos si un sha256 existe en la cache.
def find_match(sha256):
  path = os.path.abspath(os.path.dirname(__file__))
  path_cache = os.path.join(path, "cache", "Malware_cache.txt")
  path_config = os.path.join(path, "configuration", "parameters.yaml")
  try:
    if os.path.exists(path_cache):
      #obtenemos la cache
      cache_file = open(path_cache, 'r')
      cache_content = cache_file.readlines()
      cache_file.close()
      file_parameters = open(path_config, 'r').read()
      parameters_content = yaml.load(file_parameters)
      limit_score_string = parameters_content['score']
      limit_score = int(limit_score_string)
      #variable que indicara si es malware o no el fichero.
      indicator = 0
      for lines in cache_content:
        if (sha256 in lines):
          words = lines.split()
          score = int(words[1])
          #si el sha256 existe y es mayor del umbral sera malware sino clean.
          if score > limit_score:
            indicator = 2
          else:
            indicator = 1
      if indicator == 0:
        #si el sha256 no existe, se mete una entrada en la cache.
        cache = open(path_cache, 'a')
        cache.write(str(sha256) + '\t' + str(0) + '\n')
        cache.close()
      return indicator
  except:
    return 0
    
#funcion que comprueba el tipo de fichero        
def file_magic_function(filename):
  try:
    message = open(filename, 'rb').read()
    dir_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),'filters', 'snort_file.txt')
    snort_file = open(dir_file, 'r').readlines()
    tam = 0
    tabla_uno = []
    #se lee linea a linea el fichero de snort
    while tam < len(snort_file):
        #separamos cada linea en palabras
        words = snort_file[tam].split()
        #si la ultima es un 1 vamos cogiendo linea a linea hasta que no lo sea
        if words[-1] == "1":
             while words[-1] == "1":
                 #final es la suma del byte inicial a mirar y el numero de bytes a mirar
                 final = int(words[1]) + int(words[0])
                 #se coge en hexadecimal el contenido de un fichero acotado por un byte inicial y otro final
                 content = binascii.hexlify(message[int(words[0]):final])
                 #se pasa a mayuscula
                 match = str(content.decode('ascii')).upper()
                 #si ese contenido coincide con el tipico de un fichero de ese tipo que viene en nuestro fichero snort metemo 1 en la tabla y sino 0
                 if match == words[2]:
                     tabla_uno.append(1)
                 else:
                     tabla_uno.append(0)
                 #avanzamos de linea y dividimo en palabras    
                 tam += 1
                 words = snort_file[tam].split()
             #Aqui words[-1] ya no es 1 sino 0 y se coge el contenido en hexadecimal en un rango de bytes 
             words =  snort_file[tam].split()
             final = int(words[1]) + int(words[0])
             content = binascii.hexlify(message[int(words[0]):final])
             match = str(content.decode('ascii')).upper()
             #si coincide con el contenido tipico se mete 1 en la tabla y si no 0
             if match == words[2]:
                 tabla_uno.append(1)
             else:
                 tabla_uno.append(0)
             #Aqui ya se ha salido del bucle es decir, antes se ponia 1 o 0 porque para que el fichero sea de un tipo debe coincidir todo sino no lo es
             flag = 1
             #si toda la lista esta a 1 es de ese tipo si no no lo es
             for attribute in tabla_uno:
                 if attribute == 0:
                     flag = 0
             if flag == 1:
                 return words[3]
             tabla_uno = []
             tam += 1
        #si la ultima palabra no era 1 pues se coge el contenido del fichero en hexadecimal delimitado por un rango de bytes y se mira si coincide con el tipico.     
        else:
            final = int(words[1]) + int(words[0])
            content = binascii.hexlify(message[int(words[0]):final])
            match = str(content.decode('ascii')).upper()
            if match == words[2]:
                return words[3]
            tam += 1       
  except:
    bitacora_string = 'Error in type function'
    logs_function(bitacora_string)
    type_file_none = 'None'
    return type_file_none

#funcion fundamental que abre constantemente el fichero para saber cuando esta disponible
#Un fichero esta indisponible mientras no se haya terminado de copiar en alguna direccion al completo y tenga todos los permisos.
#este programa es mas rapido que windows a la hora de dar permisos, por tanto estara indisponible de forma momentanea.  
def file_open(filename, tiempo):
  flag = True
  while flag == True:
    try:
      file_open = open(filename, 'rb')
      flag = False
    except:
      time.sleep(tiempo)

#funcion que construye en json el mensaje kafka y crea el fichero temporal.
def new_file_kafka(filename, sha256, name_file, score, client_id, kafka_queue):
  try:
    if os.path.exists(filename):
      #ruta de los ficheros temporales
      ruta = os.path.abspath(os.path.dirname(__file__))
      path = os.path.join(ruta, 'archivos')
      #ruta del fichero con los datos del PC
      windows_parameters = os.path.join(ruta, 'windows_value.txt')
      #completo la ruta del fichero temporal
      full_path = os.path.join (path, name_file)
      shutil.copy(windows_parameters, full_path)
      name_file = os.path.basename(filename)
      #si existen las rutas
      if os.path.exists(full_path):
        #se abre el fichero temporal en forma de incluir mas datos sin sobrescribir
        temporal_file = open(full_path, "a")
        #se incluyen la accion, la ruta y los hash
        temporal_file.write("\"" + "file_uri\":" + "\"")
        temporal_file.write(filename + "\",")
        temporal_file.write("\"" + "file_name\":" + "\"")
        temporal_file.write(name_file + "\",")
        temporal_file.write("\"" + "hash\":" + "\"")
        temporal_file.write(sha256 + "\",")
        if score != 1000:
          temporal_file.write("\"" + "probe_score\":")
          temporal_file.write(str(score) + ",")
        temporal_file.write("\"action\":\"FORWARD\",")
        temporal_file.write("\"endpoint_uuid\":\"" + str(client_id) + "\",")
        temporal_file.write("\"" + "timestamp\":")
        time_now = int(time.time())
        temporal_file.write(str(time_now) + "}")
        temporal_file.close()
        #se llama a la funcion de subida de datos a kafka
        #upload_kafka(full_path, kafka_producer, None)
        string_queue = str(full_path + "|None")
        kafka_queue.put(string_queue)
  except:
    pass


def upload_s3(original_path, filename, sha256, md5_hash):
  #obtenemos la ruta del fichero de parametros.
  ruta = os.path.abspath(os.path.dirname(__file__))
  path = os.path.join(ruta, 'configuration', 'parameters.yaml')
  file_path = open(path, 'r').read()
  parameters_s3 = yaml.load(file_path)
  aws_access = parameters_s3['access_key']
  aws_secret = parameters_s3['secret_key']
  bucket_name = parameters_s3['s3_bucket']
  if os.path.exists(filename):
    #variable que contabiliza el numero de intentos de subida a s3
    count = 0
    flag = True
    while flag == True:
      try:      
        #realizamos la conexion a s3 ignorando el certificado        
        conn = boto.connect_s3(aws_access_key_id = aws_access,aws_secret_access_key = aws_secret,host = 's3.redborder.cluster',validate_certs=False, calling_format = boto.s3.connection.OrdinaryCallingFormat(),)
        #obtenemos el bucket donde subir el fichero
        bucket = conn.get_bucket(bucket_name, validate=False)
        #subimos el fichero con un nombre determinado, en este caso el sha256
        k = Key(bucket)
        k.key = str(sha256)
        #subimos el fichero
        k.set_contents_from_filename(filename)
        time.sleep(1)
        flag = False
      except:
        #si falla y solo lo hemos intentado una vez se reintenta.
        if count < 2:
          count += 1
          time.sleep(2)
        else:
          #si hemos llegado al tope dejamos de intentarlo.
          flag = False

    try:
      #Una vez subido o no por fallos, lo eliminamos.
      if os.path.exists(filename):
        os.remove(filename)
        
      if count == 2:
        #si da error se avisa a traves de la bitacora.
        bitacora_string = 'Error uploading file' + original_path + ' to S3'
        logs_function(bitacora_string)  
      elif count < 2:
        #si se ha subido se deja constancia a traves de la bitacora
        bitacora_string = 'File ' + original_path + ' has been uploaded to S3'
        logs_function(bitacora_string)   
    except:
      pass
      
#funcion que obtiene todos los datos relacionados con un fichero.
def get_parameter(filename, action, type_file, sha256, md5_hash, filtro, kafka_queue, bitacora_size, client_id):
  try:
    if os.path.exists(filename):
      #nombre aleatorio para el json
      name = id_generator()
      name_file = 'EndPoint_'  + name + '.json'
      #si no esta filtrado
      if filtro == None:
        #buscamos si existe en la cache
        find_new = find_match(sha256)
        if find_new == 0:
          ruta = os.path.abspath(os.path.dirname(__file__))
          #obtenemos la ruta de la carpeta de s3 y del fichero y hacemos una copia temporal del fichero.
          s3_path = os.path.join(ruta, 's3')
          path_s3 = os.path.join(s3_path, sha256)
          flag = True
          exists = 0
          #puede ocurrir que el fichero este siendo usado por otro proceso, por tanto se esperara hasta que este disponible
          while flag == True:
            try:
              if os.path.exists(filename):
                shutil.copyfile(filename, path_s3)
                flag = False
              else:
                flag = False
                exists = 1
            except:
              time.sleep(2)
          if exists == 0:    
            #como el fichero es nuevo se sube a s3.    
            upload_s3(filename, path_s3, sha256, md5_hash)
            #si no existe es nuevo y se escribe en la cache a la vez que lo indicamos como nuevo en la bitacora.
            get_acl(filename, action, sha256, md5_hash, type_file, filtro, 'New', kafka_queue, bitacora_size, client_id)
            time.sleep(1)
            score = -1
            #se envia a kafka como nuevo poniendo -1 en el score.
            new_file_kafka(filename, sha256, name_file, score, client_id, kafka_queue)
            time.sleep(1)
        else:
          #si el fichero ya fue visto antes indicamos en la bitacora que fue visto poniendo si es limpio o malware y enviamos a kafka.
          score = find_score(sha256)
          get_acl(filename, action, sha256, md5_hash, type_file, filtro, str(score), kafka_queue, bitacora_size, client_id)
          new_file_kafka(filename, sha256, name_file, score, client_id, kafka_queue)
      # si el fichero esta filtrado, se indica en la bitacora como unknown.      
      elif filtro != None:
        get_acl(filename, action, sha256, md5_hash, type_file, filtro, 'Unknown', kafka_queue, bitacora_size, client_id)
  except:
    pass

#vemos si el fichero esta filtrado por tipo o no.
def get_filter_type(filter_type, type_file):
  try:
    result = 0
    for element in filter_type:
      #si esta filtrado devuelve 1 si no 0.
      if element == type_file:
        result = 1
    if result == 0:
      return 0
    elif result == 1:
      return 1
  except:
    return 0


#funcion de filtrado
def filter_function(filename, action, cola_lenta, filter_type, kafka_queue, file_size, bitacora_size, client_id):
  try:
    if os.path.exists(filename):
        tiempo = 3
        file_open(filename, tiempo)
        tamanio = get_size_file(filename)
        file_slow_queue = filename + "|" + action
        #si el tamanio es menor de 128Mb(virustotal) se envia para comenzar el proceso de subida de ficheros.
        if tamanio != None:
          #si el tamanio es el adecuado sigue adelante sino se filtra y se mete en la cola lenta.
          if tamanio <= file_size:
            type_file = file_magic_function(filename)
            time.sleep(1)
            result_type = get_filter_type(filter_type, type_file)
            #obtenemos si el fichero esta filtrado por tipo o no. si lo esta se filtra y se mete en la cola lenta.
            if result_type == 0:
              time.sleep(1)
              sha256 = create_sha_256(filename, tiempo)
              time.sleep(2)
              md5_hash = create_md5(filename, tiempo)
              time.sleep(2)
              get_parameter(filename, action, type_file, sha256, md5_hash, None, kafka_queue, bitacora_size, client_id)
            else:
              cola_lenta.put(file_slow_queue)
          else:
            cola_lenta.put(file_slow_queue)
  except:
    bitacora_string = 'Error in filter function'
    logs_function(bitacora_string)
    pass

#cola lenta, se tomara mas tiempo para hacer todo el proceso asociado al un fichero.
def threader_slow(slow_queue, kafka_queue, bitacora_size, client_id):
  while True:
    try:
      #sacamos un trabajo de la cola, si esta vacia se queda bloqueado hasta que la cola deja de estar vacia.
      worker = slow_queue.get()
      filename = worker.split("|")[0]
      action = worker.split("|")[1]
      if os.path.exists(filename):
        tiempo = 8
        #comprueba la disponibilidad del fichero y cuando lo esta sigue adelante.
        file_open(filename, tiempo)
        #hace los hashes.
        sha256 = create_sha_256(filename, tiempo)
        time.sleep(2)
        md5_hash = create_md5(filename, tiempo)
        time.sleep(2)
        #hace el tipo de fichero.
        type_file = file_magic_function(filename)
        #envia a bitacora.
        get_parameter(filename, action, type_file, sha256, md5_hash, 'Filter', kafka_queue, bitacora_size, client_id)
        time.sleep(2)
    except:
      bitacora_string = 'Error in slow queue'
      logs_function(bitacora_string)
      continue

def threader(normal_queue,lista, slow_queue, type_list, kafka_queue, file_size, bitacora_size, client_id):
    while True:
        try:
          #sacamos un trabajo de la cola, si esta vacia se queda bloqueado hasta que la cola deja de estar vacia.
          worker = normal_queue.get()
          filename = worker.split("|")[0]
          action = worker.split("|")[1]
          if (os.path.exists(filename) and os.path.isfile(filename)):
              #enviamos el fichero a comenzar el proceso.
              filter_function(filename, action, slow_queue, type_list, kafka_queue, file_size, bitacora_size, client_id)
              time.sleep(0.5)
          elif (os.path.isdir(filename) and os.path.exists(filename)):
            #si es un directorio el elemento capturado recorremos todos sus elementos y los enviamos al proceso normal de ficheros.
            for dirpath, dirnames, filenames in os.walk(filename):
              for files in filenames:
                  path = os.path.join(dirpath, files)
                  if os.path.exists(path):
                    filter_function(path, action, slow_queue, type_list, kafka_queue, file_size, bitacora_size, client_id)
                    time.sleep(0.5)
        except:
          bitacora_string = 'Error in normal queue'
          logs_function(bitacora_string)
          continue

def threader_log(queue_log,filter_list, kafka_queue, bitacora_size, client_id):
  while True:
    try:
      #sacamos un trabajo de la cola, si esta vacia se queda bloqueado hasta que la cola deja de estar vacia.
      worker_new = queue_log.get()
      bitacira_string = ''
      for elements in worker_new:
        #en elemts[0] estara el tipo de evento del 1-5.
        #lo que haremos es que dependiendo del tipo de evento sacaremos un log a la bitacora distinto.
        if elements[0] == 2:
          valor = search_in_list(elements[1], filter_list)
          if valor == 0:
            bitacira_string = "\"namespace_uuid\":\"" + str(client_id) + '\",\"endpoint_uuid\":\"' + str(client_id) + '\",\"type\":\"file_information\",\"filename\":\"' + elements[1] + '\",\"action\":\"deleted\"}'
            bitacora_writer('information', bitacira_string, kafka_queue, bitacora_size)
        if elements[0] == 4:
          valor = search_in_list(elements[1], filter_list)
          if valor == 0:
            bitacira_string += "\"namespace_uuid\":\"" + str(client_id) + '\",\"endpoint_uuid\":\"' + str(client_id) + '\",\"type\":\"file_information\",\"filename\":\"' + elements[1] + '\",\"action\":\"renamed to '
        if elements[0] == 5:
          valor = search_in_list(elements[1], filter_list)
          if valor == 0 and (os.path.isfile(elements[1]) or os.path.isdir(elements[1])):
            bitacira_string += elements[1] + '\"}'
            bitacora_writer('information', bitacira_string, kafka_queue, bitacora_size)
    except:
      bitacira_string = 'Error in logs function'
      logs_function(bitacira_string)
      continue
      
