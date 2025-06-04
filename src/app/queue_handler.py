# """
# Handles message queue consumption for RabbitMQ and SQS.

# This module receives stock data, applies volatility analysis indicators, and sends the
# processed results to the output handler.
# """

# import json
# import os
# import time

# import boto3
# import pika
# from botocore.exceptions import BotoCoreError, NoCredentialsError

# from app.logger import setup_logger
# from app.output_handler import send_to_output
# from app.processor import analyze_volatility

# # Initialize logger
# logger = setup_logger(__name__)

# # Queue type: "rabbitmq" or "sqs"
# QUEUE_TYPE = os.getenv("QUEUE_TYPE", "rabbitmq").lower()

# # RabbitMQ config
# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
# RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "stock_analysis")
# RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "volatility_analysis_queue")
# RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "#")
# RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# # SQS config
# SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
# SQS_REGION = os.getenv("SQS_REGION", "us-east-1")

# # Initialize boto3 client
# sqs_client = None
# if QUEUE_TYPE == "sqs":
#     try:
#         sqs_client = boto3.client("sqs", region_name=SQS_REGION)
#         logger.info(f"SQS client initialized for region {SQS_REGION}")
#     except (BotoCoreError, NoCredentialsError) as e:
#         logger.error("Failed to initialize SQS client: %s", e)
#         sqs_client = None


# def connect_to_rabbitmq() -> pika.BlockingConnection:
#     """
#     Establishes a connection to RabbitMQ, retrying up to 5 times on failure.

#     Returns
#     -------
#         pika.BlockingConnection: A connection object to interact with RabbitMQ.

#     Raises
#     ------
#         ConnectionError: If unable to connect to RabbitMQ after retries.
#     """
#     retries: int = 5
#     while retries > 0:
#         try:
#             # Attempt to establish a connection to RabbitMQ
#             connection: pika.BlockingConnection = pika.BlockingConnection(
#                 pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host=RABBITMQ_VHOST)
#             )
#             if connection.is_open:
#                 logger.info("Connected to RabbitMQ (vhost=%s)", RABBITMQ_VHOST)
#                 return connection
#         except Exception as e:
#             # Log the exception and retry after a delay
#             retries -= 1
#             logger.warning("RabbitMQ connection failed: %s. Retrying in 5s...", e)
#             time.sleep(5)

#     # Raise an error if all retries fail
#     raise ConnectionError("Could not connect to RabbitMQ after retries")


# def consume_rabbitmq() -> None:
#     """
#     Consume and process messages from RabbitMQ.

#     This function connects to RabbitMQ, sets up an exchange, queue, and binding,
#     and starts consuming messages from the queue. When a message is received,
#     it attempts to parse the message as JSON and calls `analyze_volatility` to
#     process the message. If the processing is successful, it sends the result
#     to the output handler and acknowledges the message. If there is an error
#     processing the message, it logs the error and either requeues the message
#     or rejects it depending on the error.

#     Raises
#     ------
#         ConnectionError: If unable to connect to RabbitMQ after retries.
#     """
#     connection: pika.BlockingConnection = connect_to_rabbitmq()
#     channel: pika.channel.Channel = connection.channel()

#     # Set up exchange, queue, and binding
#     channel.exchange_declare(exchange=RABBITMQ_EXCHANGE, exchange_type="topic", durable=True)
#     channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
#     channel.queue_bind(
#         exchange=RABBITMQ_EXCHANGE, queue=RABBITMQ_QUEUE, routing_key=RABBITMQ_ROUTING_KEY
#     )

#     def callback(
#         ch: pika.channel.Channel,
#         method: pika.spec.Basic.Deliver,
#         properties: pika.spec.BasicProperties,
#         body: bytes,
#     ) -> None:
#         """
#         Callback for processing messages from RabbitMQ.

#         Args:
#         ----
#             ch (pika.channel.Channel): The channel object.
#             method (pika.spec.Basic.Deliver): The message delivery object.
#             properties (pika.spec.BasicProperties): The message properties.
#             body (bytes): The message body as bytes.
#         """
#         try:
#             message: dict[str, Any] = json.loads(body)
#             logger.info("Received message: %s", message)

#             result: dict[str, Any] = analyze_volatility(message["symbol"], message["data"])
#             send_to_output(result)

#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except json.JSONDecodeError:
#             logger.error("Invalid JSON: %s", body)
#             ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
#         except Exception as e:
#             logger.error("Error processing message: %s", e)
#             ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

#     # Start consuming messages from the queue
#     channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)
#     logger.info("Waiting for messages from RabbitMQ...")

#     try:
#         channel.start_consuming()
#     except KeyboardInterrupt:
#         logger.info("Stopping RabbitMQ consumer...")
#         channel.stop_consuming()
#     finally:
#         connection.close()
#         logger.info("RabbitMQ connection closed.")


# def consume_sqs() -> None:
#     """
#     Consume and process messages from AWS SQS.

#     This function continuously polls for messages in the configured SQS queue.
#     When a message is received, it attempts to parse the message as JSON and
#     calls `analyze_volatility` to process the message. If the processing is
#     successful, it sends the result to the output handler and deletes the SQS
#     message. If there is an error processing the message, it logs the error and
#     retries.

#     Returns
#     -------
#         None
#     """
#     if not sqs_client or not SQS_QUEUE_URL:
#         logger.error("SQS not initialized or missing queue URL.")
#         return

#     logger.info("Polling for SQS messages...")

#     while True:
#         try:
#             response: dict = sqs_client.receive_message(
#                 QueueUrl=SQS_QUEUE_URL,
#                 MaxNumberOfMessages=10,
#                 WaitTimeSeconds=10,
#             )

