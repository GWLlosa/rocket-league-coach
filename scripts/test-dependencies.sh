#!/bin/bash
# Test script to verify all dependencies are installed correctly

echo "Testing Python dependencies..."
echo "=============================="

# Test basic imports
echo -n "Testing numpy... "
python -c "import numpy; print(f'OK (version {numpy.__version__})')" 2>/dev/null || echo "FAILED"

echo -n "Testing pandas... "
python -c "import pandas; print(f'OK (version {pandas.__version__})')" 2>/dev/null || echo "FAILED"

echo -n "Testing scipy... "
python -c "import scipy; print(f'OK (version {scipy.__version__})')" 2>/dev/null || echo "FAILED"

echo -n "Testing carball... "
python -c "import carball; print('OK')" 2>/dev/null || echo "FAILED"

echo -n "Testing aiofiles... "
python -c "import aiofiles; print('OK')" 2>/dev/null || echo "FAILED"

echo -n "Testing fastapi... "
python -c "import fastapi; print('OK')" 2>/dev/null || echo "FAILED"

echo -n "Testing requests... "
python -c "import requests; print('OK')" 2>/dev/null || echo "FAILED"

echo -n "Testing rich... "
python -c "import rich; print('OK')" 2>/dev/null || echo "FAILED"

echo ""
echo "Testing application imports..."
echo "=============================="

echo -n "Testing config... "
python -c "from src.config import get_settings; print('OK')" 2>/dev/null || echo "FAILED"

echo -n "Testing API health... "
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "OK" || echo "FAILED (API not running)"

echo ""
echo "Test complete!"
