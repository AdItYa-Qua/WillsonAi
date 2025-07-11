import pywhatkit as kit 

def message( number,text):
    kit.sendwhatmsg(number,text)


number =  "+918770394330"
text = input("What you want to message: ")

message(number,text)