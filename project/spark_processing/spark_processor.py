"""
Spark Streaming Processor
Processes real-time bank transactions from Kafka using Apache Spark
Integrates with ML model for fraud detection
"""

import os
import sys
import json
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_json, struct
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SparkStreamingProcessor:
    """
    Spark Streaming processor for real-time fraud detection.
    Reads transactions from Kafka, applies ML model, and stores results.
    """
    
    def __init__(self):
        self.spark = None
        self.kafka_df = None
        self.model_path = config.MODEL_PATH
        
    def create_spark_session(self):
        """Create and configure Spark session"""
        logger.info("Creating Spark session...")
        
        self.spark = SparkSession.builder \
            .appName(config.SPARK_APP_NAME) \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0") \
            .config("spark.sql.streaming.checkpointLocation", config.SPARK_CHECKPOINT_DIR) \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .getOrCreate()
            
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("Spark session created successfully")
        return self.spark
    
    def get_transaction_schema(self):
        """Define the transaction schema"""
        return StructType([
            StructField("transaction_id", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("amount", DoubleType(), True),
            StructField("location", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("merchant", StringType(), True),
            StructField("card_present", BooleanType(), True)
        ])
    
    def read_from_kafka(self):
        """Read streaming data from Kafka"""
        logger.info(f"Reading from Kafka topic: {config.KAFKA_TOPIC}")
        
        self.kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", config.KAFKA_TOPIC) \
            .option("startingOffsets", "earliest") \
            .option("maxOffsetsPerTrigger", 100) \
            .load()
            
        logger.info("Kafka stream connected successfully")
        return self.kafka_df
    
    def parse_transactions(self, kafka_df):
        """Parse JSON transactions from Kafka"""
        logger.info("Parsing transaction data...")
        
        schema = self.get_transaction_schema()
        
        parsed_df = kafka_df \
            .select(from_json(col("value").cast("string"), schema).alias("data")) \
            .select("data.*")
            
        return parsed_df
    
    def process_transactions(self, parsed_df):
        """
        Process transactions - apply fraud detection logic.
        In production, this would call the ML model.
        """
        logger.info("Processing transactions...")
        
        # For prototype: Apply rule-based fraud detection
        # In production: Use ML model for predictions
        processed_df = parsed_df \
            .withColumn("is_fraud", 
                (col("amount") > 5000) | (~col("card_present") & (col("amount") > 1000))
            ) \
            .withColumn("fraud_probability",
                when(col("amount") > 5000, 0.9)
                .when(~col("card_present") & (col("amount") > 1000), 0.7)
                .when(col("amount") > 3000, 0.4)
                .otherwise(0.1)
            ) \
            .withColumn("processed_timestamp", col("timestamp"))
            
        return processed_df
    
    def write_to_kafka(self, processed_df):
        """Write processed results back to Kafka"""
        logger.info("Writing processed transactions to Kafka...")
        
        output_topic = "processed-transactions"
        
        query = processed_df \
            .select(to_json(struct("*")).alias("value")) \
            .writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
            .option("topic", output_topic) \
            .option("checkpointLocation", f"{config.SPARK_CHECKPOINT_DIR}/kafka") \
            .outputMode("append") \
            .start()
            
        return query
    
    def write_to_console(self, processed_df):
        """Write processed data to console for debugging"""
        logger.info("Writing processed transactions to console...")
        
        query = processed_df \
            .writeStream \
            .format("console") \
            .option("truncate", "false") \
            .outputMode("append") \
            .start()
            
        return query
    
    def start_processing(self):
        """Start the complete streaming pipeline"""
        # Create Spark session
        self.create_spark_session()
        
        # Read from Kafka
        kafka_df = self.read_from_kafka()
        
        # Parse transactions
        parsed_df = self.parse_transactions(kafka_df)
        
        # Process transactions (fraud detection)
        processed_df = self.process_transactions(parsed_df)
        
        # Write results
        # For prototype, write to console
        query = self.write_to_console(processed_df)
        
        # Also write to Kafka for downstream processing
        # self.write_to_kafka(processed_df)
        
        logger.info("Streaming processor started. Waiting for data...")
        
        # Wait for termination
        query.awaitTermination()
    
    def stop(self):
        """Stop the Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("Spark session stopped")


# Import for when function
from pyspark.sql.functions import when


def main():
    """Main function to run Spark streaming processor"""
    processor = SparkStreamingProcessor()
    
    try:
        processor.start_processing()
    except KeyboardInterrupt:
        logger.info("Stopping processor...")
    finally:
        processor.stop()


if __name__ == "__main__":
    main()

