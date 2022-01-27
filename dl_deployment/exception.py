''''
Custom Exception defining class.

'''

class NullUniqueID(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullUniqueID, self).__init__()
        self.message = 'unique_id is not passed as an input to the api'
    
    def __str__(self):
        return self.message
    
class NullModelName(Exception):
    ''' Raised when the Failure column is not provided as an iunput. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullModelName, self).__init__()
        self.message = 'model_name is not passed as an input to the API'
    
    def __str__(self):
        return self.message

class InvalidUniqueID(Exception):
    def __init__(self):
        # Calling the init function of parent class
        super(InvalidUniqueID, self).__init__()
        self.message = 'Invalid Unique ID'
    
    def __str__(self):
        return self.message

class InvalidModelName(Exception):
    def __init__(self):
        # Calling the init function of parent class
        super(InvalidModelName, self).__init__()
        self.message = 'Invalid Model Name'
    
    def __str__(self):
        return self.message