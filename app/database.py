"""
Database connection module using async MongoDB
"""
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import sys
from pymongo.errors import ConfigurationError
import logging

load_dotenv()

class DatabaseManager:
    _instance = None
    
    def __init__(self):
        self.client = None
        self.db = None
    
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize()
        return cls._instance
    
    async def initialize(self):
        try:
            MONGO_URL = os.getenv("MONGO_URL")
            if not MONGO_URL:
                raise ConfigurationError("MONGO_URL not found in environment variables")
            
            self.client = AsyncIOMotorClient(
                MONGO_URL,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                serverSelectionTimeoutMS=30000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client.get_database("financeiro_db")
            logging.info("✅ MongoDB connection established successfully!")
            
        except Exception as e:
            logging.error(f"❌ MongoDB connection error: {e}")
            sys.exit(1)
    
    async def get_users_collection(self):
        return self.db.users
    
    async def get_projects_collection(self):
        return self.db.projects
    
    async def get_notes_collection(self):
        return self.db.notes

# Initialize database connection
async def init_db():
    return await DatabaseManager.get_instance()

# Helper functions to get collections
async def get_users_collection():
    db_manager = await DatabaseManager.get_instance()
    return await db_manager.get_users_collection()

async def get_projects_collection():
    db_manager = await DatabaseManager.get_instance()
    return await db_manager.get_projects_collection()

async def get_notes_collection():
    db_manager = await DatabaseManager.get_instance()
    return await db_manager.get_notes_collection()
