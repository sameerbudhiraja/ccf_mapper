import json
import os

# Path to the JSON file
json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..', 'adobe.ccf', 'adobe_internal_controls.json')
json_path = os.path.abspath(json_path)

# Load the JSON data
with open(json_path, 'r', encoding='utf-8') as f:
	adobe_internal_controls = json.load(f)

# Export the data for use in other modules
__all__ = ['adobe_internal_controls']

