import ast
import os
import pkgutil
import sys
import subprocess

excluded_modules = ['kiteconnect', 'utils']


def get_imports(file_path):
    """
    Extract import statements from a Python file.
    """
    with open(file_path, 'r') as file:
        tree = ast.parse(file.read(), file_path)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if '.' in module_name:
                        module_name = module_name.split('.')[0]
                    if module_name in excluded_modules:
                        continue
                    imports.append(module_name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module
                if '.' in module_name:
                    module_name = module_name.split('.')[0]
                if module_name in excluded_modules:
                    continue
                imports.append(module_name)
        return imports

def check_installed(package_name):
    """
    Check if a package is installed.
    """
    # Don't check built-in modules
    if package_name in sys.builtin_module_names:
        return True
    # Check if the package is installed
    try:
        loader = pkgutil.find_loader(package_name)
        return loader is not None
    except ImportError:
        return False

def check_installed_packages(required_packages):
    """
    Check if required packages are installed.
    Returns a set of installed packages and a set of missing packages.
    """
    installed_packages = set()
    missing_packages = set()
    for package in required_packages:
        if check_installed(package):
            installed_packages.add(package)
        else:
            missing_packages.add(package)
    return installed_packages, missing_packages

def analyze_folder(folder_path):
    """
    Analyze Python files in a folder and extract import statements.
    Returns a dictionary with file-wise imports and a set of all required imports.
    """
    imports_by_file = {}
    all_required_imports = set()
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = get_imports(file_path)
                imports_by_file[file_path] = imports
                all_required_imports.update(imports)
    return imports_by_file, all_required_imports


# Example usage:
folder_path = 'kiteconnect'  # Replace with the path to your folder
imports_by_file, all_required_imports = analyze_folder(folder_path)
installed_packages, missing_packages = check_installed_packages(all_required_imports)

# Print results
print("File-wise imports:")
for file_path, imports in imports_by_file.items():
    print(f"Imports in {file_path}:", imports)

print("\nAll required imports:", all_required_imports)
print("\nInstalled packages:", installed_packages)
print("Missing packages:", missing_packages)

def install_missing_packages(missing_packages):
    """
    Install missing packages using pip.
    """
    for package in missing_packages:
        subprocess.run(['pip', 'install', package])

if missing_packages:
    print("Missing packages:", missing_packages)
    install_missing_packages(missing_packages)
    print("Missing packages installed.")
else:
    print("All required packages are already installed.")

installed_packages, missing_packages = check_installed_packages(all_required_imports)
print("Missing packages:", missing_packages)

