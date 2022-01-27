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

class NullModelId(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullModelId, self).__init__()
        self.message = 'Learning Rate Cannot be empty'
    
    def __str__(self):
        return self.message
    
class NullRunID(Exception):
    ''' Raised when unique id is not provided as an input. '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(NullRunID, self).__init__()
        self.message = 'Run Id needed to show the status of the training'
    
    def __str__(self):
        return self.message
        
class IncorrectOptions(Exception):
    ''' Raised when augment options are provided other than the ones present in config file '''
    
    def __init__(self):
        # Calling the init function of parent class
        super(IncorrectOptions, self).__init__()
        self.message = 'Please check the pre-processing options provided'
    
    def __str__(self):
        return self.message
    
