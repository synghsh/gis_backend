class MandatoryInputMissingException(Exception):
    def __init__(self, message):
        super(MandatoryInputMissingException, self).__init__(message)
        self.message = message

class DatabaseException(Exception):
    def __init__(self, message):
        super(DatabaseException, self).__init__(message)
        self.message = message

class BadRequest(Exception):
    def __init__(self, message):
        super(BadRequest, self).__init__(message)
        self.message = message

class InternalServerError(Exception):
    def __init__(self, message):
        super(InternalServerError, self).__init__(message)
        self.message = message

class MethodNotAllowed(Exception):
    def __init__(self, message):
        super(MethodNotAllowed, self).__init__(message)
        self.message = message

class InvalidStatusException(Exception):
    def __init__(self, message):
        super(InvalidStatusException, self).__init__(message)
        self.message = message

class InvalidUsernameFormatException(Exception):
    def __init__(self, message):
        super(InvalidUsernameFormatException, self).__init__(message)
        self.message = message

class InvalidPhoneNumberException(Exception):
    def __init__(self, message):
        super(InvalidPhoneNumberException, self).__init__(message)
        self.message = message

class InvalidEmailIdException(Exception):
    def __init__(self, message):
        super(InvalidEmailIdException, self).__init__(message)
        self.message = message

class OperationalException(Exception):
    def __init__(self, message):
        super(OperationalException, self).__init__(message)
        self.message = message

class InvalidOtpException(Exception):
    def __init__(self, message):
        super(InvalidOtpException, self).__init__(message)
        self.message = message

class NoOtpDataFoundException(Exception):
    def __init__(self, message):
        super(NoOtpDataFoundException, self).__init__(message)
        self.message = message

class OtpExpiredException(Exception):
    def __init__(self, message):
        super(OtpExpiredException, self).__init__(message)
        self.message = message

class UploadFailedException(Exception):
    def __init__(self, message):
        super(UploadFailedException, self).__init__(message)
        self.message = message

class DownloadFailedException(Exception):
    def __init__(self, message):
        super(DownloadFailedException, self).__init__(message)
        self.message = message

class ItemNotFoundException(Exception):
    def __init__(self, message):
        super(ItemNotFoundException, self).__init__(message)
        self.message = message

class ItemFoundException(Exception):
    def __init__(self, message):
        super(ItemFoundException, self).__init__(message)
        self.message = message

class UnauthorizedAccessException(Exception):
    def __init__(self, message):
        super(UnauthorizedAccessException, self).__init__(message)
        self.message = message

class AlreadyLogoutException(Exception):
    def __init__(self, message):
        super(AlreadyLogoutException, self).__init__(message)
        self.message = message

class UserNotFoundException(Exception):
    def __init__(self, message):
        super(UserNotFoundException, self).__init__(message)
        self.message = message

class UserAlreadyExistException(Exception):
    def __init__(self, message):
        super(UserAlreadyExistException, self).__init__(message)
        self.message = message

class AlreadySentOtpException(Exception):
    def __init__(self, message):
        super(AlreadySentOtpException, self).__init__(message)
        self.message = message

class UserInactiveException(Exception):
    def __init__(self, message):
        super(UserInactiveException, self).__init__(message)
        self.message = message

class InvalidPasswordException(Exception):
    def __init__(self, message):
        super(InvalidPasswordException, self).__init__(message)
        self.message = message

class InvalidPasswordFormatException(Exception):
    def __init__(self, message):
        super(InvalidPasswordFormatException, self).__init__(message)
        self.message = message

