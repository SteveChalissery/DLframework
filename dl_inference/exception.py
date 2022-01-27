''''
Custom Exception defining class.

'''

class NullUniqueID(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullUniqueID, self).__init__()
        self.message = 'Unique Id cannot be empty'
    
    def __str__(self):
        return self.message

class NullEpochs(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullEpochs, self).__init__()
        self.message = 'Epochs cannot be empty'
    
    def __str__(self):
        return self.message

class NullLearningRate(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullLearningRate, self).__init__()
        self.message = 'Learning Rate Cannot be empty'
    
    def __str__(self):
        return self.message

class NullModelName(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullModelName, self).__init__()
        self.message = 'Please provide model name to start the inferencing'
    
    def __str__(self):
        return self.message
    
class NullImageUrls(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullImageUrls, self).__init__()
        self.message = 'Please provide at least one test image url.'
    
    def __str__(self):
        return self.message
    
class InvalidURL(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(InvalidURL, self).__init__()
        self.message = 'Inavlid URL.'
    
    def __str__(self):
        return self.message

class InvalidImageURL(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(InvalidImageURL, self).__init__()
        self.message = 'URL does not point to a valid image source'
    
    def __str__(self):
        return self.message

class ResourceNotFound(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(ResourceNotFound, self).__init__()
        self.message = f'Resource was not found in azure storage. Please check the name or contact the developer.'
    
    def __str__(self):
        return self.message