import logging

logger = logging.getLogger(__name__)

def process_data(data):
    obj = data.get("object")
    result = obj.method()
    return result