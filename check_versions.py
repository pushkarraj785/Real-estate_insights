import importlib.metadata
import sys

# Print Python version
print(f"Python version: {sys.version}")

# Try to get package versions
packages = ['google-generativeai', 'httpx', 'pandas', 'numpy', 'flask', 'requests', 'beautifulsoup4']
print("\nPackage versions:")

for package in packages:
    try:
        version = importlib.metadata.version(package)
        print(f"- {package}: {version}")
    except importlib.metadata.PackageNotFoundError:
        print(f"- {package}: Not found")

print("\nThis information can help diagnose version compatibility issues.")
