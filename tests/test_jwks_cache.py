"""
Tests for JWKS cache functionality.

Verifies cache operations, TTL behavior, and cache management utilities.
"""

import pytest
from app.jwt_utils import _jwks_cache, clear_jwks_cache, get_cache_info


def test_jwks_cache_set_and_get():
    """Test basic cache set and get operations."""
    # Clear cache first
    _jwks_cache.clear()
    
    # Set cache value
    _jwks_cache['jwks'] = {'keys': []}
    
    # Verify cache contains the key
    assert 'jwks' in _jwks_cache
    assert _jwks_cache['jwks'] == {'keys': []}


def test_jwks_cache_clear():
    """Test cache clearing functionality."""
    # Set cache value
    _jwks_cache['jwks'] = {'keys': []}
    assert 'jwks' in _jwks_cache
    
    # Clear cache
    _jwks_cache.clear()
    
    # Verify cache is empty
    assert 'jwks' not in _jwks_cache


def test_clear_jwks_cache_utility():
    """Test the clear_jwks_cache utility function."""
    # Set cache value
    _jwks_cache['jwks'] = {'keys': []}
    assert 'jwks' in _jwks_cache
    
    # Clear using utility function
    clear_jwks_cache()
    
    # Verify cache is empty
    assert 'jwks' not in _jwks_cache


def test_get_cache_info():
    """Test cache info retrieval."""
    # Clear cache first
    _jwks_cache.clear()
    
    # Get cache info
    info = get_cache_info()
    
    # Verify info structure
    assert 'maxsize' in info
    assert 'ttl' in info
    assert 'current_size' in info
    assert 'keys' in info
    
    # Verify empty cache
    assert info['current_size'] == 0
    assert info['keys'] == []
    
    # Add item to cache
    _jwks_cache['jwks'] = {'keys': []}
    
    # Get updated info
    info = get_cache_info()
    assert info['current_size'] == 1
    assert 'jwks' in info['keys']


def test_cache_maxsize():
    """Test cache respects maxsize limit."""
    # Clear cache first
    _jwks_cache.clear()
    
    # Get cache info to check maxsize
    info = get_cache_info()
    maxsize = info['maxsize']
    
    # Fill cache beyond maxsize
    for i in range(maxsize + 5):
        _jwks_cache[f'key_{i}'] = {'data': i}
    
    # Verify cache size doesn't exceed maxsize
    assert len(_jwks_cache) <= maxsize


def test_cache_ttl_configuration():
    """Test cache TTL is properly configured."""
    info = get_cache_info()
    
    # Verify TTL is set (should be > 0)
    assert info['ttl'] > 0
    
    # Verify maxsize is set
    assert info['maxsize'] > 0
