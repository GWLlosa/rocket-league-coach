"""Cache management system for replay files and analysis results."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
import shutil
import tempfile

from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Manages caching for replay files, analysis results, and player data."""
    
    def __init__(self, base_cache_dir: Optional[Path] = None):
        """Initialize the cache manager.
        
        Args:
            base_cache_dir: Base directory for cache. If None, uses config setting.
        """
        self.settings = get_settings()
        self.base_cache_dir = base_cache_dir or self.settings.analysis_cache_dir
        
        # Cache subdirectories
        self.replays_cache = self.base_cache_dir / "replays"
        self.analysis_cache = self.base_cache_dir / "analysis" 
        self.player_cache = self.base_cache_dir / "players"
        self.metadata_cache = self.base_cache_dir / "metadata"
        
        # Database path
        self.db_path = self.base_cache_dir / "cache.db"
        
        # Initialize cache structure
        self._init_cache_structure()
        self._init_database()
    
    def _init_cache_structure(self) -> None:
        """Create cache directory structure."""
        directories = [
            self.base_cache_dir,
            self.replays_cache,
            self.analysis_cache,
            self.player_cache,
            self.metadata_cache,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info("Cache directory structure initialized", base_dir=str(self.base_cache_dir))
    
    def _init_database(self) -> None:
        """Initialize SQLite database for cache metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS replay_cache (
                    replay_id TEXT PRIMARY KEY,
                    gamertag TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    cached_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP NOT NULL,
                    game_date TIMESTAMP,
                    game_result TEXT,
                    ttl_hours INTEGER DEFAULT 24
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    cache_key TEXT PRIMARY KEY,
                    gamertag TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    result_path TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP NOT NULL,
                    ttl_hours INTEGER DEFAULT 168,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_history (
                    gamertag TEXT,
                    replay_id TEXT,
                    game_date TIMESTAMP,
                    game_result TEXT,
                    rank_tier INTEGER,
                    cached_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (gamertag, replay_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_replay_cache_gamertag ON replay_cache(gamertag)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_replay_cache_cached_at ON replay_cache(cached_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_gamertag ON analysis_cache(gamertag)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_player_history_gamertag ON player_history(gamertag)")
            
            conn.commit()
            
        logger.info("Cache database initialized", db_path=str(self.db_path))
    
    def _generate_cache_key(self, *args: Any) -> str:
        """Generate a unique cache key from arguments.
        
        Args:
            *args: Arguments to hash for the cache key
            
        Returns:
            Hexadecimal cache key string
        """
        content = "_".join(str(arg) for arg in args)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def cache_replay_file(
        self, 
        replay_id: str, 
        gamertag: str,
        file_content: bytes,
        game_date: Optional[datetime] = None,
        game_result: Optional[str] = None,
        ttl_hours: int = 24
    ) -> Path:
        """Cache a replay file.
        
        Args:
            replay_id: Unique replay identifier
            gamertag: Player gamertag
            file_content: Binary replay file content
            game_date: When the game was played
            game_result: 'win' or 'loss'
            ttl_hours: Time to live in hours
            
        Returns:
            Path to the cached file
        """
        # Create safe filename
        safe_filename = f"{replay_id}_{gamertag.replace(' ', '_')}.replay"
        file_path = self.replays_cache / safe_filename
        
        # Write file content
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        file_size = len(file_content)
        now = datetime.now()
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO replay_cache 
                (replay_id, gamertag, file_path, file_size, cached_at, last_accessed, game_date, game_result, ttl_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                replay_id, gamertag, str(file_path), file_size, 
                now, now, game_date, game_result, ttl_hours
            ))
            conn.commit()
        
        logger.info(
            "Replay file cached",
            replay_id=replay_id,
            gamertag=gamertag,
            file_size=file_size,
            path=str(file_path)
        )
        
        return file_path
    
    def get_cached_replay(self, replay_id: str, gamertag: str) -> Optional[Path]:
        """Get a cached replay file if it exists and is valid.
        
        Args:
            replay_id: Unique replay identifier
            gamertag: Player gamertag
            
        Returns:
            Path to cached file or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT file_path, cached_at, ttl_hours 
                FROM replay_cache 
                WHERE replay_id = ? AND gamertag = ?
            """, (replay_id, gamertag))
            
            row = cursor.fetchone()
            
        if not row:
            return None
        
        file_path = Path(row['file_path'])
        cached_at = datetime.fromisoformat(row['cached_at'])
        ttl_hours = row['ttl_hours']
        
        # Check if file exists and is not expired
        if not file_path.exists():
            self._remove_replay_cache_entry(replay_id, gamertag)
            return None
        
        if datetime.now() - cached_at > timedelta(hours=ttl_hours):
            self._remove_replay_cache_entry(replay_id, gamertag)
            return None
        
        # Update last accessed time
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE replay_cache 
                SET last_accessed = ? 
                WHERE replay_id = ? AND gamertag = ?
            """, (datetime.now(), replay_id, gamertag))
            conn.commit()
        
        return file_path
    
    def cache_analysis_result(
        self,
        gamertag: str,
        analysis_type: str,
        result_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: int = 168  # 1 week default
    ) -> str:
        """Cache analysis results.
        
        Args:
            gamertag: Player gamertag
            analysis_type: Type of analysis (e.g., 'win_loss_correlation', 'rule_based')
            result_data: Analysis result data
            metadata: Optional metadata about the analysis
            ttl_hours: Time to live in hours
            
        Returns:
            Cache key for the stored result
        """
        cache_key = self._generate_cache_key(gamertag, analysis_type, time.time())
        result_filename = f"{cache_key}.json"
        result_path = self.analysis_cache / result_filename
        
        # Save result data
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        now = datetime.now()
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_cache
                (cache_key, gamertag, analysis_type, result_path, cached_at, last_accessed, ttl_hours, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key, gamertag, analysis_type, str(result_path),
                now, now, ttl_hours, metadata_json
            ))
            conn.commit()
        
        logger.info(
            "Analysis result cached",
            cache_key=cache_key,
            gamertag=gamertag,
            analysis_type=analysis_type,
            path=str(result_path)
        )
        
        return cache_key
    
    def get_cached_analysis(
        self, 
        gamertag: str, 
        analysis_type: str,
        max_age_hours: Optional[int] = None
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Get cached analysis results.
        
        Args:
            gamertag: Player gamertag
            analysis_type: Type of analysis
            max_age_hours: Maximum age in hours (overrides TTL)
            
        Returns:
            Tuple of (cache_key, result_data) or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT cache_key, result_path, cached_at, ttl_hours
                FROM analysis_cache 
                WHERE gamertag = ? AND analysis_type = ?
                ORDER BY cached_at DESC
                LIMIT 1
            """, (gamertag, analysis_type))
            
            row = cursor.fetchone()
        
        if not row:
            return None
        
        cache_key = row['cache_key']
        result_path = Path(row['result_path'])
        cached_at = datetime.fromisoformat(row['cached_at'])
        ttl_hours = row['ttl_hours']
        
        # Use max_age_hours if provided, otherwise use TTL
        max_age = max_age_hours or ttl_hours
        
        # Check if file exists and is not expired
        if not result_path.exists():
            self._remove_analysis_cache_entry(cache_key)
            return None
        
        if datetime.now() - cached_at > timedelta(hours=max_age):
            self._remove_analysis_cache_entry(cache_key)
            return None
        
        # Load and return result data
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load cached analysis", cache_key=cache_key, error=str(e))
            self._remove_analysis_cache_entry(cache_key)
            return None
        
        # Update last accessed time
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE analysis_cache 
                SET last_accessed = ? 
                WHERE cache_key = ?
            """, (datetime.now(), cache_key))
            conn.commit()
        
        return cache_key, result_data
    
    def store_player_game_history(
        self,
        gamertag: str,
        replay_id: str,
        game_date: datetime,
        game_result: str,
        rank_tier: Optional[int] = None
    ) -> None:
        """Store player game history for tracking win/loss patterns.
        
        Args:
            gamertag: Player gamertag
            replay_id: Unique replay identifier
            game_date: When the game was played
            game_result: 'win' or 'loss'
            rank_tier: Player's rank tier
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO player_history
                (gamertag, replay_id, game_date, game_result, rank_tier, cached_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                gamertag, replay_id, game_date, game_result, 
                rank_tier, datetime.now()
            ))
            conn.commit()
        
        logger.debug(
            "Player game history stored",
            gamertag=gamertag,
            replay_id=replay_id,
            result=game_result
        )
    
    def get_player_game_history(
        self,
        gamertag: str,
        limit: Optional[int] = None,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get player game history.
        
        Args:
            gamertag: Player gamertag
            limit: Maximum number of games to return
            days_back: Only return games from this many days back
            
        Returns:
            List of game history dictionaries
        """
        query = """
            SELECT replay_id, game_date, game_result, rank_tier
            FROM player_history 
            WHERE gamertag = ?
        """
        params = [gamertag]
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            query += " AND game_date >= ?"
            params.append(cutoff_date)
        
        query += " ORDER BY game_date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def cleanup_expired_cache(self) -> Dict[str, int]:
        """Remove expired cache entries and files.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {"replays_removed": 0, "analysis_removed": 0, "files_removed": 0}
        now = datetime.now()
        
        # Cleanup expired replay cache
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find expired replays
            cursor = conn.execute("""
                SELECT replay_id, gamertag, file_path
                FROM replay_cache 
                WHERE datetime(cached_at, '+' || ttl_hours || ' hours') < ?
            """, (now,))
            
            expired_replays = cursor.fetchall()
            
            for row in expired_replays:
                file_path = Path(row['file_path'])
                if file_path.exists():
                    file_path.unlink()
                    stats["files_removed"] += 1
                
                stats["replays_removed"] += 1
            
            # Remove expired replay cache entries
            conn.execute("""
                DELETE FROM replay_cache 
                WHERE datetime(cached_at, '+' || ttl_hours || ' hours') < ?
            """, (now,))
            
            # Find expired analysis cache
            cursor = conn.execute("""
                SELECT cache_key, result_path
                FROM analysis_cache 
                WHERE datetime(cached_at, '+' || ttl_hours || ' hours') < ?
            """, (now,))
            
            expired_analysis = cursor.fetchall()
            
            for row in expired_analysis:
                result_path = Path(row['result_path'])
                if result_path.exists():
                    result_path.unlink()
                    stats["files_removed"] += 1
                
                stats["analysis_removed"] += 1
            
            # Remove expired analysis cache entries
            conn.execute("""
                DELETE FROM analysis_cache 
                WHERE datetime(cached_at, '+' || ttl_hours || ' hours') < ?
            """, (now,))
            
            conn.commit()
        
        logger.info("Cache cleanup completed", **stats)
        return stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count, SUM(file_size) as total_size FROM replay_cache")
            replay_stats = cursor.fetchone()
            
            cursor = conn.execute("SELECT COUNT(*) as count FROM analysis_cache")
            analysis_stats = cursor.fetchone()
            
            cursor = conn.execute("SELECT COUNT(DISTINCT gamertag) as count FROM player_history")
            player_stats = cursor.fetchone()
        
        # Calculate directory sizes
        def get_dir_size(directory: Path) -> int:
            """Get total size of directory in bytes."""
            return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
        
        return {
            "replay_cache": {
                "entries": replay_stats[0] or 0,
                "total_file_size": replay_stats[1] or 0,
                "directory_size": get_dir_size(self.replays_cache),
            },
            "analysis_cache": {
                "entries": analysis_stats[0] or 0,
                "directory_size": get_dir_size(self.analysis_cache),
            },
            "player_history": {
                "unique_players": player_stats[0] or 0,
            },
            "total_cache_size": get_dir_size(self.base_cache_dir),
        }
    
    def _remove_replay_cache_entry(self, replay_id: str, gamertag: str) -> None:
        """Remove a replay cache entry and its file."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path FROM replay_cache 
                WHERE replay_id = ? AND gamertag = ?
            """, (replay_id, gamertag))
            
            row = cursor.fetchone()
            if row:
                file_path = Path(row[0])
                if file_path.exists():
                    file_path.unlink()
            
            conn.execute("""
                DELETE FROM replay_cache 
                WHERE replay_id = ? AND gamertag = ?
            """, (replay_id, gamertag))
            conn.commit()
    
    def _remove_analysis_cache_entry(self, cache_key: str) -> None:
        """Remove an analysis cache entry and its file."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT result_path FROM analysis_cache 
                WHERE cache_key = ?
            """, (cache_key,))
            
            row = cursor.fetchone()
            if row:
                result_path = Path(row[0])
                if result_path.exists():
                    result_path.unlink()
            
            conn.execute("DELETE FROM analysis_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
    
    def clear_cache(self, confirm: bool = False) -> None:
        """Clear all cache data. USE WITH CAUTION!
        
        Args:
            confirm: Must be True to actually clear the cache
        """
        if not confirm:
            raise ValueError("Must set confirm=True to clear cache")
        
        # Remove all cached files
        if self.replays_cache.exists():
            shutil.rmtree(self.replays_cache)
        if self.analysis_cache.exists():
            shutil.rmtree(self.analysis_cache)
        if self.player_cache.exists():
            shutil.rmtree(self.player_cache)
        if self.metadata_cache.exists():
            shutil.rmtree(self.metadata_cache)
        
        # Clear database
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Reinitialize
        self._init_cache_structure()
        self._init_database()
        
        logger.warning("All cache data cleared")


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager
