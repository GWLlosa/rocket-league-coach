"""Cache manager for replay files, analysis results, and player data."""

import asyncio
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sqlite3
from threading import Lock

from ..config import get_settings
from ..logging_config import get_logger, log_performance, LoggingMixin
from .models import (
    ReplayCacheEntry,
    CacheEntryType,
    CacheMetrics,
    CacheConfig,
    PlayerGameHistory,
    GameResultModel,
    PlayerAnalysisModel,
    model_to_json,
    model_from_json,
)


class CacheManager(LoggingMixin):
    """Manages caching of replay files, analysis results, and player data."""
    
    def __init__(self, cache_config: CacheConfig = None):
        self.settings = get_settings()
        self.config = cache_config or CacheConfig(
            ttl_hours=self.settings.cache_ttl_hours,
            max_size_gb=5.0,
            cleanup_interval_hours=6,
            max_entries=10000
        )
        
        # Cache directories
        self.replay_cache_dir = self.settings.replays_dir
        self.analysis_cache_dir = self.settings.analysis_cache_dir
        self.player_data_dir = self.settings.player_data_dir
        
        # Ensure directories exist
        for directory in [self.replay_cache_dir, self.analysis_cache_dir, self.player_data_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Cache database
        self.db_path = self.settings.analysis_cache_dir / "cache.db"
        self.db_lock = Lock()
        
        # In-memory cache for frequently accessed items
        self._memory_cache: Dict[str, Any] = {}
        self._cache_access_times: Dict[str, datetime] = {}
        
        # Initialize database
        self._init_database()
        
        # Start background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _init_database(self):
        """Initialize SQLite database for cache metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    file_path TEXT,
                    size_bytes INTEGER,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_history (
                    player_name TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    analysis_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(entry_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache_entries(last_accessed)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_player_analysis ON analysis_results(player_name)
            """)
            
            conn.commit()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self.cleanup_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Cache cleanup error", error=str(e))
    
    async def store_replay_file(
        self,
        replay_id: str,
        file_path: Path,
        file_size: int
    ) -> ReplayCacheEntry:
        """Store replay file in cache."""
        now = datetime.utcnow()
        entry = ReplayCacheEntry(
            replay_id=replay_id,
            file_path=file_path,
            file_size=file_size,
            download_time=now,
            last_accessed=now,
            access_count=1
        )
        
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, entry_type, file_path, size_bytes, created_at, last_accessed, access_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    replay_id,
                    CacheEntryType.REPLAY_FILE.value,
                    str(file_path),
                    file_size,
                    now.isoformat(),
                    now.isoformat(),
                    1,
                    json.dumps(entry.to_dict())
                ))
                conn.commit()
        
        self.logger.debug(
            "Stored replay file in cache",
            replay_id=replay_id,
            file_size=file_size,
            file_path=str(file_path)
        )
        
        return entry
    
    async def get_replay_file(self, replay_id: str) -> Optional[ReplayCacheEntry]:
        """Get replay file from cache."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_path, size_bytes, created_at, last_accessed, access_count, metadata
                    FROM cache_entries 
                    WHERE key = ? AND entry_type = ?
                """, (replay_id, CacheEntryType.REPLAY_FILE.value))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                file_path, size_bytes, created_at, last_accessed, access_count, metadata = row
                
                # Check if file still exists
                if not Path(file_path).exists():
                    # Remove stale entry
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (replay_id,))
                    conn.commit()
                    return None
                
                # Check TTL
                created_time = datetime.fromisoformat(created_at)
                if datetime.utcnow() - created_time > timedelta(seconds=self.config.ttl_seconds):
                    # Entry expired
                    await self._remove_cache_entry(replay_id)
                    return None
                
                # Update access time and count
                now = datetime.utcnow()
                conn.execute("""
                    UPDATE cache_entries 
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE key = ?
                """, (now.isoformat(), replay_id))
                conn.commit()
                
                # Create entry object
                entry_data = json.loads(metadata)
                entry = ReplayCacheEntry.from_dict(entry_data)
                entry.last_accessed = now
                entry.access_count = access_count + 1
                
                self.logger.debug(
                    "Retrieved replay file from cache",
                    replay_id=replay_id,
                    access_count=entry.access_count
                )
                
                return entry
    
    async def store_player_history(self, player_name: str, history: PlayerGameHistory):
        """Store player game history."""
        data_json = model_to_json(history)
        now = datetime.utcnow()
        
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO player_history (player_name, data, last_updated)
                    VALUES (?, ?, ?)
                """, (player_name, data_json, now.isoformat()))
                conn.commit()
        
        # Also cache in memory for quick access
        self._memory_cache[f"history_{player_name}"] = history
        self._cache_access_times[f"history_{player_name}"] = now
        
        self.logger.debug(
            "Stored player history",
            player=player_name,
            games_count=len(history.games)
        )
    
    async def get_player_history(self, player_name: str) -> Optional[PlayerGameHistory]:
        """Get player game history."""
        # Check memory cache first
        cache_key = f"history_{player_name}"
        if cache_key in self._memory_cache:
            self._cache_access_times[cache_key] = datetime.utcnow()
            return self._memory_cache[cache_key]
        
        # Check database
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT data, last_updated FROM player_history WHERE player_name = ?
                """, (player_name,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                data_json, last_updated = row
                
                # Check TTL
                updated_time = datetime.fromisoformat(last_updated)
                if datetime.utcnow() - updated_time > timedelta(seconds=self.config.ttl_seconds):
                    # Entry expired
                    conn.execute("DELETE FROM player_history WHERE player_name = ?", (player_name,))
                    conn.commit()
                    return None
                
                # Parse history
                history = model_from_json(PlayerGameHistory, data_json)
                
                # Cache in memory
                self._memory_cache[cache_key] = history
                self._cache_access_times[cache_key] = datetime.utcnow()
                
                return history
    
    async def store_analysis_result(self, analysis: PlayerAnalysisModel):
        """Store analysis result."""
        data_json = model_to_json(analysis)
        now = datetime.utcnow()
        
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO analysis_results 
                    (analysis_id, player_name, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    analysis.analysis_id,
                    analysis.player_name,
                    data_json,
                    analysis.created_at.isoformat(),
                    now.isoformat()
                ))
                conn.commit()
        
        # Cache in memory
        cache_key = f"analysis_{analysis.analysis_id}"
        self._memory_cache[cache_key] = analysis
        self._cache_access_times[cache_key] = now
        
        self.logger.info(
            "Stored analysis result",
            analysis_id=analysis.analysis_id,
            player=analysis.player_name,
            status=analysis.status.value
        )
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[PlayerAnalysisModel]:
        """Get analysis result by ID."""
        # Check memory cache first
        cache_key = f"analysis_{analysis_id}"
        if cache_key in self._memory_cache:
            self._cache_access_times[cache_key] = datetime.utcnow()
            return self._memory_cache[cache_key]
        
        # Check database
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT data FROM analysis_results WHERE analysis_id = ?
                """, (analysis_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                data_json = row[0]
                analysis = model_from_json(PlayerAnalysisModel, data_json)
                
                # Cache in memory
                self._memory_cache[cache_key] = analysis
                self._cache_access_times[cache_key] = datetime.utcnow()
                
                return analysis
    
    async def get_player_analyses(self, player_name: str, limit: int = 10) -> List[PlayerAnalysisModel]:
        """Get recent analyses for a player."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT data FROM analysis_results 
                    WHERE player_name = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (player_name, limit))
                
                analyses = []
                for row in cursor.fetchall():
                    data_json = row[0]
                    analysis = model_from_json(PlayerAnalysisModel, data_json)
                    analyses.append(analysis)
                
                return analyses
    
    async def _remove_cache_entry(self, key: str):
        """Remove cache entry and associated file."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                # Get file path before deletion
                cursor = conn.execute("""
                    SELECT file_path FROM cache_entries WHERE key = ?
                """, (key,))
                row = cursor.fetchone()
                
                if row:
                    file_path = Path(row[0])
                    if file_path.exists():
                        try:
                            file_path.unlink()
                        except Exception as e:
                            self.logger.warning(
                                "Failed to delete cache file",
                                file_path=str(file_path),
                                error=str(e)
                            )
                
                # Remove database entry
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
        
        # Remove from memory cache if present
        memory_keys = [k for k in self._memory_cache.keys() if key in k]
        for mem_key in memory_keys:
            self._memory_cache.pop(mem_key, None)
            self._cache_access_times.pop(mem_key, None)
    
    async def cleanup_cache(self):
        """Clean up expired and oversized cache entries."""
        with log_performance("cache_cleanup"):
            now = datetime.utcnow()
            
            # Clean up expired entries
            expired_keys = []
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT key, created_at FROM cache_entries
                    """)
                    
                    for key, created_at in cursor.fetchall():
                        created_time = datetime.fromisoformat(created_at)
                        if now - created_time > timedelta(seconds=self.config.ttl_seconds):
                            expired_keys.append(key)
            
            # Remove expired entries
            for key in expired_keys:
                await self._remove_cache_entry(key)
            
            # Clean up oversized cache
            await self._cleanup_oversized_cache()
            
            # Clean up memory cache
            self._cleanup_memory_cache()
            
            self.logger.info(
                "Cache cleanup completed",
                expired_entries=len(expired_keys),
                memory_cache_size=len(self._memory_cache)
            )
    
    async def _cleanup_oversized_cache(self):
        """Remove least recently used entries if cache is too large."""
        metrics = await self.get_cache_metrics()
        
        if metrics.total_size_bytes > self.config.max_size_bytes:
            # Get entries sorted by last access (oldest first)
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT key, size_bytes, last_accessed FROM cache_entries 
                        ORDER BY last_accessed ASC
                    """)
                    
                    current_size = metrics.total_size_bytes
                    target_size = int(self.config.max_size_bytes * 0.8)  # Remove to 80% of limit
                    
                    for key, size_bytes, last_accessed in cursor.fetchall():
                        if current_size <= target_size:
                            break
                        
                        await self._remove_cache_entry(key)
                        current_size -= size_bytes
                        
                        self.logger.debug(
                            "Removed cache entry for size",
                            key=key,
                            size_bytes=size_bytes
                        )
    
    def _cleanup_memory_cache(self):
        """Clean up memory cache of old entries."""
        now = datetime.utcnow()
        ttl = timedelta(hours=1)  # Memory cache TTL is shorter
        
        expired_keys = [
            key for key, access_time in self._cache_access_times.items()
            if now - access_time > ttl
        ]
        
        for key in expired_keys:
            self._memory_cache.pop(key, None)
            self._cache_access_times.pop(key, None)
    
    async def get_cache_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        COALESCE(SUM(size_bytes), 0) as total_size,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM cache_entries
                """)
                
                total_entries, total_size, oldest, newest = cursor.fetchone()
                
                # Calculate hit/miss rates (simplified)
                cursor = conn.execute("""
                    SELECT COALESCE(AVG(access_count), 0) FROM cache_entries
                """)
                avg_access = cursor.fetchone()[0]
                
                return CacheMetrics(
                    total_entries=total_entries or 0,
                    total_size_bytes=total_size or 0,
                    hit_rate=min(avg_access / 10.0, 1.0) if avg_access else 0.0,
                    miss_rate=1.0 - min(avg_access / 10.0, 1.0) if avg_access else 1.0,
                    eviction_count=0,  # Would need separate tracking
                    oldest_entry=datetime.fromisoformat(oldest) if oldest else None,
                    newest_entry=datetime.fromisoformat(newest) if newest else None
                )
    
    async def clear_cache(self, entry_type: Optional[CacheEntryType] = None):
        """Clear cache entries of specified type or all entries."""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                if entry_type:
                    # Clear specific type
                    cursor = conn.execute("""
                        SELECT key FROM cache_entries WHERE entry_type = ?
                    """, (entry_type.value,))
                    keys = [row[0] for row in cursor.fetchall()]
                    
                    conn.execute("""
                        DELETE FROM cache_entries WHERE entry_type = ?
                    """, (entry_type.value,))
                else:
                    # Clear all
                    cursor = conn.execute("SELECT key FROM cache_entries")
                    keys = [row[0] for row in cursor.fetchall()]
                    
                    conn.execute("DELETE FROM cache_entries")
                    conn.execute("DELETE FROM player_history")
                    conn.execute("DELETE FROM analysis_results")
                
                conn.commit()
        
        # Clean up files
        for key in keys:
            try:
                await self._remove_cache_entry(key)
            except Exception as e:
                self.logger.warning("Failed to remove cache entry", key=key, error=str(e))
        
        # Clear memory cache
        self._memory_cache.clear()
        self._cache_access_times.clear()
        
        self.logger.info(
            "Cache cleared",
            entry_type=entry_type.value if entry_type else "all",
            entries_removed=len(keys)
        )
    
    async def close(self):
        """Close cache manager and cleanup."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Cache manager closed")


# Convenience function for creating cache manager instances
def create_cache_manager() -> CacheManager:
    """Create a configured cache manager."""
    return CacheManager()
