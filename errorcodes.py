# ERROR FRAMEWORK
"""
    Master Error Framework
"""
# Error Keys
DATA = 'Data'
ERROR = 'Errors'
TOKEN = 'Token'
STATUS_CODE = 'status_code'
EXCEPTION = 'Exception'
CODE = 'Code'
MESSAGE = 'Message'
STATUS_MESSAGE = 'Status Message'

# SUCCESS CODES ====
SUCCESS_STATUS = 200

SUCCESSCODE = 'SUCCESS001'
SUCCESSMESSAGE = 'Success'

SUCCESSCODE2 = 'SUCCESS002'
SUCCESSMESSAGE2 = 'OTP Generated Successfully'

SUCCESSCODE3 = 'SUCCESS003'
SUCCESSMESSAGE3 = 'User Logout Successfully'

SUCCESSCODE4 = 'SUCCESS004'
SUCCESSMESSAGE4 = 'User Login Successfully'

SUCCESSCODE5 = 'SUCCESS005'
SUCCESSMESSAGE5 = 'User Registered Successfully'

# Generic Messages map
SUCCESS_MESSAGES = {
    "SUCCESS001": "Success",
    "SUCCESS002": "OTP Generated Successfully",
    "SUCCESS003": "User Logout Successfully",
    "SUCCESS004": "User Login Successfully",
    "SUCCESS005": "User Registered Successfully"
}

# BUSINESS ERRORS
BUSSINESS_EXC_STATUS = 310

BE001 = 'BE001'
BE001MESSAGE = 'Missing Mandatory Inputs.'

BE002 = 'BE002'
BE002MESSAGE = '{} not found'

BE003 = 'BE003'
BE003MESSAGE = '{} found'

BE007 = 'BE007'
BE007MESSAGE = 'Condition Not Satisfied.'

BE008 = 'BE008'
BE008MESSAGE = 'File Upload Failure'

BE014 = 'BE014'
BE014MESSAGE = 'No Data Available.'

# INFORMATIONAL ERRORS
INFO_EXC_STATUS = 311

IN006 = 'IN006'
IN006MESSAGE = "Username Must be a Phone Number or an Email"

IN002 = "IN002"
IN002MESSAGE = "Please Provide a Valid Primary Phone Number"

# SYSTEM ERRORS
SYS_EXC_STATUS = 312

SE001 = 'SE001'
SE001MESSAGE = 'Oops!!! Something Went Wrong. Please Try Again Later.'

SE002 = 'SE002'
SE002MESSAGE = 'Operational Error'

SE003 = 'SE003'
SE003MESSAGE = 'Database Connection Error'

# WARNINGS
WARN_EXC_STATUS = 313

WA001 = 'WA001'
WA001MESSAGE = 'Unauthorized Access'

WA003 = 'WA003'
WA003MESSAGE = 'OTP Expired'

WA004 = 'WA004'
WA004MESSAGE = 'No OTP Found. Please Request for a New OTP'

WA006 = 'WA006'
WA006MESSAGE = 'Invalid OTP'

WA007 = 'WA007'
WA007MESSAGE = 'Duplicate {} Entry Found'

WA010 = 'WA010'
WA010MESSAGE = 'Your account is currently inactive. Please contact the administrator.'

# CLIENT & SERVER STATUS CODES
BAD_REQUEST = 400
UNAUTHORIZE_ACCESS = 401
FORBIDDEN = 403
USER_NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
REQUEST_TIMEOUT = 408
INTERNAL_SERVER_ERROR = 500
