import json
from django.core.serializers.json import DjangoJSONEncoder

def make_json_data(data: dict):
    """Encodes and decodes dict via DjangoJSONEncoder to standardize dates and decimals."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))

def build_envelope(data=None, exception=False, errors=None, token=None, status_code=200):
    """Constructs the exact ASRLM final response structure."""
    return {
        "Data": data if data is not None else {},
        "Exception": exception,
        "Errors": errors,
        "Token": token,
        "Status_Code": status_code
    }
