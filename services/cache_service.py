"""
Cache Service - Redis operations
Save as: backend/services/cache_service.py
"""

import redis
import json
from typing import Optional, Any
import os


class CacheService:
    """Service for caching operations using Redis"""
    
    def __init__(self):
        self.redis_client = self._init_redis()
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=False,
                socket_connect_timeout=5
            )
            
            client.ping()
            print("✅ Redis connected")
            return client
            
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")
            return None
    
    def set(self, key: str, value: Any, expiry: int = 3600) -> bool:
        """Set cache value with expiry"""
        try:
            if self.redis_client:
                serialized = json.dumps(value)
                self.redis_client.setex(key, expiry, serialized)
                return True
            return False
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                
                if data:
                    return json.loads(data)
            
            return None
            
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete cache key"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
                return True
            return False
            
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            return False
            
        except Exception as e:
            return False