#             for msg in response.get("Messages", []):
#                 try:
#                     body: dict = json.loads(msg["Body"])
#                     logger.info("Received SQS message: %s", body)

#                     # Process the message
#                     result: dict = analyze_volatility(body["symbol"], body["data"])
#                     send_to_output(result)

#                     # Delete the message from SQS
#                     sqs_client.delete_message(
#                         QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"]
#                     )
#                     logger.info("Deleted SQS message: %s", msg["MessageId"])
#                 except json.JSONDecodeError:
#                     logger.error("Invalid JSON: %s", msg["Body"])
#                 except Exception as e:
#                     logger.error("Error processing SQS message: %s", e)
#         except Exception as e:
#             logger.error("SQS polling failed: %s", e)
#             time.sleep(5)


# def consume_messages() -> None:
#     """
#     Starts the appropriate message consumer based on QUEUE_TYPE.

#     Selects the appropriate message consumer based on the environment variable
#     QUEUE_TYPE, which should be either "rabbitmq" or "sqs".

#     Returns
#     -------
#         None
#     """
#     if QUEUE_TYPE == "rabbitmq":
#         consume_rabbitmq()  # Consume messages from RabbitMQ
#     elif QUEUE_TYPE == "sqs":
#         consume_sqs()  # Consume messages from SQS
#     else:
#         logger.error("Invalid QUEUE_TYPE specified. Use 'rabbitmq' or 'sqs'.")
"""Handles message queue consumption for RabbitMQ and SQS.

This module receives stock data, applies volatility analysis, and sends
processed results to the output handler.
"""

import json
import os
import time

import boto3
import pika
from botocore.exceptions import BotoCoreError, NoCredentialsError

from app.logger import setup_logger
from app.output_handler import send_to_output
from app.processor import analyze_volatility

logger = setup_logger(__name__)

# Environment variables
QUEUE_TYPE = os.getenv("QUEUE_TYPE", "rabbitmq").lower()
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "stock_analysis")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "analysis_volatility_queue")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "#")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
SQS_REGION = os.getenv("SQS_REGION", "us-east-1")

# Initialize SQS client
sqs_client = None
if QUEUE_TYPE == "sqs":
    try:
        sqs_client = boto3.client("sqs", region_name=SQS_REGION)
        logger.info(f"SQS client initialized for region {SQS_REGION}")
    except (BotoCoreError, NoCredentialsError) as e:
        logger.error("Failed to initialize SQS client: %s", e)
        sqs_client = None


def connect_to_rabbitmq() -> pika.BlockingConnection:
    """ """
    retries = 5
    while retries > 0:
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            if conn.is_open:
                logger.info("Connected to RabbitMQ")
                return conn
        except Exception as e:
            retries -= 1
            logger.warning("RabbitMQ connection failed: %s. Retrying in 5s...", e)
            time.sleep(5)
    raise ConnectionError("Could not connect to RabbitMQ after retries")


def consume_rabbitmq() -> None:
    """ """
    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(exchange=RABBITMQ_EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.queue_bind(
        exchange=RABBITMQ_EXCHANGE, queue=RABBITMQ_QUEUE, routing_key=RABBITMQ_ROUTING_KEY
    )

    def callback(ch, method, properties, body: bytes) -> None:
        """

        :param ch: param method:
        :param properties: param body: bytes:
        :param body: bytes:
        :param body: bytes:
        :param body: bytes:
        :param method: param body: bytes:
        :param body: bytes:
        :param body: 
        :type body: bytes :
        :param body: 
        :type body: bytes :
        :param body: bytes: 

        
        """
        try:
            message = json.loads(body)
            logger.info("Received message: %s", message)

            symbol = message.get("symbol")
            data = message.get("data", {})
            result = {
                "symbol": symbol,
                "timestamp": message.get("timestamp"),
                "source": "VolatilityAnalysis",
                "analysis": analyze_volatility(symbol, data),
            }

            send_to_output(result)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError:
            logger.error("Invalid JSON: %s", body)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error("Error processing message: %s", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)
    logger.info("Waiting for messages from RabbitMQ...")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Gracefully stopping RabbitMQ consumer...")
        channel.stop_consuming()
    finally:
        connection.close()
        logger.info("RabbitMQ connection closed.")


def consume_sqs() -> None:
    """ """
    if not sqs_client or not SQS_QUEUE_URL:
        logger.error("SQS not initialized or missing queue URL.")
        return

    logger.info("Polling for SQS messages...")

    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
            )

            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg["Body"])
                    logger.info("Received SQS message: %s", body)

                    symbol = body.get("symbol")
                    data = body.get("data", {})
                    result = {
                        "symbol": symbol,
                        "timestamp": body.get("timestamp"),
                        "source": "VolatilityAnalysis",
                        "analysis": analyze_volatility(symbol, data),
                    }

                    send_to_output(result)
                    sqs_client.delete_message(
                        QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"]
                    )
                    logger.info("Deleted SQS message: %s", msg["MessageId"])
                except Exception as e:
                    logger.error("Error processing SQS message: %s", e)
        except Exception as e:
            logger.error("SQS polling failed: %s", e)
            time.sleep(5)


def consume_messages() -> None:
    """Selects the consumer based on QUEUE_TYPE environment variable."""
    if QUEUE_TYPE == "rabbitmq":
        consume_rabbitmq()
    elif QUEUE_TYPE == "sqs":
        consume_sqs()
    else:
        logger.error("Invalid QUEUE_TYPE specified. Use 'rabbitmq' or 'sqs'.")
