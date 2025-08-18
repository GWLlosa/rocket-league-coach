# Docker Build Notes

## Expected Build Output

When building the Rocket League Coach Docker container, you will see various output messages. This document helps you understand what's normal and what might be a problem.

## Harmless Warnings (Can Be Ignored)

### debconf Warnings

You will likely see red text like this during the build:

```
debconf: unable to initialize frontend: Dialog
debconf: (TERM is not set, so the dialog frontend is not usable.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: falling back to frontend: Teletype
```

**This is completely normal and harmless.** These warnings occur because:
- Docker builds run in a non-interactive environment
- The Debian package manager (apt) is trying to use interactive prompts
- It automatically falls back to non-interactive mode
- The packages install successfully despite these warnings

### pip Root User Warnings

You will see warnings in red text like:

```
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. 
It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
```

**This is normal in Docker builds and can be ignored.** Here's why:
- During the build phase, we must run as root to install system packages
- The Dockerfile switches to a non-root user (`app`) after installation
- Docker containers are isolated environments, so the typical concerns about running pip as root don't apply
- This is standard practice for Docker container builds

### Carball Import Warning

When importing carball, you might see:

```
Not importing functions due to missing packages: No module named 'boxcars_py'
```

**This is also normal.** Carball has optional dependencies that we don't need for basic replay analysis.

## Actual Errors to Watch For

These would indicate real problems:

### Build Failures

```
ERROR: Service 'rocket-league-coach' failed to build
The command '/bin/sh -c pip install...' returned a non-zero code: 1
```

If you see this, the build actually failed and needs troubleshooting.

### Missing Dependencies

```
ERROR: Could not find a version that satisfies the requirement...
```

This means a Python package couldn't be installed.

## Build Time Expectations

- **First build**: 5-10 minutes (downloading all dependencies)
- **Subsequent builds**: 1-3 minutes (using cache)
- **No-cache build**: 5-10 minutes

## Verifying Successful Build

After the build completes, verify success with:

```bash
# Check if container is running
docker-compose -f docker-compose.prod.yml ps

# Test dependencies
docker-compose -f docker-compose.prod.yml exec rocket-league-coach bash /app/scripts/test-dependencies.sh

# Check health endpoint
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "service": "rocket-league-coach",
  "version": "1.0.0",
  "environment": "production"
}
```

## Summary of Harmless Red Text

During the build, you can safely ignore these red/warning messages:
1. `debconf: unable to initialize frontend` - Normal for non-interactive builds
2. `WARNING: Running pip as the 'root' user` - Normal for Docker builds
3. `Not importing functions due to missing packages: No module named 'boxcars_py'` - Optional dependency

The build is only failing if you see:
- `ERROR:` messages
- `returned a non-zero code`
- The build stops and exits

## Troubleshooting Build Issues

### Clean Rebuild

If you encounter issues, try a clean rebuild:

```bash
# Stop and remove containers
docker-compose -f docker-compose.prod.yml down

# Remove old images and cache
docker system prune -af

# Rebuild without cache
docker-compose -f docker-compose.prod.yml build --no-cache

# Start fresh
docker-compose -f docker-compose.prod.yml up -d
```

### Check Docker Resources

```bash
# Ensure Docker has enough disk space
df -h /var/lib/docker

# Check Docker memory limits
docker system info | grep -i memory
```

Minimum recommended:
- Disk space: 10GB free
- Memory: 4GB available to Docker

## Build Optimization Tips

1. **Use BuildKit** for faster builds:
   ```bash
   DOCKER_BUILDKIT=1 docker-compose -f docker-compose.prod.yml build
   ```

2. **Leverage cache** by not changing requirements.txt unnecessarily

3. **Use .dockerignore** to exclude unnecessary files (already configured)

## Dependencies Installation Order

The Dockerfile installs dependencies in a specific order to avoid conflicts:

1. System packages (gcc, g++, gfortran) - needed for scipy
2. Python build tools (pip, wheel, setuptools)
3. NumPy - must be installed before scipy
4. SciPy - requires NumPy to be present
5. Other requirements from requirements.txt
6. Carball - installed with --no-deps to avoid version conflicts

This order is critical for successful builds.

## Why We Use Root During Build

The Dockerfile follows Docker best practices:
1. **Build phase** (as root): Install system packages and Python dependencies
2. **Runtime phase** (as non-root user `app`): Run the application

This is why pip warnings about running as root are expected and safe during the build phase.
