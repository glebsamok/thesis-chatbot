"""
Utility Functions Module

This module contains common utility functions used throughout the application.
These are helper functions that provide basic file operations and other
commonly needed functionality.

Author: Thesis Research Project
Date: 2024
"""

def get_file_content(file_path):
    """
    Read and return the entire content of a file as a string.
    
    This function opens a file in read mode and returns its complete content.
    It's commonly used for reading configuration files, prompts, or other
    text-based files that need to be loaded into the application.
    
    Args:
        file_path (str): Path to the file to be read
        
    Returns:
        str: The complete content of the file as a string
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        IOError: If there are issues reading the file
        
    Example:
        >>> content = get_file_content('prompts/system_prompt.txt')
        >>> print(content)
        'This is the system prompt content...'
    """
    with open(file_path, 'r') as file:
        return file.read()