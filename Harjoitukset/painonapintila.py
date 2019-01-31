# Määritellään nyt pin 18 sisääntuloksi ja kytketään sisäinen vastus
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# napin painalluksen funktio
while True:
    if GPIO.input(18) == False:
        print ("Nappi toimii!")