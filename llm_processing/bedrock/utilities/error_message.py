#!/usr/bin/env python3
"""
Error message handling for Field Museum Bedrock Transcription application.
This module provides a class for handling and displaying error messages.
"""

import traceback
import sys
from typing import Optional

class ErrorMessage:
    """A class for handling and displaying error messages with length limits."""
    
    def __init__(self, value: str, max_length: int = 2000):
        """
        Initialize an ErrorMessage.
        
        Args:
            value: The error message text
            max_length: Maximum length to display in string representation
        """
        self.value = value
        self.max_length = max_length
        
        # Print traceback to terminal when created
        print("\nError traceback:", file=sys.stderr)
        traceback.print_stack(file=sys.stderr)
    
    def __str__(self) -> str:
        """
        String representation of the error message.
        
        Returns:
            The error message, truncated if longer than max_length
        """
        if len(self.value) <= self.max_length:
            return self.value
        else:
            return f"{self.value[:self.max_length]}... [Error message truncated, total length: {len(self.value)}]"
    
    def __repr__(self) -> str:
        """
        Representation of the error message.
        
        Returns:
            A string representation of the ErrorMessage object
        """
        return f"ErrorMessage(length={len(self.value)})"
    
    def get_full_message(self) -> str:
        """
        Get the full error message.
        
        Returns:
            The complete error message
        """
        return self.value
    
    def get_truncated_message(self, length: Optional[int] = None) -> str:
        """
        Get a truncated version of the error message.
        
        Args:
            length: Maximum length of the truncated message (defaults to self.max_length)
            
        Returns:
            The truncated error message
        """
        max_len = length if length is not None else self.max_length
        if len(self.value) <= max_len:
            return self.value
        else:
            return f"{self.value[:max_len]}... [truncated]"
    
    @classmethod
    def from_exception(cls, exception: Exception, max_length: int = 2000) -> 'ErrorMessage':
        """
        Create an ErrorMessage from an exception.
        
        Args:
            exception: The exception to convert
            max_length: Maximum length to display in string representation
            
        Returns:
            An ErrorMessage object
        """
        # Print the exception traceback to stderr
        print("\nException traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        return cls(str(exception), max_length)


# Example usage
if __name__ == "__main__":
    try:
        # Generate a long error message
        error_text = "Error details: " + "x" * 5000
        raise ValueError(error_text)
    except Exception as e:
        # Create an ErrorMessage from the exception
        error_msg = ErrorMessage.from_exception(e)
        
        # Display the error message (truncated)
        print(f"Error occurred: {error_msg}")
        
        # Get a more severely truncated version
        short_msg = error_msg.get_truncated_message(100)
        print(f"Short error: {short_msg}")