import os
import threading
import time
import win32con
import win32file
import wmi
import logging
import pythoncom
from controllers.tasks.Task import Task
from managers.FilterManager import FilterManager
from managers.WindowsValueManager import WindowsValueManager
from managers.QueueManager import QueueManager


class MonitorDiskPartition(Task):

    def prepareImpl(self, config=None):
        pass


    def doTaskImpl(self):
        try:
            pythoncom.CoInitialize()
            self.running = True
            connection = wmi.WMI()
            # lista que controla que particion logica del disco existe y esta activo en el sistema y cual no
            threads_state = []
            # lista de particion logica del disco.
            threads_list = []
            # lista con las posibles particiones logicas del discos del sistema
            partitions_logical_disk = []

            while self.running:
                try:
                    WindowsValueManager.set_values()
                    # si es una particion logica del disco fisico se incluira a la lista para monitorizarlo y evitar asi los discos de red
                    for physical_disk in connection.Win32_DiskDrive():
                        for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
                            for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                                if len(partitions_logical_disk) == 0:
                                    # si la lista de discos esta vacia es porque acabamos de empezar
                                    # se introducen en la lista el disco encontrado
                                    disk_partition = logical_disk.Caption + "\\"
                                    partitions_logical_disk.append(disk_partition)
                                    threads_state.append(0)
                                else:
                                    # si existe en la lista algun disco se compara
                                    # si coincide no se introduce en la lista (match = 1)
                                    # si no existe ningun disco en la lista igual que ese, se introduce y se mete en la lista de estados en su misma posicion un 0.
                                    match = 0
                                    for element in partitions_logical_disk:
                                        disk_partition = logical_disk.Caption + "\\"
                                        if element == disk_partition:
                                            match = 1


                                    if match == 0:
                                        disk_partition = logical_disk.Caption + "\\"
                                        partitions_logical_disk.append(disk_partition)
                                        threads_state.append(0)
                    threads_position = 0
                    # se recorre la lista de discos y comprobamos que su ruta existe
                    for path_logical_disk in partitions_logical_disk:
                        if os.path.exists(path_logical_disk):
                            # si existe la ruta y el disco estaba inactivo se crea hilo
                            # como estaba inactivo ponemos un uno en referencia a que ahora si lo esta en su posicion correspondiente
                            if threads_state[threads_position] == 0:
                                thread_monitor_disk = threading.Thread(target=self.changes_files, args=(path_logical_disk,),name=path_logical_disk)
                                threads_list.append(thread_monitor_disk)
                                thread_monitor_disk.start()
                            threads_state[threads_position] = 1
                        # Si no existe la ruta pero el disco estaba activo en la ultima comprobacion se pone como inactivo en su posicion correspondiente.
                        else:
                            if threads_state[threads_position] == 1:
                                threads_state[threads_position] = 0
                        threads_position = threads_position + 1

                    time.sleep(2)
                except:
                    continue
        except Exception as e:
            logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()


    def shutdownImpl(self):
        self.running = False


    def changes_files(self, logical_disk):
        # Acciones que pueden ocurrir para que salte un evento
        ACTIONS = {
            1: "Created",
            2: "Deleted",
            3: "Updated",
            4: "Renamed from something",
            5: "Renamed to something"
        }

        FILE_LIST_DIRECTORY = 0x0001

        # Ruta a monitorizar
        path_to_watch = logical_disk
        # configuracion de la monitorizacion
        hDir = win32file.CreateFile(
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

            try:

                # Monitorizacion (ruta, buffer, subcarpetas a monitorizar (si o no), cambios con los que salta el evento)
                results = win32file.ReadDirectoryChangesW(
                    hDir,
                    5012,
                    True,
                    win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                    win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                    win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                    win32con.FILE_NOTIFY_CHANGE_SIZE |
                    win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                    win32con.FILE_NOTIFY_CHANGE_SECURITY,
                    None,
                    None
                )
                # mientras exista resultados asociados a un evento
                send_list = []

                # Del evento capturado se coge la accion y el archivo implicado en el evento.
                for action, file in results:
                    # completamos el nombre del fichero implicado en un evento.
                    full_filename = os.path.join(path_to_watch, file)
                    temporal_list = [action, full_filename]
                    # introducimos en la lista de eventos la accion y el fichero implicado.
                    send_list.append(temporal_list)
                    # si la ruta existe y es un fichero.
                    if os.path.exists(full_filename) and os.path.isfile(full_filename):
                        match = FilterManager.get_filter_path(full_filename)
                        # si el fichero no esta filtrado por ruta y la accion no es borrar, es decir, el fichero existe para trabajar con el mismo.
                        if match == False and action != 2:
                            file_action = dict()
                            file_action['filename'] = full_filename
                            # se asigna una accion dependiendo del numero relacionado a la accion
                            if action == 1:
                                file_action['action'] = 'created'
                            else:
                                file_action['action'] = 'updated'
                            # se encola el evento en la cola normal
                            QueueManager.putOnQueue('file_capture',file_action)

                        # en caso de ser un directorio solo se mandara el evento si es nuevo.
                        elif os.path.isdir(full_filename) and action == 1 and match == False:
                            #si no esta filtrado el directorio por ruta se trabajara con el siempre y cuando se haya creado, ya que si es actualizado sera un fichero de dentro.
                            file_action = dict()
                            file_action['filename'] = full_filename
                            file_action['action'] = 'created'
                            QueueManager.putOnQueue('file_capture',file_action)
                # se mete toda la informacion asociado a un evento en la cola de informacion
                QueueManager.putOnQueue('file_event',send_list)
                # si la ruta raiz (en este caso la particion de windows, ya que puede ser un usb y desaparecer) deja de existir se acaba el bucle.
                if not os.path.exists(path_to_watch):
                    exit_thread = 0

            except Exception:
                continue