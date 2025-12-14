"""
Data caching system for HVSR Pro
=================================

Implements efficient caching for loaded seismic data to avoid redundant file I/O.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import pickle
from datetime import datetime, timedelta


class DataCache:
    """
    LRU cache for seismic data with memory management.
    
    Features:
    - File hash-based cache keys
    - Automatic memory limit enforcement
    - Cache expiration
    - Persistence to disk
    """
    
    def __init__(self, max_memory_mb: float = 1000, max_age_hours: float = 24):
        """
        Initialize data cache.
        
        Args:
            max_memory_mb: Maximum memory usage in megabytes
            max_age_hours: Maximum age of cached items in hours
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._max_age = timedelta(hours=max_age_hours)
        self._current_memory = 0
    
    def _compute_file_hash(self, filepath: str) -> str:
        """
        Compute hash of file for cache key.
        
        Args:
            filepath: Path to file
            
        Returns:
            SHA256 hash of file contents
        """
        sha256_hash = hashlib.sha256()
        path = Path(filepath)
        
        # For large files, only hash first and last MB
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10 MB
            with open(filepath, 'rb') as f:
                # Hash first MB
                sha256_hash.update(f.read(1024 * 1024))
                # Seek to last MB
                f.seek(-1024 * 1024, 2)
                sha256_hash.update(f.read(1024 * 1024))
        else:
            # Hash entire file
            with open(filepath, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        
        # Include modification time in hash
        mtime = path.stat().st_mtime
        sha256_hash.update(str(mtime).encode())
        
        return sha256_hash.hexdigest()
    
    def get(self, filepath: str) -> Optional[Any]:
        """
        Retrieve data from cache.
        
        Args:
            filepath: Path to data file
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            cache_key = self._compute_file_hash(filepath)
        except FileNotFoundError:
            return None
        
        if cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        
        # Check if expired
        age = datetime.now() - entry['timestamp']
        if age > self._max_age:
            self.remove(filepath)
            return None
        
        # Update access time
        entry['last_accessed'] = datetime.now()
        entry['access_count'] += 1
        
        return entry['data']
    
    def put(self, filepath: str, data: Any) -> None:
        """
        Store data in cache.
        
        Args:
            filepath: Path to data file
            data: Data to cache
        """
        try:
            cache_key = self._compute_file_hash(filepath)
        except FileNotFoundError:
            return
        
        # Estimate memory usage
        data_size = self._estimate_size(data)
        
        # Ensure space available
        while self._current_memory + data_size > self._max_memory_bytes:
            if not self._evict_lru():
                break  # Cache is empty
        
        # Store in cache
        self._cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now(),
            'last_accessed': datetime.now(),
            'access_count': 0,
            'size': data_size,
            'filepath': filepath
        }
        
        self._current_memory += data_size
    
    def remove(self, filepath: str) -> None:
        """
        Remove item from cache.
        
        Args:
            filepath: Path to data file
        """
        try:
            cache_key = self._compute_file_hash(filepath)
        except FileNotFoundError:
            return
        
        if cache_key in self._cache:
            entry = self._cache.pop(cache_key)
            self._current_memory -= entry['size']
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._current_memory = 0
    
    def _evict_lru(self) -> bool:
        """
        Evict least recently used item.
        
        Returns:
            True if item was evicted, False if cache is empty
        """
        if not self._cache:
            return False
        
        # Find LRU item
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]['last_accessed']
        )
        
        # Remove it
        entry = self._cache.pop(lru_key)
        self._current_memory -= entry['size']
        
        return True
    
    def _estimate_size(self, data: Any) -> int:
        """
        Estimate memory usage of data.
        
        Args:
            data: Data object
            
        Returns:
            Estimated size in bytes
        """
        try:
            return len(pickle.dumps(data))
        except Exception:
            # Fallback: rough estimate
            return 1024 * 1024  # 1 MB default
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_accesses = sum(e['access_count'] for e in self._cache.values())
        
        return {
            'num_items': len(self._cache),
            'memory_used_mb': self._current_memory / (1024 * 1024),
            'memory_limit_mb': self._max_memory_bytes / (1024 * 1024),
            'total_accesses': total_accesses,
            'files_cached': [e['filepath'] for e in self._cache.values()]
        }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (f"DataCache(items={stats['num_items']}, "
                f"memory={stats['memory_used_mb']:.1f}/{stats['memory_limit_mb']:.1f} MB)")
