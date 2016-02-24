import os
import hashlib
import time
import sha3
import binascii
import win32security

class FileParameters():

    path = None

    @staticmethod
    def config(path):
        FileParameters.path = path

    @staticmethod
    def get_md5(filename, timer):
        #obtenemos el md5 de un fichero.
        md5_hash = None
        if os.path.exists(filename):
            #flag para el numero de intentos de hacer el sha256
            flag = True
            #Mientras nos de errores de permisos
            count = 0
            while flag==True:
                try:
                    file_open = open(filename, "r+b")
                    #MUY IMPORTANTE HACER LAS OPERACIONES POR SEPARADO PORQUE EL RENDIMIENTO DE LA CPU MEJORA EN TORNO AL 30 PORCIENTO
                    content = file_open.read()
                    #se crean los hash en hexadecimal
                    md5_normal = hashlib.md5(content)
                    md5_hash = md5_normal.hexdigest()
                    file_open.close()
                    flag = False
                except:
                    if count < 20:
                        time.sleep(timer)
                        count += 1
                    else:
                        flag = False
        return md5_hash

    @staticmethod
    def get_sha256(filename, timer):
        sha_256 = None
        if os.path.exists(filename):
            #flag para el numero de intentos de hacer el sha256
            flag = True
            count = 0
            while flag==True:
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
                except:
                    if count < 20:
                        time.sleep(timer)
                        count += 1
                    else:
                        flag = False
        return sha_256

    @staticmethod
    def get_file_type(filename):
        try:
            message = open(filename, 'rb').read()
            dir_file = os.path.join(FileParameters.path,'filters', 'snort_file.txt')
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
            type_file_none = 'None'
            return type_file_none

    @staticmethod
    def get_acl(filename):
        try:
            #Obtenemos toda la seguridad del fichero, es decir, las dacl(data access control list) y la seguridad para la gestion.
            security_file = win32security.GetFileSecurity(filename, win32security.DACL_SECURITY_INFORMATION)
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
                return permission_decimal_format
            else:
                return None
        except:
            return None
            pass