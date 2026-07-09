import logging
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Connect to Redis
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_timeout=5
    )
except Exception as e:
    logger.error(f"Failed to create Redis connection: {e}")
    redis_client = None

class SeatLockService:
    def __init__(self):
        self.client = redis_client

    def acquire_lock(self, seat_id: int, user_id: int, expire_seconds: int = 300) -> bool:
        """
        Acquires a lock for a seat using SET key value NX PX.
        Returns True if the lock was acquired, False otherwise.
        """
        if not self.client:
            logger.warning("Redis client is not available. Falling back to lock bypass.")
            return True # In test environments without Redis, we allow it.
        
        lock_key = f"lock:seat:{seat_id}"
        # Set key to user_id, NX=True (set if not exists), EX=expire_seconds (expiry time)
        try:
            success = self.client.set(lock_key, str(user_id), ex=expire_seconds, nx=True)
            if success:
                logger.info(f"Lock acquired for seat {seat_id} by user {user_id}")
                return True
            else:
                logger.warning(f"Failed to acquire lock for seat {seat_id}. Seat already locked.")
                return False
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error while locking seat: {e}")
            return True # Fallback for demo/robustness if Redis goes down temporarily
        except Exception as e:
            logger.error(f"Error locking seat {seat_id}: {e}")
            return False

    def release_lock(self, seat_id: int, user_id: int) -> bool:
        """
        Releases a seat lock only if it belongs to the requesting user.
        Uses a Lua script for atomic verification and deletion.
        """
        if not self.client:
            return True
        
        lock_key = f"lock:seat:{seat_id}"
        
        # Lua script to check if the lock owner matches user_id before releasing
        lua_release = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = self.client.eval(lua_release, 1, lock_key, str(user_id))
            if result == 1:
                logger.info(f"Lock released for seat {seat_id} by user {user_id}")
                return True
            else:
                logger.warning(f"Attempted to release lock for seat {seat_id} by user {user_id}, but lock does not exist or belongs to someone else.")
                return False
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error while releasing seat: {e}")
            return True
        except Exception as e:
            logger.error(f"Error releasing lock for seat {seat_id}: {e}")
            return False

    def is_locked(self, seat_id: int) -> bool:
        """Checks if a seat is locked."""
        if not self.client:
            return False
        lock_key = f"lock:seat:{seat_id}"
        try:
            return self.client.exists(lock_key) > 0
        except Exception:
            return False

seat_lock_service = SeatLockService()
