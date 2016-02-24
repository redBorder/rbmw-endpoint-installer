from boto.s3.key import Key
import boto
from boto.s3.connection import OrdinaryCallingFormat
import time
import os
import shutil

class S3Manager():

    configuration = None
    path = None

    # Method to load configuration for S3
    @staticmethod
    def load_config(config, path):
        S3Manager.configuration = config.getConfigProperties()
        S3Manager.path = path


    # Method to get file from S3
    @staticmethod
    def get_s3_file(sha256):
        s3_path = os.path.join(S3Manager.path, 's3', sha256)
        return s3_path


    @staticmethod
    def create_temp_file(old_file, new_file):
        flag = False
        count = 0
        while flag == False:
            try:
                if count < 5:
                    shutil.copyfile(old_file, new_file)
                    flag = True
                    return "ok"
                else:
                    flag = True
                    return "error"
            except:
                time.sleep(15)
                count += 1


    # Method to upload files to S3
    @staticmethod
    def upload_s3(filename, sha256):
        s3_file_upload = S3Manager.get_s3_file(sha256)
        aws_access = S3Manager.configuration['access_key']
        aws_secret = S3Manager.configuration['secret_key']
        bucket_name = S3Manager.configuration['s3_bucket']
        copy_status = S3Manager.create_temp_file(filename,s3_file_upload)
        if copy_status == "ok":
            count = 0
            flag = True
            while flag == True:
                try:
                    #realizamos la conexion a s3 ignorando el certificado
                    conn = boto.connect_s3(aws_access_key_id = aws_access,aws_secret_access_key = aws_secret,host = 's3.redborder.cluster',validate_certs=False, calling_format = OrdinaryCallingFormat())
                    #obtenemos el bucket donde subir el fichero
                    bucket = conn.get_bucket(bucket_name, validate=False)
                    #subimos el fichero con un nombre determinado, en este caso el sha256
                    k = Key(bucket)
                    k.key = sha256
                    #subimos el fichero
                    k.set_contents_from_filename(s3_file_upload)
                    time.sleep(1)
                    flag = False
                    if os.path.exists(s3_file_upload):
                        os.remove(s3_file_upload)
                    return "upload"
                except Exception as e:
                    print(e)
                    #si falla y solo lo hemos intentado una vez se reintenta.
                    if count < 2:
                        count += 1
                        time.sleep(2)
                    else:
                        #si hemos llegado al tope dejamos de intentarlo.
                        flag = False
                        return "error_upload"
        else:
            return "error_copy"