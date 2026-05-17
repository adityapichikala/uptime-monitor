import re

file_path = '/etc/systemd/system/k3s.service'
with open(file_path, 'r') as f:
    content = f.read()

# Make sure we don't double append
if '--disable traefik' not in content:
    # Replace the server line to add disables
    content = content.replace('server \\', 'server \\\n    --disable traefik \\\n    --disable metrics-server \\')

with open(file_path, 'w') as f:
    f.write(content)

print("K3s service optimized successfully!")
