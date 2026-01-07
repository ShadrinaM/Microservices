import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class Database:
    _connection_pool = None
    
    @classmethod
    def initialize(cls):
        """Инициализация пула соединений с БД"""
        try:
            DATABASE_URL = os.getenv('DATABASE_URL')
            if not DATABASE_URL:
                # Формируем URL из отдельных переменных, если нужно
                db_host = os.getenv('DB_HOST', 'postgres-service.user-management.svc.cluster.local')
                db_port = os.getenv('DB_PORT', '5432')
                db_name = os.getenv('DB_NAME', 'userdb')
                db_user = os.getenv('DB_USER', 'admin')
                db_password = os.getenv('DB_PASSWORD')
                
                if not db_password:
                    raise ValueError("DB_PASSWORD environment variable is not set")
                
                DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            logger.info(f"Connecting to database at {db_host}")
            cls._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
            logger.info("Database connection pool created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    @classmethod
    def get_connection(cls):
        """Получение соединения из пула"""
        if cls._connection_pool is None:
            cls.initialize()
        
        try:
            return cls._connection_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise
    
    @classmethod
    def return_connection(cls, connection):
        """Возврат соединения в пул"""
        if cls._connection_pool is not None:
            cls._connection_pool.putconn(connection)
    
    @classmethod
    def close_all_connections(cls):
        """Закрытие всех соединений пула"""
        if cls._connection_pool is not None:
            cls._connection_pool.closeall()
    
    @classmethod
    def check_connection(cls):
        """Проверка соединения с БД"""
        conn = None
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True, "Database connection successful"
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"
        finally:
            if conn:
                cls.return_connection(conn)

# Инициализация при импорте
try:
    Database.initialize()
except Exception as e:
    logger.warning(f"Initial database connection failed: {e}. Will retry later.")