import os
import glob
import re

# List of excluded phrases to filter out files.
excluded_phrases = ["static final", "extends LocalEntity", "private Integer version"]

def read_java_files(directory):
    # Classes to be excluded from processing.
    excluded_classes = ["filtervo", "vo", "importacao", "legado", "enum", "Client", "sed", "SED"]
    public_class_files = []
    public_abstract_class_files = []

    # Walk through the directory to find Java files.
    for source, _, files in os.walk(directory):
        for file in glob.glob(os.path.join(source, '*.java')):
            file_name = os.path.basename(file)
            if any(word in file_name for word in excluded_classes):
                continue
            file_name = camel_case_to_snake_case(file_name, 'false')
            file_name = 'sge_' + file_name

            with open(file, 'r') as f:
                content = f.read()

            # Categorizing files based on class type.
            if 'public class ' in content:
                public_class_files.append((file, file_name))
            elif 'public abstract class ' in content:
                public_abstract_class_files.append((file, file_name))

    # Process files with 'public abstract class' first.
    for file, file_name in public_abstract_class_files:
        process_java_file(file, file_name)

    # Then process files with 'public class'.
    for file, file_name in public_class_files:
        process_java_file(file, file_name)

def process_java_file(file_path, file_name):
    with open(file_path, 'r') as file:
        content = file.read()

        # Check if the file contains 'public class'.
        if 'class ' in content:
            class_info = extract_annotations(content)
            generate_lookml(class_info, file_name)
        else:
            print(f"File {file_name} ignored, does not contain 'public class'.")

def extract_annotations(content):
    properties = {}
    table_name = None
    lines = content.splitlines()
    base_class = None
    column_name = None
    extends_paper = "extends Papel" in content

    for i, line in enumerate(lines):
        if line.strip().startswith('public ') and 'extends' in line:
            base_class = line.split('extends')[-1].split()[0].strip()
            continue

        if any(excluded_word in line for excluded_word in excluded_phrases):
            continue

        if line.strip().startswith('@Table('):
            table_name = line.split('"')[1]

        if 'private' in line or 'protected' in line:
            parts = line.split()
            if len(parts) < 3:
                continue
            field_type = parts[1]
            field_name = parts[2].replace(';', '')

            j = i - 1
            annotations = []
            specified_column_name = None
            while j >= 0 and ('@' in lines[j]):
                annotation = lines[j].strip()
                if annotation.startswith('@Column(name ='):
                    specified_column_name = annotation.split('"')[1]

                if annotation.startswith('@'):
                    annotations.append(annotation)

                j -= 1

            column_name = specified_column_name if specified_column_name is not None else field_name
            field_name = camel_case_to_snake_case(field_name, 'false')
            properties[field_name] = {'type': field_type, 'annotations': annotations, 'column_name': column_name}

    return {'table_name': table_name, 'properties': properties, 'extends_paper': extends_paper, 'base_class': base_class}

def camel_case_to_snake_case(name, has_id):
    if name is not None:
        if '.java' in name:
            name = name.replace('.java', '')
        
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    if has_id == 'true':
        name += '_id'

    return name

def generate_lookml(class_info, file_name):
    table_name = class_info['table_name']
    base_class = class_info['base_class']
    extends_paper = class_info['extends_paper']
    lookml = f"view: {file_name} {{\n"

    if table_name:
        lookml += f"  sql_table_name: {{_user_attributes['database_user']}}.{table_name} ;;\n\n"

    if base_class and base_class != 'SonnerBaseEntity':
        if lookml_base_class_generated(base_class):
            lookml += f"  extends: [{camel_case_to_snake_case(base_class, 'false')}]\n\n"
        else:
            print"Class not found for base view creation")
            return 
    

    if extends_paper:
        lookml += "     dimension: id {\n"
        lookml += "         type: number\n"
        lookml += "         sql: ${{TABLE}}.id ;;\n"
        lookml += "         primary_key: yes\n"
        lookml += "     }\n\n"

    for field_name, info in class_info['properties'].items():
        lookml_type, is_primary_key = map_lookml_type(info['annotations'], info['type'])
        

        if lookml_type == 'date':
            lookml += f"     dimension_group: {field_name} {{\n"
            lookml += f"        timeframes: [time, date, week, month, year]\n"
        else:
            lookml += f"     dimension: {field_name} {{\n"

        lookml += f"        sql: ${{TABLE}}.{info['column_name']} ;;\n"
        lookml += f"        type: {lookml_type}\n"
        if is_primary_key:
            lookml += "         primary_key: yes\n"
        lookml += "     }\n"
        lookml += "\n"
    lookml += "     }\n"

    save_lookml_file(lookml, file_name, destination_folder)
    return lookml

def lookml_base_class_generated(base_class):
    # Check if the LookML file for the base class exists
    file_path = os.path.join(destination_folder, f"{camel_case_to_snake_case(base_class, 'false')}.lkml")
    return os.path.exists(file_path)

def save_lookml_file(lookml, file_name, destination_folder):
    # Ensure the destination folder exists
    os.makedirs(destination_folder, exist_ok=True)

    full_path = os.path.join(destination_folder, f"{file_name}.view.lkml")

    with open(full_path, 'w') as file:
        file.write(lookml)
    print(f"LookML File saved at: {full_path}")

def map_lookml_type(annotations, field_type):
    is_primary_key = '@Id' in annotations or '@GeneratedValue' in annotations

    if field_type == 'ForeignKey':
        return 'number', is_primary_key

    # Mapping based on field type
    lookml_type = {
        'String': 'string',
        'Integer': 'number',
        'Long': 'number',
        'BigDecimal': 'number',
        'Date': 'date',  # or 'time', depending on the need
        'Boolean': 'yesno',
        # Add other mappings as necessary
    }.get(field_type, 'string')  # Default type

    return lookml_type, is_primary_key

source_folder = '/home/bernard/development/projects/grp-web/grp-web/sonner-model/src/main/java/br/com/sonner/escola/model/'
destination_folder = '/home/bernard/development/pip/generated'
# Replace 'path_to_folder' with the path to the directory containing the Java files
read_java_files(source_folder)
