def get_file_content(file_path):
    with open(file_path, 'r') as file:
        return file.read()