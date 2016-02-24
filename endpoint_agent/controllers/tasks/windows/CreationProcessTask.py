import json
import logging
import os
import time
import psutil
import wmi
import pythoncom
import win32api
import win32con
import win32process
from controllers.tasks.Task import Task
from managers.QueueManager import QueueManager

class CreationProcessTask(Task):

    def prepareImpl(self, config=None):
        pass


    def doTaskImpl(self):
        try:
            pythoncom.CoInitialize()
            connection = wmi.WMI()
            self.running = True
            #Se inicia la monitoricion de procesos en tiempo real, en este caso se monitorizaran los procesos que se crean.
            watcher = connection.Win32_Process.watch_for("creation")
            while self.running == True:
                try:
                    #Cuando un nuevo proceso se cree en el sistema entra en el try anterior y capturamos el proceso creado.
                    new_process = watcher()
                    bitacora_string = dict()
                    #obtenemos el ejecutable binario que ejecuta dicho proceso
                    executable = self.get_executable(new_process, new_process.ProcessID, new_process.Caption, new_process.CommandLine, new_process.Description)
                    #obtenemos caracteristicas adicionales del proceso.
                    bitacora_string['namespace_uuid'] = Task.client_id
                    bitacora_string['endpoint_uuid'] = Task.client_id
                    bitacora_string['type'] = 'process'
                    bitacora_string['action'] = 'creation'
                    #formamos un string informativo para la bitacora.
                    if new_process.ProcessID != None:
                        bitacora_string['pid'] = new_process.ProcessID
                    if new_process.Caption != None:
                        bitacora_string['name'] = new_process.Caption
                    if executable != None:
                        bitacora_string['application'] = executable

                    self.characterist(new_process, bitacora_string)

                    try:
                       #obtenemos el proceso padre en caso de existir
                       parent_process = psutil.Process(new_process.ParentProcessId)
                       if parent_process:
                           try:
                               #obtenemos el ejecutable binario del proceso padre y metemos en la bitacora la informacion del proceso hijo y padre.
                               executable_parent = self.get_parent_executable(new_process.ParentProcessId, parent_process.name())
                               bitacora_string['parent_application'] = executable_parent
                           except Exception as e:
                                logging.getLogger('application').error(e)
                    except:
                        continue
                    bitacora_string['timestamp'] = int(time.time())
                    string_json = json.dumps(bitacora_string)
                    logging.getLogger('binnacle').info(string_json)
                    QueueManager.putOnQueue('kafka', {'topic': 'rb_ioc', 'content': string_json})

                except Exception as e:
                    continue

        except Exception as e:
            logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()


    def shutdownImpl(self):
        self.running = False


    def characterist(self, process, bitacora_string):
       try:
           #se obtiene la prioridad del proceso
          if process.Priority:
            bitacora_string['priority'] = process.Priority
          #se obtiene el identificador del usuario que ha creado el proceso
          if process.SessionId:
             bitacora_string['sessionId'] = process.SessionId
       except:
          pass

    #funcion que obtiene el ejecutable binario padre de un proceso.
    def get_parent_executable(self,pid, name):
       try:
          executable = self.get_process_executable(pid)
          if not executable:
              executable = self.get_process_executable_by_name(name)
          if not executable:
              return None
          else:
               return executable
       except Exception as e:
            logging.getLogger('application').error(e)
            return None
            pass


    #Funcion que obtiene el ejecutable binario de un proceso a traves del nombre.
    def get_process_executable_by_name(self,filename,cmdline=None):
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
    def get_process_executable(self,pid):
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
    def get_executable(self,process, pid, name, commandLine, description):
       try:
          #se intenta obtener el ejecutable binario de forma facil.
          executable = process.ExecutablePath
          if not executable:
              #se intenta obtener el ejecutable binario a traves del PID.
              executable = self.get_process_executable(pid)
              if not executable:
                  #si no se obtiene, se reintenta, debido a la suceptibilidad a errores.
                  executable = process.ExecutablePath
              if not executable:
                   #se intenta obtener el ejecutable binario a traves del nombre.
                   executable = self.get_process_executable_by_name(name)
              if not executable:
                  if commandLine:
                      #si en los parametros existe la variable commandLine se intenta obtener a traves de ella y el nombre.
                      executable = self.get_process_executable_by_name(name, commandLine)
              if not executable:
                  if commandLine:
                      #si no se puede obtener con metodos anteriores pues se intenta obtener a traves de la descripcion y el commandLine.
                      executable = self.get_process_executable_by_name(description, commandLine)
          #si por lo que sea no se obtiene porque no existe pues retornamos None, sino el ejecutable binario.
          if not executable:
              return None
          else:
               return executable
       except:
          pass