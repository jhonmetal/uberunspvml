from os import environ
import base64

class ParseConnector:
    def __init__(self, cnxString):
        #standard cnx Env username:password@server:port/database
        self.cnxString = environ[cnxString]
        if self.cnxString :
            if self.cnxString.startswith("SK|") :
                base64_bytes = cnxString.encode('ascii')
                message_bytes = base64.b64decode(base64_bytes)
                self.cnxString = message_bytes.decode('ascii')

        parser = self.cnxString.split("@")
        credetial = parser[0].split(":")
        parser[1] = parser[1].replace("/",":")
        server = parser[1].split(":")
        
        if(len(credetial) != 2 or len(server)<2):
            raise Exception("Error en la cadena de conexión, formato invalido")

        self.cnx = {
            "user" : credetial[0],
            "password" : credetial[1],
            "host" : server[0],
            "port" : server[1],
            "database" : server[2]
        }

    def get_cnx(self):
        return self.cnx
