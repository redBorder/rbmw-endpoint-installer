import socket
import wmi
import pythoncom
import logging

class WindowsValueManager():

    values = dict()

    @staticmethod
    def set_values():
        try:
            pythoncom.CoInitialize()
            WindowsValueManager.values['sensor_name'] = socket.gethostbyname_ex (socket.gethostname ())[0]
            #Mientras existan y no sean nulas, se cogen la MAC, IP e IP de Subred del PC, la union de todas que no son nulas da las del PC
            for parameters_network in wmi.WMI ().Win32_NetworkAdapterConfiguration ():
                if parameters_network.MACAddress != None and parameters_network.DNSDomain != None and parameters_network.IPAddress != None and parameters_network.IPSubnet != None and parameters_network.DefaultIPGateway != None:
                    WindowsValueManager.values['client_mac'] = parameters_network.MACAddress.lower()
                    WindowsValueManager.values['domain_name'] = parameters_network.DNSDomain
                    WindowsValueManager.values['endpoint_agent'] = parameters_network.IPAddress[0]
                    WindowsValueManager.values['src_net_name'] = parameters_network.IPSubnet[0]
            #Mientras existan y no sean nulas, se cogen el nombre de la cuenta de usuario, su perfil asociado y el tipo de cuenta de usuario
            for parameters_profile in wmi.WMI ().Win32_NetworkLoginProfile ():
                if parameters_profile.Name != None:
                    WindowsValueManager.values['client_id'] = parameters_profile.Name
        except Exception as e:
            logging.getLogger('application').error(e)
        finally:
            pythoncom.CoUninitialize()



    @staticmethod
    def get_values():
        return WindowsValueManager.values
