import requests
from requests.exceptions import ConnectionError, Timeout
import uuid
from supporting import aws
import logging
import os
import json



# Logging formatter that includes the correlation ID
formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s')

# Set up the root logger
log = logging.getLogger()
log.setLevel("INFO")
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

# Remove existing handlers
for handler in log.handlers:
    log.removeHandler(handler)

# Add a new handler with the custom formatter
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


def lambda_handler(event, context):
    database_id = os.getenv('DATABASE_ID')

    try:
        # Haal instellingen op
        database_settings = aws.dynamodb_query(table='database_settings', id=database_id)
        if not database_settings:
            log.error(f"Geen instellingen gevonden voor ID: {database_id}")
            return {'statusCode': 404, 'body': 'Settings not found'}

        test_host = database_settings[0]['host'][0]
        test_port = 8001
        url = f"http://{test_host}:{test_port}/ping" # Of een specifiek endpoint

        log.info(f"Start connectie test naar {url}")

        # Voer de request uit met een korte timeout (bijv. 5 seconden)
        # Zo voorkom je dat je Lambda onnodig lang blijft draaien (en geld kost)
        response = requests.get(url, timeout=5)

        if response.status_code == database_settings[0]['host'][1]:
            log.info(f"Success: Raspberry Pi is online. Status: {response.status_code}")
            return {
                'statusCode': 200,
                'body': json.dumps({'status': 'online', 'details': response.text})
            }
        else:
            log.warning(f"Pi reageert, maar geeft foutcode: {response.status_code}")
            return {
                'statusCode': response.status_code,
                'body': json.dumps({'status': 'error', 'message': 'Unexpected status code'})
            }

    except Timeout:
        log.error(f"Timeout: Kon geen verbinding maken met {test_host} binnen 5 seconden.")
        return {'statusCode': 408, 'body': json.dumps({'status': 'offline', 'reason': 'timeout'})}
    except ConnectionError:
        log.error(f"ConnectionError: {test_host} is onbereikbaar of weigert de verbinding.")
        return {'statusCode': 503, 'body': json.dumps({'status': 'offline', 'reason': 'connection_refused'})}
    except Exception as e:
        log.error(f"Onverwachte fout: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'internal_server_error'})}

lambda_handler(None, None)
