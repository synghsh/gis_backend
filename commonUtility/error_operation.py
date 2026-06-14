from errorcodes import (CODE, MESSAGE, BUSSINESS_EXC_STATUS, INFO_EXC_STATUS, SYS_EXC_STATUS, WARN_EXC_STATUS, SE002, SE002MESSAGE, INTERNAL_SERVER_ERROR)

class customExceptionBuilder:
    def __init__(self, logger, errorCode, errorMessage):
        self.logger = logger
        self.logger.warning('|----------| Custom Exception Builder: Initiating |---------|')
        self.errorkeys = ['Business_Errors', 'Info', 'System_Errors', 'Warnings']
        self.errordisplay = [[], [], [], []]
        self.ek, self.ec = [], []
        self.exception, self.response, self.statusCode = True, {}, INTERNAL_SERVER_ERROR
        try:
            self.errorCode, self.errorMessage = errorCode, errorMessage
            self.logger.error(f'Custom Exception -> Code: {self.errorCode}, Message: {self.errorMessage}')
            typeOfErr = self.errorCode[0:2]
            self.logger.warning(f"Type of exception identified: {typeOfErr}")
            self.err = str(typeOfErr)
            self.statusCode = self.select_status_code()
            e_d_p = self.select_err_disp_posix()
            self.ek.append(CODE)
            self.ec.append(self.errorCode)
            self.ek.append(MESSAGE)
            self.ec.append(self.errorMessage)
            self.errordisplay[e_d_p].append(dict(zip(self.ek, self.ec)))
            self.error = dict(zip(self.errorkeys, self.errordisplay))
        except Exception as e:
            self.logger.exception(e)
            self.ek.append(CODE)
            self.ec.append(SE002)
            self.ek.append(MESSAGE)
            self.ec.append(SE002MESSAGE)
            self.errordisplay[2].append(dict(zip(self.ek, self.ec)))
            self.err = dict(zip(self.errorkeys, self.errordisplay))
            self.error, self.statusCode = self.err, INTERNAL_SERVER_ERROR
        finally:
            self.logger.warning(f'|----------| Custom Exception Builder: Finished with Status {self.statusCode} |---------|')
    
    def select_status_code(self):
        scSwitcher = {
            'BE': BUSSINESS_EXC_STATUS,
            'IN': INFO_EXC_STATUS,
            'SE': SYS_EXC_STATUS,
            'WA': WARN_EXC_STATUS
        }
        return scSwitcher.get(self.err, INTERNAL_SERVER_ERROR)
    
    def select_err_disp_posix(self):
        edSwitcher = {
            'BE': 0,
            'IN': 1,
            'SE': 2,
            'WA': 3
        }
        return edSwitcher.get(self.err, 2)
