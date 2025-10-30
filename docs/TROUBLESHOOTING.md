# License Compliance Checker - Troubleshooting Guide

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Scanning Issues](#scanning-issues)
3. [License Resolution Issues](#license-resolution-issues)
4. [Policy Issues](#policy-issues)
5. [API and Server Issues](#api-and-server-issues)
6. [Dashboard Issues](#dashboard-issues)
7. [Docker Issues](#docker-issues)
8. [Performance Issues](#performance-issues)
9. [Database Issues](#database-issues)
10. [Getting Help](#getting-help)

---

## Installation Issues

### pip install fails with "No matching distribution found"

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement lcc
```

**Causes & Solutions**:

1. **Wrong package name**: The package is `license-compliance-checker`, not `lcc`
   ```bash
   # Correct
   pip install license-compliance-checker

   # Incorrect
   pip install lcc
   ```

2. **Python version too old**: LCC requires Python 3.9+
   ```bash
   # Check Python version
   python --version

   # Upgrade Python if needed
   # On macOS with Homebrew:
   brew install python@3.11

   # On Ubuntu:
   sudo apt install python3.11
   ```

3. **pip is outdated**: Upgrade pip
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

### ModuleNotFoundError after installation

**Symptoms**:
```
ModuleNotFoundError: No module named 'lcc'
```

**Causes & Solutions**:

1. **Multiple Python environments**: Installed in wrong environment
   ```bash
   # Check which Python is being used
   which python
   which pip

   # Use pip with the same Python
   python -m pip install license-compliance-checker

   # Or use venv
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install license-compliance-checker
   ```

2. **Editable install issue**: Reinstall
   ```bash
   pip uninstall license-compliance-checker
   pip install license-compliance-checker
   ```

### "Command 'lcc' not found"

**Symptoms**:
```bash
$ lcc --version
bash: lcc: command not found
```

**Causes & Solutions**:

1. **PATH not configured**: Add pip bin directory to PATH
   ```bash
   # Find where pip installs binaries
   python -m site --user-base

   # Add to PATH (in ~/.bashrc or ~/.zshrc)
   export PATH="$HOME/.local/bin:$PATH"

   # Reload shell
   source ~/.bashrc
   ```

2. **Use as module**: Run as Python module instead
   ```bash
   python -m lcc.cli.main --version
   ```

---

## Scanning Issues

### "No detectors found components"

**Symptoms**:
```
INFO: Scan completed in 0.1s
INFO: Found 0 components
```

**Causes & Solutions**:

1. **Wrong directory**: Not in project root
   ```bash
   # Check directory contents
   ls -la

   # Look for package manifests
   find . -name "package.json" -o -name "requirements.txt" -o -name "go.mod"

   # Scan correct directory
   lcc scan /path/to/project/root
   ```

2. **Unsupported language**: LCC supports Python, JavaScript, Go, Rust, Java, Ruby, .NET
   ```bash
   # Check if your language is supported
   lcc --help
   ```

3. **Manifest file in subdirectory**: Use recursive option
   ```bash
   lcc scan . --recursive
   ```

### Scan is very slow

**Symptoms**:
- Scan takes > 5 minutes
- High CPU or memory usage

**Causes & Solutions**:

1. **Large project with many files**: Exclude unnecessary directories
   ```bash
   lcc scan . --exclude "node_modules" --exclude "vendor" --exclude ".git"
   ```

2. **GitHub API rate limiting**: Use GitHub token
   ```bash
   # Set GitHub token
   export GITHUB_TOKEN="ghp_your_token_here"

   # Or in config.yaml
   github:
     token: ghp_your_token_here
   ```

3. **Network issues**: Use cache
   ```bash
   # Enable cache (default)
   lcc scan . --cache-ttl 86400  # 24 hours
   ```

4. **Too many resolvers**: Disable unused resolvers
   ```yaml
   # config.yaml
   resolvers:
     - registry  # Fast
     - clearlydefined  # Medium
     # - github  # Slow, disable if not needed
   ```

### "Permission denied" when scanning

**Symptoms**:
```
ERROR: Permission denied: /path/to/file
```

**Causes & Solutions**:

1. **Insufficient file permissions**: Run with appropriate permissions
   ```bash
   # Check permissions
   ls -la /path/to/file

   # Fix permissions
   chmod +r /path/to/file

   # Or run as root (not recommended)
   sudo lcc scan /path
   ```

2. **SELinux blocking access**: Temporarily disable or configure
   ```bash
   # Check SELinux status
   getenforce

   # Temporarily disable (for testing only)
   sudo setenforce 0
   ```

---

## License Resolution Issues

### Many "UNKNOWN" licenses

**Symptoms**:
- Report shows many components with "UNKNOWN" license
- Policy violations due to unknown licenses

**Causes & Solutions**:

1. **Package not in registries**: Add custom metadata
   ```yaml
   # overrides.yaml
   overrides:
     my-package:
       license: MIT
       reason: "Verified from upstream GitHub repo"
   ```

2. **Network issues**: Check connectivity
   ```bash
   # Test registry access
   curl https://pypi.org/pypi/requests/json
   curl https://registry.npmjs.org/express

   # Test GitHub API
   curl https://api.github.com/rate_limit
   ```

3. **GitHub rate limiting**: Set GitHub token
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```

4. **Custom packages**: Use local resolution
   ```bash
   # Scan with local LICENSE files
   lcc scan . --resolvers filesystem
   ```

### Incorrect license detected

**Symptoms**:
- License doesn't match upstream source
- Dual-license not properly detected

**Causes & Solutions**:

1. **Registry metadata is wrong**: Use override
   ```yaml
   # overrides.yaml
   overrides:
     package-name:
       license: "MIT OR Apache-2.0"
       reason: "Registry metadata incorrect, verified from source"
   ```

2. **SPDX expression parsing issue**: Simplify or override
   ```yaml
   overrides:
     complex-package:
       license: Apache-2.0  # Choose preferred license
   ```

3. **Custom/proprietary license**: Add to policy
   ```yaml
   # policy.yaml
   contexts:
     production:
       allow:
         - Proprietary-CompanyName
   ```

### AI/ML model license not detected

**Symptoms**:
- Hugging Face models show "UNKNOWN"
- Dataset licenses not recognized

**Causes & Solutions**:

1. **Missing model card**: Add metadata
   ```yaml
   overrides:
     bert-base-uncased:
       license: Apache-2.0
       type: huggingface
   ```

2. **Custom AI license**: Add to policy
   ```yaml
   contexts:
     research:
       allow:
         - llama-2
         - openrail-m
         - deepmind-gemma
   ```

3. **Hugging Face API issues**: Check connectivity
   ```bash
   # Test Hugging Face API
   curl https://huggingface.co/api/models/bert-base-uncased
   ```

---

## Policy Issues

### Policy file not found

**Symptoms**:
```
ERROR: Policy 'my-policy' not found
```

**Causes & Solutions**:

1. **Wrong policy directory**: Check policy location
   ```bash
   # Default location
   ls ~/.lcc/policies/

   # Check config
   lcc config show | grep policy_dir

   # Set custom location
   export LCC_POLICY_DIR=/path/to/policies
   ```

2. **Wrong file extension**: Use `.yaml` or `.yml`
   ```bash
   # Correct
   my-policy.yaml
   my-policy.yml

   # Incorrect
   my-policy.json
   my-policy.txt
   ```

3. **File permissions**: Check read permissions
   ```bash
   ls -la ~/.lcc/policies/
   chmod +r ~/.lcc/policies/my-policy.yaml
   ```

### Policy validation fails

**Symptoms**:
```
ERROR: Invalid policy: ...
```

**Causes & Solutions**:

1. **YAML syntax error**: Check YAML formatting
   ```bash
   # Validate YAML
   lcc policy validate my-policy

   # Check for tabs (YAML requires spaces)
   cat -A my-policy.yaml | grep "\t"
   ```

2. **Missing required fields**: Add required fields
   ```yaml
   name: my-policy
   version: "1.0"
   contexts:
     production:
       allow: []
       deny: []
       review: []
   ```

3. **Invalid license identifier**: Check SPDX identifiers
   ```yaml
   # Correct
   allow:
     - Apache-2.0
     - GPL-3.0

   # Incorrect
   allow:
     - Apache 2.0  # No spaces
     - GPLv3       # Use official identifier
   ```

### Unexpected policy results

**Symptoms**:
- Allowed licenses are flagged
- Denied licenses pass

**Causes & Solutions**:

1. **Wrong context**: Specify correct context
   ```bash
   # Check which context is being used
   lcc scan . --policy my-policy --context production --dry-run
   ```

2. **Wildcard not matching**: Check pattern
   ```yaml
   # Specific
   allow:
     - GPL-2.0
     - GPL-3.0

   # Wildcard (matches both)
   allow:
     - GPL-*
   ```

3. **Dual-license preference**: Check preference setting
   ```yaml
   contexts:
     production:
       dual_license_preference: most_permissive  # or avoid_copyleft
   ```

---

## API and Server Issues

### "Connection refused" when accessing API

**Symptoms**:
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Causes & Solutions**:

1. **Server not running**: Start server
   ```bash
   # Check if server is running
   ps aux | grep "lcc server"

   # Start server
   lcc server

   # Or with Docker
   docker-compose up -d
   ```

2. **Wrong port**: Check configured port
   ```bash
   # Default is 8000
   curl http://localhost:8000/health

   # If using custom port
   lcc server --port 8080
   curl http://localhost:8080/health
   ```

3. **Firewall blocking**: Check firewall
   ```bash
   # Check if port is open
   netstat -tuln | grep 8000

   # On macOS
   lsof -i :8000
   ```

### Authentication fails

**Symptoms**:
```json
{"detail": "Could not validate credentials"}
```

**Causes & Solutions**:

1. **No user exists**: Create user first
   ```bash
   lcc auth create-user admin password123 --role admin
   ```

2. **Wrong credentials**: Verify username/password
   ```bash
   # Login via CLI to test
   lcc auth login admin
   ```

3. **Token expired**: Get new token
   ```bash
   # Access tokens expire after 24 hours
   curl -X POST http://localhost:8000/auth/login \
     -d "username=admin&password=password123"
   ```

4. **Wrong Authorization header**: Check header format
   ```bash
   # Correct
   curl -H "Authorization: Bearer eyJ..." http://localhost:8000/scans

   # Incorrect
   curl -H "Authorization: eyJ..." http://localhost:8000/scans  # Missing "Bearer"
   ```

### Rate limit exceeded

**Symptoms**:
```json
{"detail": "Rate limit exceeded: 100 per 1 minute"}
```

**Causes & Solutions**:

1. **Too many requests**: Wait and retry
   ```bash
   # Wait for rate limit to reset (check Retry-After header)
   sleep 60
   ```

2. **Increase rate limit**: Configure in code (self-hosted only)
   ```python
   # In server.py
   @limiter.limit("1000/minute")  # Increase limit
   ```

3. **Use caching**: Cache responses client-side

---

## Dashboard Issues

### Dashboard shows "Failed to fetch"

**Symptoms**:
- Dashboard loads but shows errors
- API requests fail

**Causes & Solutions**:

1. **API not running**: Start API server
   ```bash
   docker-compose up -d
   ```

2. **Wrong API URL**: Check environment variables
   ```bash
   # In dashboard/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **CORS issue**: Configure CORS
   ```bash
   # Set allowed origins
   export LCC_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3001"
   ```

### Dashboard won't start

**Symptoms**:
```
Error: Cannot find module 'next'
```

**Causes & Solutions**:

1. **Dependencies not installed**: Install dependencies
   ```bash
   cd dashboard
   npm install
   ```

2. **Port already in use**: Change port or kill process
   ```bash
   # Check what's using port 3000
   lsof -i :3000

   # Kill process
   kill -9 <PID>

   # Or use different port
   PORT=3001 npm run dev
   ```

3. **Node version incompatible**: Use Node 18+
   ```bash
   # Check Node version
   node --version

   # Upgrade Node
   nvm install 18
   nvm use 18
   ```

### Can't login to dashboard

**Symptoms**:
- Login form doesn't work
- "Invalid credentials" error

**Causes & Solutions**:

1. **No user exists**: Create user via CLI
   ```bash
   lcc auth create-user admin password123 --role admin --email admin@company.com
   ```

2. **API not accessible**: Check API connectivity
   ```bash
   curl http://localhost:8000/health
   ```

3. **Browser cache**: Clear cache and cookies

---

## Docker Issues

### "docker-compose: command not found"

**Symptoms**:
```
bash: docker-compose: command not found
```

**Causes & Solutions**:

1. **Docker Compose not installed**: Install Docker Compose
   ```bash
   # On Docker Desktop, Compose v2 is included
   # Use 'docker compose' instead of 'docker-compose'
   docker compose up -d

   # Or install standalone
   pip install docker-compose
   ```

### "port is already allocated"

**Symptoms**:
```
ERROR: for api  Cannot start service api: driver failed programming external connectivity:
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Causes & Solutions**:

1. **Port in use**: Change port or stop conflicting service
   ```bash
   # Check what's using port
   lsof -i :8000

   # Kill process
   kill -9 <PID>

   # Or change port in docker-compose.yml
   ports:
     - "8001:8000"  # Map to 8001 instead
   ```

2. **Previous container still running**: Stop old containers
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### "Cannot connect to Docker daemon"

**Symptoms**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Causes & Solutions**:

1. **Docker not running**: Start Docker
   ```bash
   # On macOS/Windows: Start Docker Desktop

   # On Linux
   sudo systemctl start docker
   ```

2. **Permission denied**: Add user to docker group
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

### Container exits immediately

**Symptoms**:
```bash
$ docker-compose ps
NAME    STATE     PORTS
api     Exit 1
```

**Causes & Solutions**:

1. **Check logs**: View container logs
   ```bash
   docker-compose logs api
   docker logs <container_id>
   ```

2. **Database migration issue**: Reset database
   ```bash
   docker-compose down -v  # Remove volumes
   docker-compose up -d
   ```

3. **Configuration error**: Check environment variables
   ```bash
   # Verify .env file
   cat .env

   # Check if variables are set
   docker-compose config
   ```

---

## Performance Issues

### Slow scan on large projects

**Solutions**:

1. **Exclude large directories**:
   ```bash
   lcc scan . --exclude "node_modules" --exclude "vendor" --exclude ".venv"
   ```

2. **Increase cache TTL**:
   ```yaml
   # config.yaml
   cache:
     ttl: 604800  # 7 days
   ```

3. **Use faster resolvers only**:
   ```yaml
   resolvers:
     - registry  # Fast
     - clearlydefined  # Medium
     # Disable slow resolvers
   ```

4. **Disable unnecessary detectors**:
   ```yaml
   detectors:
     - npm
     - pypi
     # Disable detectors for languages you don't use
   ```

### High memory usage

**Solutions**:

1. **Scan smaller subsets**:
   ```bash
   # Scan specific directories
   lcc scan ./src
   lcc scan ./backend
   ```

2. **Limit concurrent operations**:
   ```yaml
   # config.yaml
   max_concurrent_resolvers: 5  # Default is 10
   ```

3. **Use Docker with memory limits**:
   ```yaml
   # docker-compose.yml
   services:
     api:
       mem_limit: 2g
   ```

---

## Database Issues

### Database locked error

**Symptoms**:
```
sqlite3.OperationalError: database is locked
```

**Causes & Solutions**:

1. **Multiple instances**: Stop other LCC processes
   ```bash
   ps aux | grep lcc
   kill <PID>
   ```

2. **Database corruption**: Recreate database
   ```bash
   # Backup
   cp ~/.lcc/lcc.db ~/.lcc/lcc.db.backup

   # Remove and recreate
   rm ~/.lcc/lcc.db
   lcc server  # Will recreate on start
   ```

### Can't access database

**Symptoms**:
```
ERROR: Cannot open database
```

**Causes & Solutions**:

1. **Permission denied**: Fix permissions
   ```bash
   chmod 644 ~/.lcc/lcc.db
   chmod 755 ~/.lcc/
   ```

2. **Disk full**: Free up space
   ```bash
   df -h
   # Clean up old scans
   lcc scans clean --older-than 30d
   ```

---

## Getting Help

### Diagnostic Information

When asking for help, provide:

```bash
# System information
lcc --version
python --version
pip list | grep license

# Configuration
lcc config show

# Last scan logs
lcc scan . --verbose

# API logs
docker-compose logs api --tail 100

# Dashboard logs
docker-compose logs dashboard --tail 100
```

### Verbose Logging

Enable detailed logging:

```bash
# CLI
lcc scan . --verbose

# Set log level via environment
export LCC_LOG_LEVEL=DEBUG
lcc scan .

# API server
lcc server --log-level DEBUG
```

### Common Log Locations

```
# CLI logs
~/.lcc/logs/lcc.log

# Docker logs
docker-compose logs -f api
docker-compose logs -f dashboard

# System logs (Linux)
journalctl -u lcc

# System logs (macOS)
tail -f /var/log/system.log | grep lcc
```

### Support Channels

1. **Documentation**: https://docs.lcc.dev
2. **GitHub Issues**: https://github.com/your-org/lcc/issues
3. **GitHub Discussions**: https://github.com/your-org/lcc/discussions
4. **Email**: support@lcc.dev

### Before Filing an Issue

1. Check existing issues: https://github.com/your-org/lcc/issues
2. Search documentation
3. Try the latest version
4. Collect diagnostic information
5. Create minimal reproducible example

### Issue Template

```markdown
**Environment**:
- LCC version: [run `lcc --version`]
- Python version: [run `python --version`]
- OS: [e.g., Ubuntu 22.04, macOS 13.5]
- Installation method: [pip, Docker, source]

**Description**:
[Clear description of the issue]

**Steps to Reproduce**:
1.
2.
3.

**Expected behavior**:
[What you expected to happen]

**Actual behavior**:
[What actually happened]

**Logs**:
```
[Paste relevant logs with --verbose flag]
```

**Additional context**:
[Any other relevant information]
```

---

## Quick Reference

### Health Checks

```bash
# Check if LCC is working
lcc --version

# Check if API is running
curl http://localhost:8000/health

# Check if Dashboard is running
curl http://localhost:3000

# Check database
sqlite3 ~/.lcc/lcc.db "SELECT COUNT(*) FROM scans;"
```

### Reset Everything

```bash
# WARNING: This deletes all data

# Stop services
docker-compose down -v

# Remove database and cache
rm -rf ~/.lcc/

# Restart
docker-compose up -d

# Recreate admin user
lcc auth create-user admin password123 --role admin
```

### Performance Tuning

```yaml
# config.yaml - Fast configuration
cache:
  enabled: true
  ttl: 604800  # 7 days

resolvers:
  - registry  # Fastest
  - clearlydefined

detection:
  max_depth: 5
  timeout: 60

max_concurrent_resolvers: 5
```

---

*For additional help, see [FAQ.md](FAQ.md) or contact support@lcc.dev*
