import json
import logging
import time
import psutil
import wmi
import pythoncom
from controllers.tasks.Task import Task
from managers.QueueManager import QueueManager


class WebProcessTask(Task):

    def prepareImpl(self, config=None):
        pass

    def doTaskImpl(self):
        try:
            pythoncom.CoInitialize()
            connection = wmi.WMI()
            #Se inicia la monitoricion de procesos en tiempo real, en este caso se monitorizaran los procesos que se crean.
            watcher = connection.Win32_Process.watch_for("creation")

            self.running = True

            while self.running:
                try:
                    #Cuando un nuevo proceso se cree en el sistema entra en el try anterior y capturamos el proceso creado.
                    new_process = watcher()

                    try:
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
                               bitacora_string = dict()
                               bitacora_string['namespace_uuid'] = str(Task.client_id)
                               bitacora_string['endpoint_uuid'] = str(Task.client_id)
                               bitacora_string['type'] = 'connection'
                               bitacora_string['application'] = str(new_process.Caption)
                               bitacora_string['pid'] = new_process.ProcessID
                               bitacora_string['connections'] = new_string
                               bitacora_string['timestamp'] = int(time.time())

                               string_json = json.dumps(bitacora_string)

                               logging.getLogger('binnacle').info(string_json)
                               logging.getLogger('application').debug('data for kafka : {0}'.format(string_json))
                               QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_json})

                       except Exception:
                            continue

                    except Exception:
                        continue

                except Exception:
                    continue

        except Exception as e:
                logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()


    def shutdownImpl(self):
        self.running = False
